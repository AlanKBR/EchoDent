import os
import importlib

# Bootstrap WeasyPrint DLLs on Windows if MSYS2 is installed.
# This avoids the common "WeasyPrint could not import some external
# libraries" warning by pointing WeasyPrint to Pango/Cairo DLLs
# installed via MSYS2.
# Docs:
# https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
if os.name == "nt":
    default_msys_bin = r"C:\\msys64\\mingw64\\bin"
    env_not_set = not os.environ.get("WEASYPRINT_DLL_DIRECTORIES")
    if env_not_set and os.path.isdir(default_msys_bin):
        # Set only if not already set and path exists
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = default_msys_bin

from app import create_app, db

# Carrega variáveis de ambiente do .env se existir
# (Dotenv é geralmente instalado com Flask).
# Evita erro se não estiver instalado.
try:
    dotenv_mod = importlib.import_module("dotenv")
    load_dotenv = getattr(
        dotenv_mod,
        "load_dotenv",
        lambda *_a, **_k: False,  # fallback no-op
    )
except Exception:
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

load_dotenv()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.shell_context_processor
def make_shell_context():
    """Permite acesso fácil ao db no 'flask shell'."""
    return dict(db=db)


if __name__ == '__main__':
    app.run(debug=True)
