import click
from sqlalchemy import text

from . import db
from .seeder import seed_public, seed_tenant_default


def register_cli(app):
    @app.cli.command("dev-sync-db")
    def dev_sync_db():
        """DEV-only (Híbrido v4): Drop/Recreate schemas, create_all, then seed.

        Workflow (destrutivo e rápido):
          1) DROP SCHEMA IF EXISTS public CASCADE;
             DROP SCHEMA IF EXISTS tenant_default CASCADE;
          2) CREATE SCHEMA public; CREATE SCHEMA tenant_default;
          3) SET LOCAL search_path TO tenant_default, public;
          4) db.create_all();
          5) Seed data: public then tenant_default.
        """
        click.echo(
            "[dev-sync-db] Iniciando sincronização destrutiva de DEV..."
        )
        # Etapa 1-2: Dropar/Cria Schemas usando sessão do Flask SQLAlchemy
        click.echo("[dev-sync-db] Removendo schemas (se existirem)...")
        try:
            db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            db.session.execute(
                text("DROP SCHEMA IF EXISTS tenant_default CASCADE")
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            click.echo(f"[dev-sync-db] Aviso ao dropar schemas: {e}")

        click.echo("[dev-sync-db] Criando schemas public e tenant_default...")
        try:
            db.session.execute(text("CREATE SCHEMA public"))
            db.session.execute(text("CREATE SCHEMA tenant_default"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            click.echo(f"[dev-sync-db] Aviso ao criar schemas: {e}")

        # Etapa 3-4: Contexto + create_all()
        click.echo("[dev-sync-db] Preparando contextos e criando tabelas...")
        try:
            # Use uma conexão dedicada para garantir o search_path correto
            with db.engine.begin() as conn:
                conn.execute(text("SET search_path TO tenant_default, public"))
                # Cria todas as tabelas conforme os models
                db.metadata.create_all(bind=conn)
        except Exception as e:
            click.echo(
                f"[dev-sync-db] ERRO ao criar tabelas via create_all: {e}"
            )
            raise

        # Opcional: manter compatibilidade com testes (alembic_version)
        try:
            MIG_VER = "1bbe8ad76a77"
            # public.alembic_version
            db.session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS public.alembic_version ("
                    "version_num VARCHAR(32) NOT NULL)"
                )
            )
            db.session.execute(text("DELETE FROM public.alembic_version"))
            db.session.execute(
                text(
                    "INSERT INTO public.alembic_version (version_num) "
                    "VALUES (:v)"
                ),
                {"v": MIG_VER},
            )
            # tenant_default.alembic_version
            db.session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS "
                    "tenant_default.alembic_version ("
                    "version_num VARCHAR(32) NOT NULL)"
                )
            )
            db.session.execute(
                text("DELETE FROM tenant_default.alembic_version")
            )
            db.session.execute(
                text(
                    "INSERT INTO tenant_default.alembic_version (version_num) "
                    "VALUES (:v)"
                ),
                {"v": MIG_VER},
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            click.echo(f"[dev-sync-db] Aviso ao ajustar alembic_version: {e}")

        # Etapa 5: Seeder
        click.echo("[dev-sync-db] Executando seed (public)...")
        seed_public()
        click.echo("[dev-sync-db] Executando seed (tenant_default)...")
        seed_tenant_default()

        click.echo(
            "[dev-sync-db] Banco de dados sincronizado e populado com sucesso."
        )
