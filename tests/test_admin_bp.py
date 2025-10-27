import pytest
from unittest.mock import patch, MagicMock
from flask import url_for

@pytest.fixture
def admin_client(client, app):
    # Simula login como admin
    client.get("/__dev/login_as/admin")
    yield client

@pytest.fixture
def user_client(client, app):
    # Simula login como usuário normal
    client.get("/__dev/login_as/user")
    yield client

def test_get_fechamento_caixa_form_admin(admin_client):
    resp = admin_client.get("/admin/caixa/fechar")
    assert resp.status_code == 200
    assert b"Data do Caixa" in resp.data
    assert b"Saldo Apurado" in resp.data

def test_post_fechamento_caixa_sucesso(admin_client):
    with patch("app.services.financeiro_service.fechar_caixa_dia") as mock_fechar:
        mock_fechar.return_value = MagicMock()
        resp = admin_client.post(
            "/admin/caixa/fechar",
            data={"data_caixa": "2025-10-26", "saldo_apurado": "123.45"},
            follow_redirects=True,
        )
        mock_fechar.assert_called_once()
        assert resp.status_code == 200
        assert b"Caixa fechado com sucesso" in resp.data

def test_post_fechamento_caixa_falha(admin_client):
    with patch("app.services.financeiro_service.fechar_caixa_dia") as mock_fechar:
        mock_fechar.side_effect = ValueError("Caixa já fechado")
        resp = admin_client.post(
            "/admin/caixa/fechar",
            data={"data_caixa": "2025-10-26", "saldo_apurado": "123.45"},
            follow_redirects=True,
        )
        mock_fechar.assert_called_once()
        assert resp.status_code == 200
        assert b"Caixa j\xc3\xa1 fechado" in resp.data or b"error" in resp.data

def test_fechamento_caixa_acesso_negado_user(user_client):
    # GET
    resp = user_client.get("/admin/caixa/fechar")
    assert resp.status_code in (302, 403)
    # POST
    resp2 = user_client.post(
        "/admin/caixa/fechar",
        data={"data_caixa": "2025-10-26", "saldo_apurado": "123.45"},
    )
    assert resp2.status_code in (302, 403)
