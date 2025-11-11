import pytest
from dotenv import load_dotenv
from sqlalchemy import event

from app import create_app, db


@pytest.fixture
def app():
    """Application fixture for pytest-flask 'client' support.

    Provides an app configured for testing and ensures search_path
    is set on all pooled connections.
    """
    try:
        load_dotenv()
    except Exception:
        pass

    app = create_app("testing")
    with app.app_context():
        try:

            @event.listens_for(db.engine, "connect")
            def _set_search_path_2(dbapi_connection, _):  # noqa: ANN001
                try:
                    cur = dbapi_connection.cursor()
                    cur.execute("SET search_path TO tenant_default, public")
                    cur.close()
                except Exception:
                    pass
        except Exception:
            pass
    return app


@pytest.fixture
def app_ctx(app):
    """Application context bound to the same app used by the Flask client.

    Avoids creating a second Flask instance which caused teardown conflicts.
    """
    with app.app_context():
        yield
