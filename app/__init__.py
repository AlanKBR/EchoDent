import os
from importlib import import_module
from typing import Optional

from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

# Extensões globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(_config_name: Optional[str] = None) -> Flask:
    """Application Factory.

    Inicializa Flask, SQLAlchemy, Migrate, configura concorrência para SQLite
    (WAL) e registra blueprints. O parâmetro `_config_name` é aceito para
    compatibilidade com chamadas existentes, mas atualmente não é utilizado.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Carregar Config
    from .config import Config

    app.config.from_object(Config)
    # Testing overrides via env for ephemeral DBs in tests
    if _config_name == "testing":
        app.config["TESTING"] = True
        # Allow tests to inject DB URIs via env to avoid polluting real DBs
        test_default = os.environ.get("ECHO_TEST_DEFAULT_DB")
        test_users = os.environ.get("ECHO_TEST_USERS_DB")
        test_history = os.environ.get("ECHO_TEST_HISTORY_DB")
        test_cal = os.environ.get("ECHO_TEST_CALENDARIO_DB")
        if test_default:
            app.config["SQLALCHEMY_DATABASE_URI"] = test_default
        if test_users or test_history:
            binds = dict(app.config.get("SQLALCHEMY_BINDS", {}))
            if test_users:
                binds["users"] = test_users
            if test_history:
                binds["history"] = test_history
            app.config["SQLALCHEMY_BINDS"] = binds
        # Calendário bind override (used by agenda tests)
        if test_cal:
            binds = dict(app.config.get("SQLALCHEMY_BINDS", {}))
            binds["calendario"] = test_cal
            app.config["SQLALCHEMY_BINDS"] = binds

    # Garantir diretórios de instância e de mídia
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    media_dir = os.path.join(app.instance_path, "media_storage")
    try:
        os.makedirs(media_dir, exist_ok=True)
    except OSError:
        pass

    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # Optional: route name to redirect anonymous users
    try:
        login_manager.login_view = 'auth_bp.login'  # type: ignore[assignment]
    except Exception:
        pass

    # Configuração de concorrência para SQLite: PRAGMA journal_mode=WAL
    def _wal_listener():
        def _set_wal(dbapi_connection, _):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
            except Exception:
                # Ignora conexões não SQLite
                pass

        return _set_wal

    # Anexa listeners a todos os engines (padrão + binds)
    with app.app_context():
        engines = []
        try:
            engines.append(db.engine)
        except Exception:
            pass
        try:
            # Flask‑SQLAlchemy expõe todos engines em `db.engines`
            engines.extend(getattr(db, "engines", {}).values())
        except Exception:
            pass

        for eng in engines:
            event.listen(eng, "connect", _wal_listener())

    # Registro de Blueprints (se existirem)
    bp_specs = [
        ("app.blueprints.auth_bp", "auth_bp"),
        ("app.blueprints.core_bp", "core_bp"),
        ("app.blueprints.agendamento_bp", "agendamento_bp"),
        ("app.blueprints.paciente_bp", "paciente_bp"),
        ("app.blueprints.financeiro_bp", "financeiro_bp"),
        ("app.blueprints.agenda_bp", "agenda_bp"),
    ]
    for module_name, attr_name in bp_specs:
        try:
            mod = import_module(module_name)
            bp = getattr(mod, "bp", None) or getattr(mod, attr_name, None)
            if bp is not None:
                app.register_blueprint(bp)
        except Exception:
            # Módulo ainda sem blueprint definido: ignora no scaffold
            pass

    # Imports finais (garante modelos e eventos registrados)
    try:
        from . import models  # noqa: F401
    except Exception:
        pass
    try:
        from . import events  # noqa: F401
    except Exception:
        pass

    # Context processor: lightweight cache busting for static assets
    @app.context_processor
    def inject_asset_version():  # pragma: no cover - trivial
        try:
            ver = os.environ.get("ASSET_VERSION")
            if not ver:
                ver = app.config.get("ASSET_VERSION")
            if not ver:
                ver = "dev"
        except Exception:
            ver = "dev"
        return {"asset_v": ver}

    return app


@login_manager.user_loader
def load_user(user_id: str):  # pragma: no cover - thin wrapper
    try:
        # Local import to avoid circulars at import time
        from .models import Usuario  # type: ignore
        return db.session.get(Usuario, int(user_id))
    except Exception:
        return None
