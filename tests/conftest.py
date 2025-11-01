import pytest
from dotenv import load_dotenv
from sqlalchemy import event

from app import create_app, db


@pytest.fixture
def app_ctx():
    """Provide an application context for service-level integration tests.

    Outside HTTP requests, the before_request hook that sets search_path
    doesn't run. Ensure tenant routing explicitly for tests.
    """
    # Load environment variables before app creation
    try:
        load_dotenv()
    except Exception:
        pass

    app = create_app("testing")
    with app.app_context():
        # Ensure search_path on ALL pooled connections for this app
        try:
            @event.listens_for(db.engine, "connect")
            def _set_search_path(dbapi_connection, _):  # noqa: ANN001
                try:
                    cur = dbapi_connection.cursor()
                    cur.execute("SET search_path TO tenant_default, public")
                    cur.close()
                except Exception:
                    pass
        except Exception:
            pass
        yield
