"""Service para gerenciar preferências individuais de usuários.

Regras:
- Uma entrada UserPreferences por usuário (tenant-scoped)
- Atomicidade mandatória (try/commit/rollback)
- Cada usuário só pode editar suas próprias preferências
"""

from __future__ import annotations

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import UserPreferences, Usuario, db


def get_user_preferences(usuario_id: int) -> UserPreferences | None:
    """Retorna as preferências de um usuário."""
    return UserPreferences.query.filter_by(usuario_id=usuario_id).first()


def get_or_create_user_preferences(usuario_id: int) -> UserPreferences:
    """Retorna ou cria as preferências de um usuário."""
    prefs = get_user_preferences(usuario_id)
    if prefs is None:
        try:
            # Valida que o usuário existe
            usuario = db.session.get(Usuario, usuario_id)
            if not usuario:
                raise ValueError(f"Usuário {usuario_id} não encontrado")

            prefs = UserPreferences(usuario_id=usuario_id)
            db.session.add(prefs)
            db.session.commit()
        except (SQLAlchemyError, ValueError) as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar UserPreferences: {e}")
            raise
    return prefs


def update_user_preferences(usuario_id: int, data: dict) -> bool:
    """Atualiza preferências do usuário de forma atômica.

    Args:
        usuario_id: ID do usuário
        data: Dicionário com campos para atualizar
              (notificacoes_enabled, ...)

    Returns:
        True se atualização bem-sucedida, False caso contrário.
    """
    try:
        prefs = get_or_create_user_preferences(usuario_id)

        # Notificações (boolean)
        if "notificacoes_enabled" in data:
            value = data.get("notificacoes_enabled")
            # Conversão robusta para bool
            if isinstance(value, str):
                prefs.notificacoes_enabled = value.lower() in [
                    "true",
                    "1",
                    "yes",
                    "on",
                ]
            else:
                prefs.notificacoes_enabled = bool(value)

        db.session.commit()
        return True
    except (SQLAlchemyError, ValueError) as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar UserPreferences: {e}")
        return False


def get_paciente_lista_colunas(usuario_id: int) -> dict:
    """Retorna a configuração de colunas da lista de pacientes.

    Se o usuário ainda não tiver preferências salvas, retorna um default
    robusto alinhado ao Conceito 2.
    """
    prefs = get_or_create_user_preferences(usuario_id)
    default_colunas = {
        "telefone": True,
        "email": True,
        "idade": False,
        "sexo": False,
        "data_ultimo_registro": True,
        "status_anamnese": True,
        "cpf": False,
        "cidade": False,
    }
    try:
        saved = prefs.paciente_lista_colunas or {}
        # merge defensivo: defaults prevalecem quando chave ausente
        merged = {**default_colunas, **(saved or {})}
        # garantir que apenas chaves conhecidas retornem
        sanitized = {k: bool(merged.get(k, False)) for k in default_colunas}
        return sanitized
    except Exception:
        return default_colunas


def update_paciente_lista_colunas(usuario_id: int, colunas: dict) -> bool:
    """Atualiza, de forma atômica, a configuração de colunas da lista.

    Apenas chaves suportadas são persistidas; converte valores "truthy"
    para booleanos reais.
    """
    allowed = {
        "telefone",
        "email",
        "idade",
        "sexo",
        "data_ultimo_registro",
        "status_anamnese",
        "cpf",
        "cidade",
    }
    try:
        prefs = get_or_create_user_preferences(usuario_id)
        to_save: dict[str, bool] = {}
        for key, val in (colunas or {}).items():
            if key in allowed:
                to_save[key] = bool(val)
        # merge com defaults para manter chaves estáveis
        current = prefs.paciente_lista_colunas or {}
        merged = {**current, **to_save}
        prefs.paciente_lista_colunas = merged
        db.session.commit()
        return True
    except (SQLAlchemyError, ValueError) as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro ao atualizar paciente_lista_colunas: {e}"
        )
        return False
