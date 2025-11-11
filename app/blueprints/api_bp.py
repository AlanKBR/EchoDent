from __future__ import annotations

import httpx
from flask import Blueprint, render_template, request

from app.utils.sanitization import sanitizar_input

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")

BRASIL_API_BASE = "https://brasilapi.com.br/api/cep/v1/"


def _fetch_cep_raw(cep: str) -> dict | None:
    """Consulta CEP na BrasilAPI.

    Retorna dict normalizado ou None se erro/inválido.
    Isola dependência externa para facilitar mocking em testes.
    """
    cep_clean = (cep or "").replace("-", "").strip()
    if len(cep_clean) != 8 or not cep_clean.isdigit():
        return None
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{BRASIL_API_BASE}{cep_clean}")
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {
                "cep": data.get("cep"),
                "logradouro": data.get("street"),
                "bairro": data.get("neighborhood"),
                "cidade": data.get("city"),
                "estado": data.get("state"),
            }
    except Exception:
        return None


@api_bp.route("/buscar-cep", methods=["POST"])  # HTMX endpoint
def buscar_cep():  # pragma: no cover - thin controller (tested)
    """Retorna fragmento HTML com campos de endereço preenchidos.

    Regras:
    - Sanitiza input.
    - Nunca retorna JSON (Stack §1). Sempre fragmento Jinja.
    - Fragmento projetado para hx-target em container do formulário.
    """
    raw = request.form.get("cep") or ""
    cep = sanitizar_input(raw) if isinstance(raw, str) else raw
    resultado = _fetch_cep_raw(str(cep)) if cep else None

    # Template fragmento mínimo; frontend poderá substituir depois.
    return render_template(
        "pacientes/_endereco_fragment.html",
        dados=resultado,
        cep_input=cep,
    )
