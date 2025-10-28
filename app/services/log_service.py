import traceback
from datetime import datetime, timedelta, timezone
from flask import Request
from .. import db
from ..models import DeveloperLog

MAX_BODY_LOG_CHARS = 4096


def record_exception(
    error: Exception,
    request: Request,
    user_id: int | None,
) -> None:
    """
    Grava uma exceção não tratada no banco de dados 'logs.db'.
    Esta função é chamada pelo handler global de erros.
    
    Aderência Mandatória: Regra 7.5 (Atomicidade).
    """
    try:
        # Extrai dados do erro e da requisição
        tb_string = traceback.format_exc()
        error_type_str = type(error).__name__

        # Captura robusta do corpo da requisição
        body_content = None
        if request:
            try:
                mt = (getattr(request, "mimetype", None) or "").lower()
                # Tipos binários comuns não devem ser logados
                if mt.startswith("image/") or mt in (
                    "application/pdf",
                    "application/octet-stream",
                ):
                    body_content = "[Corpo binário não logado]"
                else:
                    # Leitura segura e truncamento em 4KB
                    request_text = request.get_data(as_text=True)
                    body_content = (request_text or "")[:MAX_BODY_LOG_CHARS]
            except Exception as e_body:
                body_content = f"Falha ao ler o body: {e_body}"

        new_log = DeveloperLog()
        new_log.error_type = error_type_str
        new_log.traceback = tb_string
        new_log.request_url = request.url if request else 'N/A'
        new_log.request_method = request.method if request else 'N/A'
        new_log.user_id = user_id
        new_log.request_body = body_content

        # O modelo DeveloperLog já tem o __bind_key__ = 'logs',
        # então o SQLAlchemy direcionará automaticamente para o bind correto.
        db.session.add(new_log)
        db.session.commit()

    except Exception as e:
        # Se o próprio log falhar, faz rollback e imprime no console
        db.session.rollback()
        print(f"CRITICAL: Falha ao gravar log de erro no DB: {e}")
        print(f"Erro Original: {traceback.format_exc()}")


def purge_old_logs(days: int = 30) -> None:
    """
    Remove registros de log mais antigos que 'days' (padrão 30 dias).
    Esta função será chamada por um job agendado (APScheduler).

    Aderência Mandatória: Regra 7.5 (Atomicidade).
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # O SQLAlchemy usará o bind 'logs' automaticamente devido ao modelo
        logs_to_delete = db.session.query(DeveloperLog).filter(
            DeveloperLog.timestamp < cutoff_date
        )
        
        deleted_count = logs_to_delete.delete(synchronize_session=False)
        db.session.commit()
        
        print(f"Log Purge: {deleted_count} logs antigos removidos.")

    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL: Falha ao purgar logs antigos: {e}")


def get_logs_paginated(page: int, per_page: int):
    """
    Retorna logs paginados, ordenados do mais recente para o mais antigo.
    """
    query = DeveloperLog.query.order_by(DeveloperLog.timestamp.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_log_by_id(log_id: int):
    """
    Retorna um único DeveloperLog pelo ID.
    """
    return db.session.get(DeveloperLog, log_id)


def purge_all_logs():
    """
    Deleta todos os registros de DeveloperLog de forma atômica.
    Retorna True em caso de sucesso, False em caso de erro.
    """
    try:
        db.session.query(DeveloperLog).delete(synchronize_session=False)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL: Falha ao purgar todos os logs: {e}")
        return False
