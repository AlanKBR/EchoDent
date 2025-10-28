from flask import request

from app import db
from app.services import log_service
from app.models import DeveloperLog


def _create_log_entry(app, path="/boom", body="{\"x\":1}", method="POST"):
    """Helper: create a DeveloperLog via the service using a real
    request context.
    """
    with app.test_request_context(
        path,
        method=method,
        data=body,
        content_type="application/json",
    ):
        try:
            raise ValueError("Test error")
        except Exception as e:
            # user_id arbitrário de teste
            log_service.record_exception(e, request, user_id=123)


def test_admin_configuracoes_access(client, app):
    # Admin can access
    client.get("/__dev/login_as/admin")
    resp = client.get("/admin/configuracoes")
    assert resp.status_code == 200

    # Non-admin is denied
    client.get("/__dev/login_as/secretaria")
    resp2 = client.get("/admin/configuracoes")
    assert resp2.status_code in (302, 403)


def test_admin_devlogs_list_and_detail(client, app):
    client.get("/__dev/login_as/admin")

    # Ensure at least one log exists
    with app.app_context():
        _create_log_entry(app, path="/boom1", body="{\"hello\":\"world\"}")
        # Fetch one to get its id
        log_obj = (
            db.session.query(DeveloperLog)
            .order_by(DeveloperLog.id.desc())
            .first()
        )
        assert log_obj is not None
        log_id = log_obj.id

    # List page
    list_resp = client.get("/admin/devlogs")
    assert list_resp.status_code == 200

    # Detail page for existing log
    detail_resp = client.get(f"/admin/devlogs/{log_id}")
    assert detail_resp.status_code == 200
    assert (
        b"ValueError" in detail_resp.data
        or b"Test error" in detail_resp.data
    )

    # Detail page for non-existing log -> 404
    not_found_resp = client.get("/admin/devlogs/999999")
    assert not_found_resp.status_code == 404


def test_admin_devlogs_purge(client, app):
    client.get("/__dev/login_as/admin")

    # Create a couple of logs
    with app.app_context():
        _create_log_entry(app, path="/boom2", body="{}")
        _create_log_entry(app, path="/boom3", body="{}")

        count_before = db.session.query(DeveloperLog).count()
        assert count_before >= 2

    # Purge
    purge_resp = client.post("/admin/devlogs/purge")
    assert purge_resp.status_code in (200, 204)
    # HX-Redirect header used for HTMX redirect
    assert "HX-Redirect" in dict(purge_resp.headers)

    # Verify all logs deleted
    with app.app_context():
        count_after = db.session.query(DeveloperLog).count()
        assert count_after == 0
