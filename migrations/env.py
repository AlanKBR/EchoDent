import logging
import os
from dotenv import load_dotenv
from logging.config import fileConfig
import sqlalchemy as sa

from flask import current_app

from alembic import context
from app import db as main_db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
load_dotenv()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')
    

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = main_db.metadata
# Prefer SHADOW_DATABASE_URL (Hybrid v4 - Shadow DB). Fallback to app engine.
shadow_url = os.environ.get('SHADOW_DATABASE_URL')
if shadow_url:
    config.set_main_option('sqlalchemy.url', shadow_url)
else:
    config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            # Support multi-pass autogenerate where multiple UpgradeOps
            # collections are produced (public + tenants). When present,
            # use upgrade_ops_list; otherwise fall back to single upgrade_ops.
            uol = getattr(script, 'upgrade_ops_list', None)
            if uol is not None:
                # If all per-pass ops are empty, drop the revision. Otherwise,
                # keep as-is (no attempt to mutate the internal list, which
                # may be read-only depending on Alembic version).
                if all(ops.is_empty() for ops in uol):
                    directives[:] = []
                    logger.info('No changes in schema detected.')
            else:
                if script.upgrade_ops.is_empty():
                    directives[:] = []
                    logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    # Build engine from SHADOW when available; else use app engine.
    engine = sa.create_engine(shadow_url) if shadow_url else get_engine()

    # Helpers to filter objects per schema pass
    def include_object_public(obj, name, type_, reflected, compare_to):
        if type_ == "table":
            return getattr(obj, "schema", None) == "public"
        if type_ in ("index", "column", "constraint"):
            table = getattr(obj, "table", None)
            if table is None:
                table = getattr(obj, "parent", None)
            schema = (
                getattr(table, "schema", None)
                if table is not None
                else None
            )
            return schema == "public"
        return True

    def include_object_tenant(obj, name, type_, reflected, compare_to):
        if type_ == "table":
            schema = getattr(obj, "schema", None)
            return schema is None or schema != "public"
        if type_ in ("index", "column", "constraint"):
            table = getattr(obj, "table", None)
            if table is None:
                table = getattr(obj, "parent", None)
            schema = (
                getattr(table, "schema", None)
                if table is not None
                else None
            )
            return schema is None or schema != "public"
        return True

    phase = os.environ.get("ECHODENT_RUN_PHASE")

    def run_public_pass():
        # Use a fresh connection/transaction for the public pass
        with engine.begin() as connection:
            try:
                connection.execute(sa.text("SET search_path TO public"))
            except Exception:
                pass

            context.configure(
                connection=connection,
                target_metadata=get_metadata(),
                include_schemas=True,
                version_table_schema="public",
                include_object=include_object_public,
                **conf_args,
            )
            context.run_migrations()

    def discover_tenants():
        # Try to read from public.tenants; fallback to default
        tenants_local = []
        with engine.connect() as connection:
            try:
                connection.execute(sa.text("SET search_path TO public"))
                res = connection.execute(
                    sa.text(
                        "SELECT schema_name FROM public.tenants "
                        "WHERE is_active = true"
                    )
                )
                tenants_local = [row[0] for row in res]
            except Exception:
                tenants_local = []
        if not tenants_local:
            tenants_local = ["tenant_default"]
        return tenants_local

    def run_tenant_pass(tenants_list):
        for tenant_schema in tenants_list:
            # Ensure schema exists before running migrations
            with engine.connect() as c_autocommit:
                try:
                    ac_conn = c_autocommit.execution_options(
                        isolation_level="AUTOCOMMIT"
                    )
                    ac_conn.execute(
                        sa.text(
                            f"CREATE SCHEMA IF NOT EXISTS {tenant_schema}"
                        )
                    )
                except Exception:
                    pass
            # Run migrations for this tenant with isolated connection
            with engine.begin() as connection:
                try:
                    connection.execute(
                        sa.text(
                            f"SET search_path TO {tenant_schema}, public"
                        )
                    )
                except Exception:
                    pass

                context.configure(
                    connection=connection,
                    target_metadata=get_metadata(),
                    include_schemas=True,
                    version_table_schema=tenant_schema,
                    include_object=include_object_tenant,
                    **conf_args,
                )
                context.run_migrations()

    # Phase control
    if phase == "public":
        run_public_pass()
        return
    if phase == "tenants":
        tenants = discover_tenants()
        run_tenant_pass(tenants)
        return

    # Default: two-pass in a single invocation
    run_public_pass()
    tenants = discover_tenants()
    run_tenant_pass(tenants)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
