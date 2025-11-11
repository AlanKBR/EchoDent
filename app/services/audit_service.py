"""
Serviço de Auditoria - EchoDent
Gerencia logs de auditoria para rastreamento de mudanças críticas.
"""

from datetime import datetime

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from app.models import LogAuditoria, db


def list_audit_logs(
    page: int = 1,
    per_page: int = 30,
    user_id: int | None = None,
    model_name: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """
    Lista logs de auditoria com filtros e paginação.

    Args:
        page: Número da página (1-indexed)
        per_page: Registros por página
        user_id: Filtro por usuário
        model_name: Filtro por tabela (ex: 'procedimento_mestre')
        action: Filtro por ação (create, update, delete)
        date_from: Data inicial (datetime)
        date_to: Data final (datetime)

    Returns:
        Pagination object do SQLAlchemy
    """
    try:
        query = (
            db.session.query(LogAuditoria)
            .options(joinedload(LogAuditoria.user))
            .order_by(desc(LogAuditoria.timestamp))
        )

        # Aplicar filtros
        if user_id:
            query = query.filter(LogAuditoria.user_id == user_id)

        if model_name:
            query = query.filter(LogAuditoria.model_name == model_name)

        if action:
            query = query.filter(LogAuditoria.action == action)

        if date_from:
            query = query.filter(LogAuditoria.timestamp >= date_from)

        if date_to:
            query = query.filter(LogAuditoria.timestamp <= date_to)

        # Paginar
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return pagination

    except Exception as e:
        current_app.logger.error(f"Erro ao listar logs de auditoria: {e}")
        return None


def get_audit_log_by_id(log_id: int) -> LogAuditoria | None:
    """
    Retorna um log de auditoria específico com detalhes completos.

    Args:
        log_id: ID do log

    Returns:
        LogAuditoria ou None
    """
    try:
        log = (
            db.session.query(LogAuditoria)
            .options(joinedload(LogAuditoria.user))
            .filter(LogAuditoria.id == log_id)
            .first()
        )
        return log
    except Exception as e:
        current_app.logger.error(
            f"Erro ao buscar log de auditoria {log_id}: {e}"
        )
        return None


def get_recent_changes(limit: int = 10) -> list[LogAuditoria]:
    """
    Retorna as mudanças mais recentes (para timeline).

    Args:
        limit: Número máximo de registros

    Returns:
        Lista de LogAuditoria
    """
    try:
        logs = (
            db.session.query(LogAuditoria)
            .options(joinedload(LogAuditoria.user))
            .order_by(desc(LogAuditoria.timestamp))
            .limit(limit)
            .all()
        )
        return logs
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar mudanças recentes: {e}")
        return []


def get_settings_changes(limit: int = 10) -> list[LogAuditoria]:
    """
    Retorna mudanças recentes em configurações (para Admin).

    Args:
        limit: Número máximo de registros

    Returns:
        Lista de LogAuditoria filtrada por tabelas de configuração
    """
    try:
        # Tabelas de configurações a monitorar
        config_tables = [
            "clinica_info",
            "global_setting",
            "usuarios",
            "procedimento_mestre",
        ]

        logs = (
            db.session.query(LogAuditoria)
            .options(joinedload(LogAuditoria.user))
            .filter(LogAuditoria.model_name.in_(config_tables))
            .order_by(desc(LogAuditoria.timestamp))
            .limit(limit)
            .all()
        )
        return logs
    except Exception as e:
        current_app.logger.error(
            f"Erro ao buscar mudanças de configurações: {e}"
        )
        return []


def format_action_name(action: str) -> str:
    """
    Formata o nome da ação para exibição.

    Args:
        action: Nome da ação (create, update, delete)

    Returns:
        Nome formatado em português
    """
    action_map = {
        "create": "Criação",
        "update": "Atualização",
        "delete": "Exclusão",
        "UPDATE_MASSA": "Ajuste em Massa",
    }
    return action_map.get(action, action.title())


def format_model_name(model_name: str) -> str:
    """
    Formata o nome do modelo para exibição.

    Args:
        model_name: Nome da tabela (ex: 'procedimento_mestre')

    Returns:
        Nome formatado em português
    """
    model_map = {
        "clinica_info": "Dados da Clínica",
        "global_setting": "Configuração Global",
        "usuarios": "Usuários",
        "procedimento_mestre": "Tratamentos",
        "plano_tratamento": "Planos de Tratamento",
        "lancamento_financeiro": "Lançamentos Financeiros",
    }
    return model_map.get(model_name, model_name.replace("_", " ").title())
