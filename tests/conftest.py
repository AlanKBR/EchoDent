import os
import tempfile
from typing import Generator

import pytest

from app import create_app, db


@pytest.fixture(scope="session")
def app() -> Generator:
    # Create temporary SQLite files for default, users, and history binds
    def _temp_db_uri() -> str:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        return "sqlite:///" + path.replace("\\", "/")

    default_uri = _temp_db_uri()
    users_uri = _temp_db_uri()
    history_uri = _temp_db_uri()

    # Provide URIs to the app factory via environment variables
    os.environ["ECHO_TEST_DEFAULT_DB"] = default_uri
    os.environ["ECHO_TEST_USERS_DB"] = users_uri
    os.environ["ECHO_TEST_HISTORY_DB"] = history_uri

    _app = create_app("testing")

    with _app.app_context():
        # Create tables for default engine (tables without bind_key)
        default_tables = [
            t for t in db.metadata.tables.values()
            if t.info.get("bind_key") in (None, "", "default")
        ]
        if default_tables:
            db.metadata.create_all(bind=db.engine, tables=default_tables)

        # Create tables for each bind by filtering on table.info["bind_key"]
        for bind_key, engine in getattr(db, "engines", {}).items():
            bind_tables = [
                t for t in db.metadata.tables.values()
                if t.info.get("bind_key") == bind_key
            ]
            if bind_tables:
                db.metadata.create_all(bind=engine, tables=bind_tables)

        # Ensure 'usuarios' (users bind) exists even if on a different MetaData
        try:
            from app.models import Usuario  # type: ignore

            engine = getattr(db, "engines", {}).get("users")
            if engine is not None:
                table = getattr(Usuario, "__table__", None)
                if table is not None:
                    table.create(bind=engine, checkfirst=True)
        except Exception:
            pass

        # Ensure 'log_auditoria' (history bind) exists
        try:
            from app.models import LogAuditoria  # type: ignore

            engine = getattr(db, "engines", {}).get("history")
            if engine is not None:
                table = getattr(LogAuditoria, "__table__", None)
                if table is not None:
                    table.create(bind=engine, checkfirst=True)
        except Exception:
            pass

    yield _app

    # Teardown: drop all tables and remove temp files
    with _app.app_context():
        # Drop tables for binds first, then default
        for bind_key, engine in getattr(db, "engines", {}).items():
            bind_tables = [
                t for t in db.metadata.tables.values()
                if t.info.get("bind_key") == bind_key
            ]
            if bind_tables:
                db.metadata.drop_all(bind=engine, tables=bind_tables)

        # Drop 'usuarios' explicitly from users bind if present
        try:
            from app.models import Usuario  # type: ignore

            engine = getattr(db, "engines", {}).get("users")
            if engine is not None:
                table = getattr(Usuario, "__table__", None)
                if table is not None:
                    table.drop(bind=engine, checkfirst=True)
        except Exception:
            pass

        # Drop 'log_auditoria' explicitly from history bind if present
        try:
            from app.models import LogAuditoria  # type: ignore

            engine = getattr(db, "engines", {}).get("history")
            if engine is not None:
                table = getattr(LogAuditoria, "__table__", None)
                if table is not None:
                    table.drop(bind=engine, checkfirst=True)
        except Exception:
            pass

        default_tables = [
            t for t in db.metadata.tables.values()
            if t.info.get("bind_key") in (None, "", "default")
        ]
        if default_tables:
            db.metadata.drop_all(bind=db.engine, tables=default_tables)

    # Cleanup environments and files
    for key in (
        "ECHO_TEST_DEFAULT_DB",
        "ECHO_TEST_USERS_DB",
        "ECHO_TEST_HISTORY_DB",
    ):
        os.environ.pop(key, None)

    # Remove temp files
    for uri in (default_uri, users_uri, history_uri):
        path = uri.replace("sqlite:///", "").replace("/", os.sep)
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    # Provide direct access to the session for tests
    with app.app_context():
        yield db.session
