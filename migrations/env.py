from __future__ import annotations

from logging.config import fileConfig
from typing import Optional

from alembic import context
from flask import current_app

# Alembic Config
config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except FileNotFoundError:
        pass


def _include_object_for_bind(active_bind: Optional[str]):
    def include_object(object_, name, type_, reflected, compare_to):
        if type_ == "table":
            table_bind = getattr(object_, "info", {}).get("bind_key")
            if active_bind is None:
                return table_bind in (None, "", "default")
            return table_bind == active_bind
        return True

    return include_object


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    with current_app.app_context():
        x_args = context.get_x_argument(as_dictionary=True)
        selected = x_args.get("bind") if isinstance(x_args, dict) else None
        active_bind = (
            None if selected in (None, "default", "", "None") else selected
        )

        # Set URL from the selected engine
        if active_bind is None:
            url = str(current_app.config["SQLALCHEMY_DATABASE_URI"])
        else:
            url = str(current_app.config["SQLALCHEMY_BINDS"][active_bind])

        target_metadata = current_app.extensions["migrate"].db.metadata

        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
            render_as_batch=True,
            include_object=_include_object_for_bind(active_bind),
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from app import db

    with current_app.app_context():
        x_args = context.get_x_argument(as_dictionary=True)
        selected = x_args.get("bind") if isinstance(x_args, dict) else None
        active_bind = (
            None if selected in (None, "default", "", "None") else selected
        )

        # Choose engine by bind
        engine = db.engine if active_bind is None else db.engines[active_bind]
        connectable = engine

        # Provide URL to Alembic config to silence warnings
        try:
            config.set_main_option("sqlalchemy.url", str(engine.url))
        except Exception:
            pass

        target_metadata = current_app.extensions["migrate"].db.metadata

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=True,
                include_object=_include_object_for_bind(active_bind),
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
