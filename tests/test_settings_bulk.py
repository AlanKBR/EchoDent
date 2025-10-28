from app import db
from app.models import GlobalSetting


def test_settings_bulk_whitelist_and_atomicity(client, app):
    # Login como admin (dev-only route enabled in testing)
    client.get("/__dev/login_as/admin")

    # Envia formulário com uma chave válida e uma inválida
    resp = client.post(
        "/admin/configuracoes/update",
        data={
            "DEV_LOGS_ENABLED": "true",
            "malicious_key": "pwned",
        },
    )
    # 204 No Content esperado com HX-Redirect (não verificamos cabeçalho aqui)
    assert resp.status_code in (200, 204)

    # Verificações no banco
    with app.app_context():
        devlogs = db.session.get(GlobalSetting, "DEV_LOGS_ENABLED")
        assert devlogs is not None
        assert (devlogs.value or "").strip().lower() == "true"

        malicious = db.session.get(GlobalSetting, "malicious_key")
        assert malicious is None
