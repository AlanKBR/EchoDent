import os
from importlib import import_module
from typing import Any, Optional

from flask import Flask, render_template, request
from flask_apscheduler import APScheduler
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Extensões globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
# Scheduler global
scheduler = APScheduler()

# Optional service reference for error logging; may remain None in some envs
log_service: Optional[Any] = None


def create_app(_config_name: str | None = None) -> Flask:
    """Application Factory.

    Inicializa Flask, SQLAlchemy, Migrate, configura concorrência para SQLite
    (WAL) e registra blueprints. O parâmetro `_config_name` é aceito para
    compatibilidade com chamadas existentes, mas atualmente não é utilizado.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Carregar Config
    from .config import Config

    app.config.from_object(Config)
    # Ensure a secret key for sessions in dev/test
    if not app.config.get("SECRET_KEY"):
        # Short dev fallback secret; safe only for development/testing
        app.config["SECRET_KEY"] = os.environ.get(
            "SECRET_KEY", "dev-secret-key"
        )
    # Testing overrides via env for ephemeral DBs in tests
    if _config_name == "testing":
        app.config["TESTING"] = True
        # Enable debug routes during testing to expose dev-only endpoints
        app.debug = True
        # Allow tests to inject DB URIs via env to avoid polluting real DBs
        test_default = os.environ.get("ECHO_TEST_DEFAULT_DB")
        test_users = os.environ.get("ECHO_TEST_USERS_DB")
        test_history = os.environ.get("ECHO_TEST_HISTORY_DB")
        test_logs = os.environ.get("ECHO_TEST_LOGS_DB")
        test_cal = os.environ.get("ECHO_TEST_CALENDARIO_DB")
        if test_default:
            app.config["SQLALCHEMY_DATABASE_URI"] = test_default
        if test_users or test_history or test_logs:
            binds = dict(app.config.get("SQLALCHEMY_BINDS", {}))
            if test_users:
                binds["users"] = test_users
            if test_history:
                binds["history"] = test_history
            if test_logs:
                binds["logs"] = test_logs
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

    # Registrar comandos de CLI (ex.: dev-sync-db)
    try:
        from .cli import register_cli  # type: ignore

        register_cli(app)
    except Exception:
        pass
    # Optional: route name to redirect anonymous users
    try:
        login_manager.login_view = "auth_bp.login"  # type: ignore[assignment]
    except Exception:
        pass

    # Inicializar APScheduler (evitar reconfigurar quando já estiver em exec.)
    try:
        _underlying = getattr(scheduler, "_scheduler", None)
        state = getattr(_underlying, "state", None)
        is_running = bool(_underlying and state not in (None, 0))
    except Exception:
        is_running = False

    # Respeitar flag DISABLE_SCHEDULER para testes E2E
    if os.environ.get("DISABLE_SCHEDULER") == "1":
        app.logger.info("Scheduler desabilitado (DISABLE_SCHEDULER=1)")
    elif not is_running:
        scheduler.init_app(app)
        # Evitar iniciar durante testes e evitar duplicação no reloader
        should_start_scheduler = (not app.testing) and (
            os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
        )
        if should_start_scheduler:
            scheduler.start()

        # Importar log_service e registrar job de purge
        # (apenas se scheduler ativo)
        try:
            from .services import log_service as _ls  # type: ignore
        except Exception:  # pragma: no cover - defensive import
            _ls = None  # type: ignore
        if _ls is not None and hasattr(_ls, "purge_old_logs"):
            scheduler.add_job(
                id="purge_dev_logs",
                func=_ls.purge_old_logs,
                trigger="interval",
                days=1,
                replace_existing=True,
            )

    # Registro de Blueprints (se existirem)
    import logging

    bp_specs = [
        ("app.blueprints.auth_bp", "auth_bp"),
        ("app.blueprints.core_bp", "core_bp"),
        ("app.blueprints.api_bp", "api_bp"),
        ("app.blueprints.agendamento_bp", "agendamento_bp"),
        ("app.blueprints.paciente_bp", "paciente_bp"),
        ("app.blueprints.financeiro_bp", "financeiro_bp"),
        ("app.blueprints.agenda_bp", "agenda_bp"),
        ("app.blueprints.odontograma_bp", "odontograma_bp"),
        ("app.blueprints.admin_bp", "admin_bp"),
        ("app.blueprints.documentos_bp", "documentos_bp"),
        ("app.blueprints.admin_templates_bp", "admin_templates_bp"),
        ("app.blueprints.settings_bp", "settings_bp"),
        ("app.blueprints.tratamentos_bp", "tratamentos_bp"),
    ]
    for module_name, attr_name in bp_specs:
        try:
            mod = import_module(module_name)
            bp = getattr(mod, "bp", None) or getattr(mod, attr_name, None)
            if bp is not None:
                app.register_blueprint(bp)
        except Exception as e:
            # Logar erro de importação/registro para diagnóstico (não silencie)
            try:
                app.logger.error(
                    "Falha ao registrar blueprint %s: %s", module_name, e
                )
            except Exception:
                logging.exception(
                    "Falha ao registrar blueprint %s", module_name
                )

    # Rotas de desenvolvimento (somente em debug)
    if app.debug:

        @app.route("/__dev/test_raise_exception", methods=["GET", "POST"])
        def __dev_test_raise_exception():  # pragma: no cover
            raise ValueError("Erro de teste de log")

    # Imports finais (garante modelos e eventos registrados)
    try:
        from . import models  # noqa: F401
    except Exception:
        pass
    try:
        from . import events  # noqa: F401
    except Exception:
        pass

    # Registrar filtros Jinja globais
    try:
        from .utils.template_filters import format_currency, format_datetime_br

        app.jinja_env.filters["format_datetime_br"] = format_datetime_br
        app.jinja_env.filters["format_currency"] = format_currency
    except Exception:
        # Em ambientes parciais de scaffold, ignore e siga em frente
        pass

    # Context processor: lightweight cache busting for static assets
    @app.context_processor
    def inject_asset_version():  # pragma: no cover - trivial
        """Injeta versão de assets para cache-busting.

        Ordem de prioridade:
        1. ASSETS_VERSION da variável de ambiente
        2. ASSETS_VERSION do app.config
        3. 'dev' como fallback
        """
        try:
            ver = os.environ.get("ASSETS_VERSION")
            if not ver:
                ver = app.config.get("ASSETS_VERSION")
            if not ver:
                ver = "dev"
        except Exception:
            ver = "dev"
        return {"asset_v": ver}

    # Context processor: expose RoleEnum to all templates
    @app.context_processor
    def inject_role_enum():  # pragma: no cover - trivial
        try:
            from .models import RoleEnum  # local import to avoid cycles

            return {"RoleEnum": RoleEnum}
        except Exception:
            return {}

    @app.context_processor
    def inject_tipo_documento():  # pragma: no cover - trivial
        try:
            from .models import TipoDocumento  # local import

            return {"TipoDocumento": TipoDocumento}
        except Exception:
            return {}

    @app.context_processor
    def inject_theme_colors():  # pragma: no cover - trivial
        """Inject theme colors for dynamic CSS variables."""
        try:
            from .services import theme_service

            theme = theme_service.get_theme_settings()
            return {
                "theme_primary_color": theme.get("primary_color", "#0d6efd"),
                "theme_secondary_color": theme.get(
                    "secondary_color", "#6c757d"
                ),
            }
        except Exception:
            return {
                "theme_primary_color": "#0d6efd",
                "theme_secondary_color": "#6c757d",
            }

    # Handler global de erros
    @app.errorhandler(Exception)
    def handle_global_exception(e):
        from werkzeug.exceptions import HTTPException

        # Preserve HTTP errors with their original status codes
        if isinstance(e, HTTPException):
            return e
        import traceback as tb

        from .models import GlobalSetting

        db.session.rollback()
        user_id = None
        try:
            user_id = (
                current_user.get_id()
                if (
                    hasattr(current_user, "get_id")
                    and current_user.is_authenticated
                )
                else None
            )
        except Exception:
            user_id = None
        try:
            # Garantir que log_service está disponível antes de usar
            if log_service is not None:
                try:
                    log_service.record_exception(e, request, user_id)
                except Exception:
                    pass
        except Exception:
            pass

        # Consultar GlobalSetting para DEV_LOGS_ENABLED
        dev_logs_enabled = False
        try:
            setting = db.session.get(GlobalSetting, "DEV_LOGS_ENABLED")
            if setting and str(setting.value).strip().lower() == "true":
                dev_logs_enabled = True
        except Exception:
            dev_logs_enabled = False

        if dev_logs_enabled:
            # Renderiza toast OOB para HTMX
            html = render_template(
                "utils/_error_toast.html",
                error=e,
                traceback=tb.format_exc(),
            )
            return (
                html,
                500,
                {
                    "HX-Reswap": "outerHTML",
                    "HX-Retarget": "body",
                    "HX-Trigger": "showErrorToast",
                },
            )
        else:
            return render_template("500.html"), 500

    return app


@login_manager.user_loader
def load_user(user_id: str):  # pragma: no cover - thin wrapper
    try:
        # Local import to avoid circulars at import time
        from .models import Usuario  # type: ignore

        return db.session.get(Usuario, int(user_id))
    except Exception:
        return None
