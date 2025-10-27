from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app import db
from app.models import OdontogramaDenteEstado, Paciente
from app.services import timeline_service
from app.utils.sanitization import sanitizar_input


def update_estado_dente(
    paciente_id: int,
    tooth_id: str,
    novo_estado_json: Dict[str, Any],
    usuario_id: int,
) -> Optional[OdontogramaDenteEstado]:
    """Upsert do estado vivo de um dente no odontograma (Regra 7 - atômico).

    - Busca por (paciente_id, tooth_id). Atualiza se existir; cria se não.
    - Após commit, registra evento na timeline (non-blocking).
    """
    # Sanitizar o identificador textual do dente; estado JSON é preservado
    tooth_id_clean = sanitizar_input(tooth_id)
    if not isinstance(tooth_id_clean, str) or not tooth_id_clean:
        raise ValueError("tooth_id inválido.")

    # Garantir que o paciente existe (FK real no mesmo bind)
    if db.session.get(Paciente, int(paciente_id)) is None:
        raise ValueError("Paciente não encontrado.")

    try:
        row = (
            db.session.query(OdontogramaDenteEstado)
            .filter(
                OdontogramaDenteEstado.paciente_id == int(paciente_id),
                OdontogramaDenteEstado.tooth_id == tooth_id_clean,
            )
            .one_or_none()
        )
        if row is None:
            row = OdontogramaDenteEstado()
            row.paciente_id = int(paciente_id)
            row.tooth_id = tooth_id_clean
            row.estado_json = novo_estado_json
            db.session.add(row)
        else:
            row.estado_json = novo_estado_json
        db.session.commit()

        # Timeline non-blocking
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="CLINICO",
                descricao=f"Odontograma atualizado (Dente {tooth_id_clean}).",
                usuario_id=usuario_id,
                paciente_id=int(paciente_id),
            )
        except Exception:
            pass
        return row
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao atualizar estado do dente: {exc}")


def get_estado_odontograma_completo(paciente_id: int) -> Dict[str, Any]:
    """Retorna o mapa de estado do odontograma para o paciente.

    Formato: { tooth_id: estado_json, ... }
    """
    rows = (
        db.session.query(OdontogramaDenteEstado)
        .filter(OdontogramaDenteEstado.paciente_id == int(paciente_id))
        .all()
    )
    return {r.tooth_id: r.estado_json for r in rows}


def update_odontograma_bulk(
    paciente_id: int, updates_map: Dict[str, Any], usuario_id: int
) -> bool:
    """Aplica N updates de estado de dente em transação única (bulk).

    - Carrega estados existentes do paciente em um mapa por tooth_id.
    - Faz upsert para cada entrada do updates_map sem comitar individualmente.
    - Comita uma única vez e registra um evento de timeline (non-blocking).
    """
    # Verificar existência do paciente (FK real)
    if db.session.get(Paciente, int(paciente_id)) is None:
        raise ValueError("Paciente não encontrado.")

    try:
        # Carregar existentes em mapa
        existentes = (
            db.session.query(OdontogramaDenteEstado)
            .filter(OdontogramaDenteEstado.paciente_id == int(paciente_id))
            .all()
        )
        existing_map = {row.tooth_id: row for row in existentes}

        for raw_tooth_id, estado in (updates_map or {}).items():
            # Sanitizar tooth_id; manter estado como veio (dict JSON)
            tooth_id_clean = sanitizar_input(str(raw_tooth_id))
            if not isinstance(tooth_id_clean, str) or not tooth_id_clean:
                raise ValueError("tooth_id inválido no payload.")
            # Validar estado_json mínimo como dict
            if not isinstance(estado, dict):
                raise ValueError("estado_json inválido no payload.")

            if tooth_id_clean in existing_map:
                obj = existing_map[tooth_id_clean]
                obj.estado_json = estado
                db.session.add(obj)
            else:
                obj = OdontogramaDenteEstado()
                obj.paciente_id = int(paciente_id)
                obj.tooth_id = tooth_id_clean
                obj.estado_json = estado
                db.session.add(obj)

        db.session.commit()
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="CLINICO",
                descricao=(
                    "Odontograma atualizado ("
                    f"{len(updates_map or {})} dentes)."
                ),
                usuario_id=usuario_id,
                paciente_id=int(paciente_id),
            )
        except Exception:
            pass
        return True
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha no bulk do odontograma: {exc}")


def snapshot_odontograma_inicial(
    paciente_id: int, usuario_id: int, force_overwrite: bool = False
) -> bool:
    """Captura o snapshot inicial do odontograma para o paciente (Regra 3).

    - Proíbe sobrescrita por padrão; permite quando `force_overwrite=True`.
    - Transação atômica (try/commit/rollback).
    """
    # Buscar paciente (mesmo bind) e validar existência
    paciente = db.session.get(Paciente, int(paciente_id))
    if paciente is None:
        raise ValueError("Paciente não encontrado.")

    try:
        # Validação de não-sobrescrita
        if (
            getattr(paciente, "odontograma_inicial_json", None) is not None
            and not force_overwrite
        ):
            raise ValueError(
                "Um snapshot inicial já existe. A sobrescrita foi negada."
            )

        # Obter estado vivo atual
        estado_vivo = get_estado_odontograma_completo(int(paciente_id))
        paciente.odontograma_inicial_json = estado_vivo
        # Carimbar timestamp UTC (timezone-aware)
        paciente.odontograma_inicial_data = datetime.now(timezone.utc)
        db.session.add(paciente)
        db.session.commit()

        # Timeline non-blocking
        try:
            suffix = " (Sobrescrito)" if force_overwrite else ""
            timeline_service.create_timeline_evento(
                evento_tipo="CLINICO",
                descricao=f"Snapshot inicial do odontograma salvo.{suffix}",
                usuario_id=usuario_id,
                paciente_id=int(paciente_id),
            )
        except Exception:
            pass
        return True
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao salvar snapshot inicial: {exc}")
