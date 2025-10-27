from __future__ import annotations

from flask import json
from app import db
from app.models import Paciente


def _login_dev_admin(client):
    # Ensure logged-in session using dev endpoint (enabled in TESTING)
    r = client.get("/__dev/login_as/admin")
    assert r.status_code in (200, 302)


def _login_dev_user(client):
    r = client.get("/__dev/login_as/dentista")
    assert r.status_code in (200, 302)


def _create_paciente_for_routes() -> int:
    p = Paciente()
    p.nome_completo = "Paciente Snapshot"
    db.session.add(p)
    db.session.commit()
    return p.id


def test_odontograma_get_endpoint_returns_json(client, monkeypatch):
    _login_dev_admin(client)

    sample = {"11": {"status": "presente"}, "12": {"status": "ausente"}}

    def fake_get_estado(paciente_id: int):  # noqa: ANN001
        assert isinstance(paciente_id, int)
        return sample

    from app.services import odontograma_service

    monkeypatch.setattr(
        odontograma_service, "get_estado_odontograma_completo", fake_get_estado
    )

    resp = client.get("/paciente/1/odontograma_estado")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == sample


def test_odontograma_post_bulk_endpoint_calls_service(client, monkeypatch):
    _login_dev_admin(client)

    called = {"flag": False, "args": None}

    def fake_bulk(
        paciente_id: int, updates_map, usuario_id: int
    ):  # noqa: ANN001
        called["flag"] = True
        called["args"] = (paciente_id, updates_map, usuario_id)
        return True

    from app.services import odontograma_service

    monkeypatch.setattr(
        odontograma_service, "update_odontograma_bulk", fake_bulk
    )

    payload = {"21": {"status": "presente"}, "22": {"status": "ausente"}}
    resp = client.post(
        "/paciente/1/odontograma_estado/bulk",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("success") is True
    assert called["flag"] is True
    pac_id, updates, user_id = called["args"]
    assert pac_id == 1
    assert updates == payload
    assert isinstance(user_id, int)


def test_snapshot_routes_user_vs_admin(client):
    # Create a patient
    pid = _create_paciente_for_routes()

    # Regular user cannot force overwrite; can create initial snapshot once
    _login_dev_user(client)
    r1 = client.post(f"/paciente/{pid}/odontograma_snapshot")
    assert r1.status_code == 200
    # Second attempt without force should fail (service validation)
    r2 = client.post(f"/paciente/{pid}/odontograma_snapshot")
    assert r2.status_code == 400
    # Force endpoint should redirect due to admin_required
    r3 = client.post(f"/paciente/{pid}/odontograma_snapshot/force")
    assert r3.status_code in (302, 303)

    # Admin: second normal snapshot still fails
    _login_dev_admin(client)
    r4 = client.post(f"/paciente/{pid}/odontograma_snapshot")
    assert r4.status_code == 400
    # Admin forced snapshot should succeed
    r5 = client.post(f"/paciente/{pid}/odontograma_snapshot/force")
    assert r5.status_code == 200
