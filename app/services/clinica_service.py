"""Service para gerenciar informações da clínica (singleton).

Regras:
- ClinicaInfo é um singleton (sempre id=1 no schema public)
- Atomicidade mandatória (try/commit/rollback)
- Sanitização de inputs de texto livre
- Upload de logos via storage_service
"""

from __future__ import annotations

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import ClinicaInfo, db
from app.utils.sanitization import sanitizar_input


def get_clinica_info() -> ClinicaInfo | None:
    """Retorna o registro singleton de ClinicaInfo (id=1)."""
    return db.session.get(ClinicaInfo, 1)


def get_or_create_clinica_info() -> ClinicaInfo:
    """Retorna ou cria o registro singleton de ClinicaInfo."""
    info = get_clinica_info()
    if info is None:
        try:
            info = ClinicaInfo(id=1)
            db.session.add(info)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar ClinicaInfo: {e}")
            raise
    return info


# ============================================================================
# Rollback / Undo (Fase 4.2)
# ============================================================================


def save_previous_state(info: ClinicaInfo) -> None:
    """
    Salva snapshot do estado atual no campo previous_state.

    Args:
        info: Instância de ClinicaInfo
    """
    from datetime import datetime, timezone

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "nome_clinica": info.nome_clinica,
            "cnpj": info.cnpj,
            "cro_clinica": info.cro_clinica,
            "telefone": info.telefone,
            "email": info.email,
            "cep": info.cep,
            "logradouro": info.logradouro,
            "numero": info.numero,
            "complemento": info.complemento,
            "bairro": info.bairro,
            "cidade": info.cidade,
            "estado": info.estado,
            "horario_funcionamento": info.horario_funcionamento,
        },
    }
    info.previous_state = snapshot


def rollback_clinica_info() -> dict:
    """
    Desfaz a última atualização da ClinicaInfo.

    Returns:
        dict com {'success': bool, 'message': str}
    """
    try:
        info = get_or_create_clinica_info()

        if not info.previous_state:
            return {
                "success": False,
                "message": "Nenhum estado anterior disponível para desfazer.",
            }

        # Restaurar dados do snapshot
        previous_data = info.previous_state.get("data", {})

        for field, value in previous_data.items():
            setattr(info, field, value)

        # Limpar previous_state após rollback
        info.previous_state = None

        db.session.commit()

        return {
            "success": True,
            "message": "✅ Configurações restauradas ao estado anterior.",
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao executar rollback: {e}")
        return {
            "success": False,
            "message": "❌ Erro ao desfazer alterações.",
        }


def update_clinica_info(data: dict) -> dict:
    """Atualiza informações da clínica de forma atômica.

    Args:
        data: Dicionário com campos para atualizar
              (nome_clinica, cnpj, cro_clinica, telefone, email,
               cep, logradouro, numero, complemento, bairro, cidade, estado,
               horario_funcionamento)

    Returns:
        dict com {
            'success': bool,
            'record_id': int,
            'previous_state': dict (apenas se success=True)
        }
    """
    print(f"\n🔹 update_clinica_info CHAMADA. Data keys: {list(data.keys())}")
    try:
        info = get_or_create_clinica_info()
        print(f"🔹 ClinicaInfo obtida. ID: {info.id}")

        # Salvar estado anterior para rollback (Fase 4.2)
        save_previous_state(info)
        print("🔹 Previous state salvo")

        # Campos de texto livre (sanitizar)
        text_fields = [
            "nome_clinica",
            "cnpj",
            "cro_clinica",
            "telefone",
            "email",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
        ]
        for field in text_fields:
            if field in data:
                value = data.get(field, "").strip()
                sanitized = sanitizar_input(value) if value else None
                setattr(info, field, sanitized)

        # Horário de funcionamento (JSON) - já vem processado do form
        if "horario_funcionamento" in data:
            info.horario_funcionamento = data["horario_funcionamento"]

        db.session.commit()

        # Retornar dados para rollback
        return {
            "success": True,
            "record_id": info.id,
            "previous_state": info.previous_state,
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"\n❌ SQLAlchemyError: {str(e)}\nType: {type(e)}\n")
        current_app.logger.error(
            "Erro ao atualizar ClinicaInfo: %s | Type: %s", str(e), type(e)
        )
        return {"success": False}
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Exception inesperada: {str(e)}\nType: {type(e)}\n")
        import traceback

        traceback.print_exc()
        current_app.logger.error(
            "Erro inesperado ao atualizar ClinicaInfo: %s | Type: %s",
            str(e),
            type(e),
        )
        return {"success": False}


def update_logo_path(logo_type: str, file_path: str | None) -> bool:
    """Atualiza o caminho de um arquivo de logo.

    Args:
        logo_type: Tipo do logo
                   ('cabecalho', 'rodape', 'marca_dagua', 'favicon')
        file_path: Caminho relativo do arquivo ou None para remover

    Returns:
        True se atualização bem-sucedida, False caso contrário.
    """
    field_map = {
        "cabecalho": "logo_cabecalho_path",
        "rodape": "logo_rodape_path",
        "marca_dagua": "marca_dagua_path",
        "favicon": "favicon_path",
    }

    if logo_type not in field_map:
        current_app.logger.error(f"Tipo de logo inválido: {logo_type}")
        return False

    try:
        info = get_or_create_clinica_info()
        setattr(info, field_map[logo_type], file_path)
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar logo path: {e}")
        return False


# ============================================================================
# Status de Completude (Fase 4.3)
# ============================================================================


def get_config_completeness() -> dict:
    """
    Calcula a completude da configuração da clínica.

    Returns:
        dict com {
            'percentage': int (0-100),
            'total_items': int,
            'completed_items': int,
            'checklist': [
                {'label': str, 'completed': bool, 'items': [...]},
                ...
            ]
        }
    """
    try:
        info = get_or_create_clinica_info()  # Garantir que sempre retorna info
    except Exception as e:
        current_app.logger.error(f"Erro ao obter info da clínica: {e}")
        info = None

    if not info:
        return {
            "percentage": 0,
            "total_items": 0,
            "completed_items": 0,
            "checklist": [],
        }

    # Definir checklist de itens
    checklist = [
        {
            "label": "Dados Empresariais",
            "items": [
                {
                    "name": "Nome da Clínica",
                    "completed": bool(info.nome_clinica),
                },
                {"name": "CNPJ", "completed": bool(info.cnpj)},
                {"name": "Telefone", "completed": bool(info.telefone)},
                {"name": "Email", "completed": bool(info.email)},
            ],
        },
        {
            "label": "Endereço",
            "items": [
                {"name": "CEP", "completed": bool(info.cep)},
                {"name": "Logradouro", "completed": bool(info.logradouro)},
                {"name": "Número", "completed": bool(info.numero)},
                {"name": "Bairro", "completed": bool(info.bairro)},
                {"name": "Cidade", "completed": bool(info.cidade)},
                {"name": "Estado", "completed": bool(info.estado)},
            ],
        },
        {
            "label": "Identidade Visual",
            "items": [
                {
                    "name": "Logo Cabeçalho",
                    "completed": bool(info.logo_cabecalho_path),
                },
                {
                    "name": "Logo Rodapé",
                    "completed": bool(info.logo_rodape_path),
                },
                {"name": "Favicon", "completed": bool(info.favicon_path)},
            ],
        },
        {
            "label": "Horário de Funcionamento",
            "items": [
                {
                    "name": "Horários Configurados",
                    "completed": bool(
                        info.horario_funcionamento
                        and isinstance(info.horario_funcionamento, dict)
                        and any(info.horario_funcionamento.values())
                    ),
                },
            ],
        },
    ]

    # Calcular completude
    try:
        total_items = sum(len(section["items"]) for section in checklist)
        completed_items = sum(
            sum(1 for item in section["items"] if item["completed"])
            for section in checklist
        )

        # Adicionar status de completude por seção
        for section in checklist:
            section_completed = sum(
                1 for item in section["items"] if item["completed"]
            )
            section_total = len(section["items"])
            section["completed"] = section_completed == section_total
            section["partial"] = 0 < section_completed < section_total

        if total_items > 0:
            percentage = int((completed_items / total_items) * 100)
        else:
            percentage = 0

        return {
            "percentage": percentage,
            "total_items": total_items,
            "completed_items": completed_items,
            "checklist": checklist,
        }
    except Exception as e:
        current_app.logger.error(f"Erro ao calcular completude: {e}")
        # Retornar estado vazio em caso de erro
        return {
            "percentage": 0,
            "total_items": 0,
            "completed_items": 0,
            "checklist": [],
        }
