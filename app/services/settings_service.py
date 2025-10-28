from app.models import GlobalSetting, db
from app.utils.sanitization import sanitizar_input
from sqlalchemy.exc import SQLAlchemyError

# Whitelist de chaves de configuração permitidas
WHITELIST_KEYS = {
    "DEV_LOGS_ENABLED",
}


def get_all_settings():
    """Retorna todos os pares chave-valor de configurações globais."""
    settings = GlobalSetting.query.all()
    return [(s.key, s.value) for s in settings]


def update_setting(key: str, value: str):
    """
    Atualiza ou cria uma configuração global de forma atômica e sanitizada.
    """
    from flask import current_app
    session = db.session
    try:
        sanitized_value = sanitizar_input(value)
        setting = GlobalSetting.query.get(key)
        if setting:
            setting.value = sanitized_value
        else:
            setting = GlobalSetting()
            setting.key = key
            setting.value = sanitized_value
            session.add(setting)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        current_app.logger.error(f"Erro ao atualizar configuração: {e}")
        return False


def update_settings_bulk(settings_dict: dict) -> bool:
    """Atualiza várias configurações de forma atômica.

    Regras:
    - Apenas chaves na WHITELIST_KEYS são consideradas.
    - Sanitiza os valores com sanitizar_input.
    - Upsert por chave (cria ou atualiza).
    - Um único commit ao final; rollback em caso de erro.
    """
    from flask import current_app
    session = db.session
    try:
        for key, value in (settings_dict or {}).items():
            if key not in WHITELIST_KEYS:
                continue
            sanitized_value = sanitizar_input(value)
            setting = session.get(GlobalSetting, key)
            if setting is None:
                setting = GlobalSetting()
                setting.key = key
                setting.value = sanitized_value
                session.add(setting)
            else:
                setting.value = sanitized_value
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        try:
            current_app.logger.error(
                f"Erro ao atualizar configurações em lote: {e}"
            )
        except Exception:
            pass
        return False
