"""
Service para gerenciamento de API Keys
---------------------------------------
Responsável por CRUD de chaves de API (BrasilAPI, gateways de pagamento, etc.)
armazenadas na tabela GlobalSetting (schema public).

Regras:
- Chaves armazenadas em texto plano (sem criptografia, conforme AGENTS.MD)
- Prefixo "API_" para todas as keys (ex: API_BRASILAPI_TOKEN)
- Sanitização obrigatória de valores via sanitizar_input()
- Função test_api_connection() para validação ao vivo
"""

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import GlobalSetting
from app.utils.sanitization import sanitizar_input

# Constantes para nomes fixos de API keys
API_KEY_BRASILAPI = "API_BRASILAPI_TOKEN"
API_KEY_GATEWAY_PAGAMENTO = "API_GATEWAY_PAGAMENTO_TOKEN"
API_KEY_GATEWAY_PAGAMENTO_SECRET = "API_GATEWAY_PAGAMENTO_SECRET"

KNOWN_API_KEYS = [
    API_KEY_BRASILAPI,
    API_KEY_GATEWAY_PAGAMENTO,
    API_KEY_GATEWAY_PAGAMENTO_SECRET,
]


def get_api_key(key_name: str) -> str | None:
    """
    Busca uma API key do banco de dados.

    Args:
        key_name: Nome da chave (ex: "API_BRASILAPI_TOKEN")

    Returns:
        str ou None se a chave não existir ou estiver vazia
    """
    try:
        setting = GlobalSetting.query.filter_by(key=key_name).first()
        if setting and setting.value:
            return setting.value
        return None
    except SQLAlchemyError as e:
        current_app.logger.error(f"Erro ao buscar API key {key_name}: {e}")
        return None


def set_api_key(key_name: str, value: str | None) -> bool:
    """
    Salva ou atualiza uma API key no banco de dados.

    Args:
        key_name: Nome da chave (ex: "API_BRASILAPI_TOKEN")
        value: Valor (sanitizado).
            Se None a chave é removida.

    Returns:
        bool: True se salvou com sucesso, False em caso de erro
    """
    try:
        # Sanitização obrigatória (AGENTS.MD)
        if value:
            value = sanitizar_input(value)

        # Buscar setting existente
        setting = GlobalSetting.query.filter_by(key=key_name).first()

        if value is None or value.strip() == "":
            # Remover chave (se existir)
            if setting:
                db.session.delete(setting)
                db.session.commit()
                current_app.logger.info(f"API key removida: {key_name}")
            return True

        # Criar ou atualizar
        if setting:
            setting.value = value
            current_app.logger.info(f"API key atualizada: {key_name}")
        else:
            # Criar novo registro
            setting = GlobalSetting()
            setting.key = key_name
            setting.value = value
            db.session.add(setting)
            current_app.logger.info(f"API key criada: {key_name}")

        db.session.commit()
        return True

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar API key {key_name}: {e}")
        return False


def test_api_connection(api_name: str) -> dict:
    """
    Testa a conexão com uma API externa usando a chave armazenada.

    Args:
        api_name: Identificador da API ("brasilapi", "gateway_pagamento")

    Returns:
        dict com:
            - 'success': bool
            - 'message': str (mensagem de sucesso ou erro)
            - 'details': dict opcional com dados de debug
    """
    import requests

    if api_name == "brasilapi":
        # BrasilAPI público: teste rápido com feriados
        try:
            response = requests.get(
                "https://brasilapi.com.br/api/feriados/v1/2025",
                timeout=5,
            )
            if response.status_code == 200:
                feriados = response.json()
                qtd = len(feriados)
                msg = f"Conexão OK! {qtd} feriados para 2025"
                return {
                    "success": True,
                    "message": msg,
                    "details": {"count": qtd},
                }
            else:
                return {
                    "success": False,
                    "message": f"Erro HTTP {response.status_code}",
                    "details": {"status": response.status_code},
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "Timeout: BrasilAPI não respondeu em 5 segundos",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Erro de conexão: {str(e)}",
            }

    elif api_name == "gateway_pagamento":
        # Gateway de pagamento (futuro, placeholder)
        token = get_api_key(API_KEY_GATEWAY_PAGAMENTO)
        if not token:
            return {
                "success": False,
                "message": "Token não configurado",
            }

        # TODO: Implementar teste real quando gateway estiver definido
        return {
            "success": False,
            "message": "Função de teste não implementada (API placeholder)",
            "details": {"token_exists": True},
        }

    else:
        return {
            "success": False,
            "message": f"API desconhecida: {api_name}",
        }


def list_api_keys() -> list[dict]:
    """
    Lista todas as API keys conhecidas com seus status.

    Returns:
        list[dict] com:
            - 'key_name': str
            - 'configured': bool (True se a chave existe e não está vazia)
            - 'masked_value': str (ex: "abc***xyz" para exibição segura)
    """
    result = []
    for key_name in KNOWN_API_KEYS:
        value = get_api_key(key_name)
        configured = value is not None and value.strip() != ""

        # Mascarar valor (exibir primeiros 3 e últimos 3 chars)
        masked_value = ""
        if configured and value:
            if len(value) > 10:
                masked_value = f"{value[:3]}***{value[-3:]}"
            else:
                masked_value = "***"  # Valor muito curto, ocultar totalmente

        result.append(
            {
                "key_name": key_name,
                "configured": configured,
                "masked_value": masked_value,
            }
        )

    return result
