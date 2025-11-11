import os


class Config:
    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Versionamento de Assets (Cache-Busting)
    # Incrementar manualmente a cada deploy ou usar variável de ambiente
    ASSETS_VERSION = os.environ.get("ASSETS_VERSION", "1.0.0")

    # Tokens de serviços externos (opcional)
    INVERTEXTO_API_TOKEN = os.environ.get("INVERTEXTO_API_TOKEN")

    # SQLAlchemy (PostgreSQL)
    # Use DATABASE_URL (ex.: postgresql+psycopg://user:pass@host:5432/echodent)
    # Se não definido, utiliza um valor de desenvolvimento convencional.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/echodent",
    )

    # Engine options recomendadas (MVCC já é nativo do Postgres)
    # Definir search_path padrão via connect_args (multi-tenant AGENTS.MD §6)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "connect_args": {"options": "-c search_path=tenant_default,public"},
    }

    # Desativa o rastreamento de alterações (economiza memória)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
