import os


class Config:
    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY")

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
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Desativa o rastreamento de alterações (economiza memória)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
