from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, cast

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import Anamnese, AnamneseStatus, MediaPaciente, Paciente
from app.services import timeline_service
from app.utils.sanitization import sanitizar_input


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    v = value.strip()
    # Try ISO first (YYYY-MM-DD) then common BR format
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def get_paciente_by_id(paciente_id: int) -> Paciente | None:
    return db.session.get(Paciente, int(paciente_id))


def get_all_pacientes() -> list[Paciente]:
    return (
        db.session.query(Paciente).order_by(Paciente.nome_completo.asc()).all()
    )


def create_paciente(form_data: Mapping[str, str], usuario_id: int) -> Paciente:
    try:
        p = Paciente()

        # Nome obrigatório (aplicar sanitização)
        _nome = sanitizar_input(form_data.get("nome_completo"))
        p.nome_completo = _nome if isinstance(_nome, str) else ""
        if not p.nome_completo:
            raise ValueError("Nome do paciente é obrigatório.")

        # Datas: sanitizar string antes de parse
        p.data_nascimento = _parse_date(
            cast(
                str | None,
                sanitizar_input(form_data.get("data_nascimento")),
            )
        )

        # Campos simples de texto livre: sanitizar e normalizar para None
        # se vazio
        for field in (
            "cpf",
            "telefone",
            "email",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
        ):
            raw = form_data.get(field)
            val = sanitizar_input(raw)
            setattr(p, field, val if isinstance(val, str) and val else None)

        db.session.add(p)
        db.session.flush()  # ensure p.id

        # optionally create empty Anamnese
        criar_anamnese = form_data.get("criar_anamnese")
        if criar_anamnese:
            a = Anamnese()
            a.paciente_id = p.id
            db.session.add(a)

        db.session.commit()
        # Escrita dupla: registrar evento de UX após sucesso
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="CADASTRO",
                descricao=f"Paciente '{p.nome_completo}' criado.",
                usuario_id=usuario_id,
                paciente_id=p.id,
            )
        except Exception:
            # Não bloquear o fluxo principal por falha no log de UX
            pass
        return p
    except Exception as exc:
        db.session.rollback()
        # Reempacotar para mensagem de domínio controlada
        raise ValueError(f"Falha ao criar paciente: {exc}")


def update_paciente(
    paciente_id: int, form_data: Mapping[str, str], usuario_id: int
) -> Paciente:
    p = get_paciente_by_id(paciente_id)
    if p is None:
        raise ValueError("Paciente não encontrado.")

    nome = (
        cast(
            str | None,
            sanitizar_input(form_data.get("nome_completo")),
        )
        or ""
    )
    if nome:
        p.nome_completo = nome

    # Sanitizar string da data antes de parsear. Manter semântica atual:
    # se a key foi enviada (mesmo vazia), atualiza o campo com o
    # resultado do parse (None quando vazio ou inválido).
    raw_dn = form_data.get("data_nascimento")
    dn = _parse_date(cast(str | None, sanitizar_input(raw_dn)))
    if raw_dn is not None:
        p.data_nascimento = dn

    # Update other simple fields (set to None if provided empty)
    for field in (
        "cpf",
        "telefone",
        "email",
        "cep",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
    ):
        if field in form_data:
            raw = form_data.get(field)
            value = sanitizar_input(raw)
            setattr(
                p,
                field,
                value if isinstance(value, str) and value else None,
            )

    db.session.add(p)
    db.session.commit()
    # Escrita dupla: registrar evento de UX após sucesso
    try:
        timeline_service.create_timeline_evento(
            evento_tipo="CADASTRO",
            descricao="Dados cadastrais atualizados.",
            usuario_id=usuario_id,
            paciente_id=p.id,
        )
    except Exception:
        pass
    return p


def update_anamnese(
    paciente_id: int, form_data: Mapping[str, Any], usuario_id: int
) -> Anamnese:
    """Create or update a patient's Anamnese and compute red flags.

        Red flags when:
        - Any of: alergias, medicamentos_uso_continuo,
            historico_doencas are non-empty
    - Any boolean-like field in form_data has value 'sim' (case-insensitive)
    """
    paciente = get_paciente_by_id(paciente_id)
    if paciente is None:
        raise ValueError("Paciente não encontrado.")

    a = paciente.anamnese
    if a is None:
        a = Anamnese()
        a.paciente_id = paciente.id
        db.session.add(a)
    # Garantir tipagem explícita
    a = cast(Anamnese, a)

    # Map possible form aliases to model fields
    alias_map: dict[str, str] = {
        "alergia_detalhes": "alergias",
        "alergias": "alergias",
        "medicamentos": "medicamentos_uso_continuo",
        "medicamentos_uso_continuo": "medicamentos_uso_continuo",
        "historico_doencas": "historico_doencas",
    }

    def _normalize_safe_text(val: str | None) -> str | None:
        """Return None for values that semantically mean 'empty/safe'.

        Treat common synonyms as empty: 'nenhuma', 'nenhum', 'nao', 'não',
        'n/a', 'none', 'no', '-', 'sem', 'sem alergias'.
        """
        if val is None:
            return None
        s = val.strip()
        if not s:
            return None
        low = s.lower()
        safe_tokens = {
            "nenhuma",
            "nenhum",
            "nao",
            "não",
            "n/a",
            "none",
            "no",
            "-",
            "sem",
            "sem alergias",
        }
        return None if low in safe_tokens else s

    # Update known fields (with sanitization + normalization of safe values)
    for form_key, model_key in alias_map.items():
        if form_key in form_data:
            raw = form_data.get(form_key)
            sanitized = sanitizar_input(cast(str | None, raw))
            val = _normalize_safe_text(
                cast(
                    str | None,
                    sanitized if isinstance(sanitized, str) else None,
                )
            )
            setattr(a, model_key, val)

    # Compute red flags
    flag = False
    for key in ("alergias", "medicamentos_uso_continuo", "historico_doencas"):
        if getattr(a, key, None):
            flag = True
            break
    if not flag:
        # Look for yes/no fields where 'sim' indicates a red flag
        for _k, v in form_data.items():
            if isinstance(v, str) and v.strip().lower() == "sim":
                flag = True
                break

    # Atualizar flags e metadados de status/atualização
    a.has_red_flags = bool(flag)
    # Marcar como concluída no ato de salvar
    try:
        from datetime import datetime, timezone
    except Exception:
        datetime = None  # type: ignore
        timezone = None  # type: ignore
    a.status = AnamneseStatus.CONCLUIDA
    if datetime and timezone:
        a.data_atualizacao = datetime.now(timezone.utc)

    db.session.commit()
    # Escrita dupla: registrar evento de UX após sucesso
    try:
        timeline_service.create_timeline_evento(
            evento_tipo="CLINICO",
            descricao="Anamnese atualizada.",
            usuario_id=usuario_id,
            paciente_id=a.paciente_id,
        )
    except Exception:
        pass
    return cast(Anamnese, a)


def save_media_file(
    paciente_id: int, file_storage, descricao: str | None, usuario_id: int
) -> MediaPaciente:
    """Save file under instance/media_storage/<paciente_id>/.

    Also record the relative path in the database.
    """
    paciente = get_paciente_by_id(paciente_id)
    if paciente is None:
        raise ValueError("Paciente não encontrado.")

    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("Arquivo inválido.")

    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError("Nome de arquivo inválido.")

    base_dir = os.path.join(current_app.instance_path, "media_storage")
    media_dir = os.path.join(base_dir, str(paciente_id))
    os.makedirs(media_dir, exist_ok=True)

    save_path = os.path.join(media_dir, filename)
    relative_path = os.path.join(str(paciente_id), filename)

    file_storage.save(save_path)

    media = MediaPaciente()
    media.paciente_id = paciente_id
    media.file_path = relative_path
    _desc = sanitizar_input(descricao)
    media.descricao = (
        cast(str | None, _desc) if isinstance(_desc, str) else None
    )
    db.session.add(media)
    db.session.commit()
    # Escrita dupla: registrar evento de UX após sucesso
    try:
        descricao_log = media.descricao or os.path.basename(media.file_path)
        timeline_service.create_timeline_evento(
            evento_tipo="DOCUMENTO",
            descricao=f"Mídia/Documento salvo: '{descricao_log}'.",
            usuario_id=usuario_id,
            paciente_id=media.paciente_id,
        )
    except Exception:
        pass
    return media


# ----------------------------------
# Anamnese Alert Logic (Regra 7)
# ----------------------------------
def check_anamnese_alert_status(paciente: Paciente) -> str | None:
    """Retorna o tipo de alerta de Anamnese ou None quando OK.

    Tipos possíveis:
    - "AUSENTE": não há registro de Anamnese (1:1 esperado via relacionamento)
    - "PENDENTE": status pendente OU sem data de atualização disponível
    - "EXPIRADA": data de atualização anterior a 6 meses atrás

    Observações:
    - O modelo atual pode não possuir campos `status`/`data_atualizacao`.
      Este helper lida com ambos os cenários de forma resiliente.
    """
    a = paciente.anamnese
    if a is None:
        return "AUSENTE"

    # Status pendente ou nunca atualizada => alerta PENDENTE
    if a.status == AnamneseStatus.PENDENTE:
        return "PENDENTE"
    if not a.data_atualizacao:
        return "PENDENTE"

    # Verificar expiração: > 180 dias (regra determinística)
    from datetime import datetime, timedelta, timezone

    dt = a.data_atualizacao
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    limite_expiracao = datetime.now(timezone.utc) - timedelta(days=180)
    if dt < limite_expiracao:
        return "EXPIRADA"

    return None


# ----------------------------------
# Nova API pública: Status detalhado da Anamnese (Passo 1 Tela Ficha)
# ----------------------------------
def get_anamnese_status(paciente: Paciente) -> dict[str, Any]:
    """Retorna estrutura de status para a Tela Ficha + Anamnese.

    Campos retornados:
    - status: 'VALIDA' | 'PENDENTE' | 'DESATUALIZADA' | 'AUSENTE'
    - mostrar_alerta: bool (Regra §7.4)
    - data_atualizacao: datetime | None
    - dias_desde_ultima_atualizacao: int | None

    Lógica:
    - AUSENTE: paciente.anamnese inexistente.
    - PENDENTE: anamnese.status == PENDENTE ou sem data_atualizacao.
    - DESATUALIZADA: data_atualizacao > 6 meses atrás (> 180 dias).
    - VALIDA: caso contrário.
    """
    from datetime import datetime, timezone

    a = paciente.anamnese
    if a is None:
        return {
            "status": "AUSENTE",
            "mostrar_alerta": True,
            "data_atualizacao": None,
            "dias_desde_ultima_atualizacao": None,
        }

    # Base: dias desde última atualização (se existir)
    dt = a.data_atualizacao
    dias = None
    if dt is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dias = (datetime.now(timezone.utc) - dt).days

    # PENDENTE
    if a.status == AnamneseStatus.PENDENTE or a.data_atualizacao is None:
        return {
            "status": "PENDENTE",
            "mostrar_alerta": True,
            "data_atualizacao": a.data_atualizacao,
            "dias_desde_ultima_atualizacao": dias,
        }

    # DESATUALIZADA (> 180 dias)
    if dt and dias is not None and dias > 180:
        return {
            "status": "DESATUALIZADA",
            "mostrar_alerta": True,
            "data_atualizacao": dt,
            "dias_desde_ultima_atualizacao": dias,
        }

    # Caso válido
    return {
        "status": "VALIDA",
        "mostrar_alerta": False,
        "data_atualizacao": dt,
        "dias_desde_ultima_atualizacao": dias,
    }


def update_ficha_anamnese_atomic(
    paciente_id: int, form_data: Mapping[str, Any], usuario_id: int
) -> Paciente:
    """Atualiza dados cadastrais + anamnese em transação única.

    Reimplementa lógica de `update_paciente` + `update_anamnese` sem commits
    intermediários para atender §7.5 (atomicidade) da missão.
    """
    from datetime import datetime, timezone

    p = get_paciente_by_id(paciente_id)
    if p is None:
        raise ValueError("Paciente não encontrado.")

    try:
        # --- Dados cadastrais ---
        nome = (
            cast(
                str | None,
                sanitizar_input(form_data.get("nome_completo")),
            )
            or ""
        )
        if nome:
            p.nome_completo = nome

        raw_dn = form_data.get("data_nascimento")
        dn = _parse_date(cast(str | None, sanitizar_input(raw_dn)))
        if raw_dn is not None:
            p.data_nascimento = dn

        for field in (
            "cpf",
            "telefone",
            "email",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
        ):
            if field in form_data:
                raw = form_data.get(field)
                value = sanitizar_input(raw)
                setattr(
                    p,
                    field,
                    value if isinstance(value, str) and value else None,
                )

        # --- Anamnese ---
        a = p.anamnese
        if a is None:
            a = Anamnese()
            a.paciente_id = p.id
            db.session.add(a)
        a = cast(Anamnese, a)

        alias_map: dict[str, str] = {
            "alergia_detalhes": "alergias",
            "alergias": "alergias",
            "medicamentos": "medicamentos_uso_continuo",
            "medicamentos_uso_continuo": "medicamentos_uso_continuo",
            "historico_doencas": "historico_doencas",
        }

        def _normalize_safe_text(val: str | None) -> str | None:
            if val is None:
                return None
            s = val.strip()
            if not s:
                return None
            low = s.lower()
            safe_tokens = {
                "nenhuma",
                "nenhum",
                "nao",
                "não",
                "n/a",
                "none",
                "no",
                "-",
                "sem",
                "sem alergias",
            }
            return None if low in safe_tokens else s

        for form_key, model_key in alias_map.items():
            if form_key in form_data:
                raw = form_data.get(form_key)
                sanitized = sanitizar_input(cast(str | None, raw))
                val = _normalize_safe_text(
                    cast(
                        str | None,
                        sanitized if isinstance(sanitized, str) else None,
                    )
                )
                setattr(a, model_key, val)

        flag = False
        for key in (
            "alergias",
            "medicamentos_uso_continuo",
            "historico_doencas",
        ):
            if getattr(a, key, None):
                flag = True
                break
        if not flag:
            for _k, v in form_data.items():
                if isinstance(v, str) and v.strip().lower() == "sim":
                    flag = True
                    break

        a.has_red_flags = bool(flag)
        a.status = AnamneseStatus.CONCLUIDA
        a.data_atualizacao = datetime.now(timezone.utc)

        db.session.add(p)
        db.session.add(a)
        db.session.commit()

        # Timeline (escrita dupla pós-transação)
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="CADASTRO",
                descricao="Dados cadastrais + Anamnese atualizados.",
                usuario_id=usuario_id,
                paciente_id=p.id,
            )
        except Exception:
            pass

        return p
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao atualizar ficha/anamnese: {exc}")
