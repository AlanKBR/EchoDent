def test_post_buscar_cep_returns_html(client, monkeypatch):
    # Autenticar dev
    client.get("/__dev/login_as/admin")
    # Mock serviço interno para evitar chamada externa
    from app.blueprints import api_bp as api_module

    def fake_fetch(cep: str):
        return {
            "cep": "01310100",
            "logradouro": "Av. Paulista",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "estado": "SP",
        }

    monkeypatch.setattr(api_module, "_fetch_cep_raw", fake_fetch)

    resp = client.post("/api/buscar-cep", data={"cep": "01310-100"})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    # Deve conter HTML com campos preenchidos
    assert "input" in body
    assert "Av. Paulista" in body
    assert "Bela Vista" in body
    assert "São Paulo" in body
    assert "SP" in body
