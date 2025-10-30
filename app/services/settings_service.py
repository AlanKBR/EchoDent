from app.models import GlobalSetting, db
from app.utils.sanitization import sanitizar_input
from sqlalchemy.exc import SQLAlchemyError

# Whitelist de chaves de configuração permitidas (organizadas por categoria)
WHITELIST_KEYS = {
    # Sistema/Desenvolvimento
    "DEV_LOGS_ENABLED",
    
    # Tema/Aparência
    "THEME_PRIMARY_COLOR",
    "THEME_MODE_DEFAULT",
    
    # Clínica (Informações Gerais)
    "CLINIC_NAME",
    "CLINIC_PHONE",
    "CLINIC_EMAIL",
    "CLINIC_ADDRESS",
    "CLINIC_CNPJ",
    
    # Preferências do Sistema
    "DEFAULT_APPOINTMENT_DURATION",
    "ENABLE_NOTIFICATIONS",
    "CURRENCY_SYMBOL",
}

# Definições de configurações padrão com categorias e descrições
DEFAULT_SETTINGS = {
    "DEV_LOGS_ENABLED": {
        "value": "false",
        "category": "sistema",
        "description": "Ativar logs de desenvolvimento"
    },
    "THEME_PRIMARY_COLOR": {
        "value": "#10b981",
        "category": "tema",
        "description": "Cor primária do tema"
    },
    "THEME_MODE_DEFAULT": {
        "value": "light",
        "category": "tema",
        "description": "Modo de tema padrão (light/dark)"
    },
    "CLINIC_NAME": {
        "value": "",
        "category": "clinica",
        "description": "Nome da clínica"
    },
    "CLINIC_PHONE": {
        "value": "",
        "category": "clinica",
        "description": "Telefone da clínica"
    },
    "CLINIC_EMAIL": {
        "value": "",
        "category": "clinica",
        "description": "E-mail da clínica"
    },
    "CLINIC_ADDRESS": {
        "value": "",
        "category": "clinica",
        "description": "Endereço da clínica"
    },
    "CLINIC_CNPJ": {
        "value": "",
        "category": "clinica",
        "description": "CNPJ da clínica"
    },
    "DEFAULT_APPOINTMENT_DURATION": {
        "value": "30",
        "category": "preferencias",
        "description": "Duração padrão de consultas (minutos)"
    },
    "ENABLE_NOTIFICATIONS": {
        "value": "true",
        "category": "preferencias",
        "description": "Ativar notificações do sistema"
    },
    "CURRENCY_SYMBOL": {
        "value": "R$",
        "category": "preferencias",
        "description": "Símbolo da moeda"
    },
}


def get_all_settings():
    """Retorna todos os pares chave-valor de configurações globais organizados por categoria."""
    settings = GlobalSetting.query.all()
    settings_dict = {}
    
    for s in settings:
        category = s.category or "geral"
        if category not in settings_dict:
            settings_dict[category] = []
        settings_dict[category].append({
            "key": s.key,
            "value": s.value,
            "description": s.description
        })
    
    return settings_dict


def get_setting(key: str, default=None):
    """Retorna o valor de uma configuração específica."""
    setting = GlobalSetting.query.get(key)
    if setting:
        return setting.value
    return default


def initialize_default_settings():
    """Inicializa configurações padrão se não existirem."""
    from flask import current_app
    session = db.session
    try:
        for key, config in DEFAULT_SETTINGS.items():
            existing = session.get(GlobalSetting, key)
            if existing is None:
                setting = GlobalSetting()
                setting.key = key
                setting.value = config["value"]
                setting.category = config["category"]
                setting.description = config["description"]
                session.add(setting)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        try:
            current_app.logger.error(f"Erro ao inicializar configurações padrão: {e}")
        except Exception:
            pass
        return False


def update_setting(key: str, value: str, category: str = None, description: str = None):
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
            if category:
                setting.category = category
            if description:
                setting.description = description
        else:
            setting = GlobalSetting()
            setting.key = key
            setting.value = sanitized_value
            setting.category = category or "geral"
            setting.description = description
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
