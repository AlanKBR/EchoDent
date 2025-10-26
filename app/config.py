import os


# Diretório base do projeto (raiz que contém a pasta `app/`)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Diretório de instância (fora de `app/`), ex: <raiz>/instance
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


def _sqlite_uri(filename: str) -> str:
    """Monta uma URI SQLite absoluta para um arquivo dentro do INSTANCE_DIR.

    Em Windows, normaliza para barras "/" para compatibilidade com a URI.
    """
    path = os.path.abspath(os.path.join(INSTANCE_DIR, filename))
    return "sqlite:///" + path.replace("\\", "/")


class Config:
    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Tokens de serviços externos (opcional)
    INVERTEXTO_API_TOKEN = os.environ.get("INVERTEXTO_API_TOKEN")

    # SQLAlchemy (multi-bind)
    SQLALCHEMY_DATABASE_URI = _sqlite_uri("pacientes.db")  # bind padrão
    SQLALCHEMY_BINDS = {
        "users": _sqlite_uri("users.db"),
        "history": _sqlite_uri("history.db"),
        # Novo bind para o módulo Agenda/Calendário
        "calendario": _sqlite_uri("calendario.db"),
    }

    # Desativa o rastreamento de alterações (economiza memória)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
