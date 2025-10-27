from app import create_app
import pytest

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_dev_route_debug_true(client):
    # DEBUG True (via TESTING)
    resp = client.get("/__dev/login_as/admin")
    assert resp.status_code in (200, 302)

def test_dev_route_debug_false():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = False
    app.config['DEBUG'] = False
    with app.test_client() as client:
        resp = client.get("/__dev/login_as/admin")
        assert resp.status_code == 404
