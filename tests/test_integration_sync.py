import os

from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def _get_engine():
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    assert url, "DATABASE_URL must be set for integration test"
    # use pre_ping to avoid stale connections
    return create_engine(url, pool_pre_ping=True)


def _scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def _count(conn, sql, params=None):
    return int(conn.execute(text(sql), params or {}).scalar() or 0)


def test_dev_sync_db_integrity():
    engine = _get_engine()
    migration_id = "1bbe8ad76a77"

    with engine.connect() as conn:
        # Assert 1: public alembic_version exists and matches
        conn.execute(text("SET search_path TO public"))
        pub_ver = _scalar(conn, "SELECT version_num FROM alembic_version")
        assert (
            pub_ver == migration_id
        ), f"public.alembic_version expected {migration_id}, got {pub_ver}"

        # Assert 2: tenant_default alembic_version exists and matches
        conn.execute(text("SET search_path TO tenant_default, public"))
        ten_ver = _scalar(conn, "SELECT version_num FROM alembic_version")
        assert ten_ver == migration_id, (
            "tenant_default.alembic_version expected "
            f"{migration_id}, got {ten_ver}"
        )

        # Assert 3: public.tenants seeded
        tenants = _count(
            conn,
            "SELECT COUNT(*) FROM public.tenants WHERE schema_name = :s",
            {"s": "tenant_default"},
        )
        assert tenants == 1, f"Expected 1 tenant_default, got {tenants}"

        # Assert 4: tenant_default.pacientes seeded (> 0)
        pacientes = _count(
            conn,
            "SELECT COUNT(*) FROM tenant_default.pacientes",
        )
        assert pacientes > 0, "Expected pacientes > 0 in tenant_default"

    # Assert 5: a seeded table has rows (agendamentos seeded in seeder)
        agendamentos = _count(
            conn,
            "SELECT COUNT(*) FROM tenant_default.agendamentos",
        )
        assert (
            agendamentos > 0
        ), "Expected agendamentos > 0 in tenant_default (seeded)"
