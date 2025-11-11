from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app import db
from app.models import TemplateDocumento, TipoDocumento
from app.utils.decorators import admin_required

"""Admin CRUD para TemplateDocumento.

Regras:
- Protegido por @login_required e @admin_required
- Linter de blocos condicionais (__BLOCO_...__) com lista fixa permitida
"""


admin_templates_bp = Blueprint(
    "admin_templates_bp", __name__, url_prefix="/admin/templates"
)


def _listar_blocos_usados(template_str: str) -> set[str]:
    import re as _re

    return set(_re.findall(r"__BLOCO_[A-Z0-9_]+__", template_str or ""))


# Lista fixa de blocos permitidos (Missão 3)
BLOCOS_PERMITIDOS: set[str] = {"__BLOCO_CID__"}


@admin_templates_bp.route("/", methods=["GET"])
@login_required
@admin_required
def index():  # pragma: no cover - thin controller
    templates = TemplateDocumento.query.order_by(TemplateDocumento.nome).all()
    return render_template("admin/templates/index.html", templates=templates)


@admin_templates_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():  # pragma: no cover - thin controller
    if request.method == "GET":
        return render_template("admin/templates/form.html", template=None)

    nome = (request.form.get("nome") or "").strip()
    tipo_raw = (request.form.get("tipo_doc") or "").strip()
    conteudo = (request.form.get("template_body") or "").strip()
    is_active = bool(request.form.get("is_active"))

    try:
        if not nome or not tipo_raw or not conteudo:
            raise ValueError("Preencha todos os campos obrigatórios.")
        tipo = TipoDocumento(tipo_raw)

        # Linter: validar blocos condicionais conhecidos
        blocos = _listar_blocos_usados(conteudo)
        blocos_desconhecidos = [
            b for b in blocos if b not in BLOCOS_PERMITIDOS
        ]
        if blocos_desconhecidos:
            raise ValueError(
                "Blocos condicionais desconhecidos: "
                + ", ".join(blocos_desconhecidos)
            )

        t = TemplateDocumento(
            nome=nome,
            tipo_doc=tipo,
            template_body=conteudo,
            is_active=is_active,
        )
        db.session.add(t)
        db.session.commit()
        flash("Template criado com sucesso.", "success")
        return redirect(url_for("admin_templates_bp.index"))
    except Exception as e:
        db.session.rollback()
        flash(str(e), "error")
        return render_template("admin/templates/form.html", template=None)


@admin_templates_bp.route("/<int:tid>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar(tid: int):  # pragma: no cover - thin controller
    t = db.session.get(TemplateDocumento, tid)
    if not t:
        abort(404)

    if request.method == "GET":
        return render_template("admin/templates/form.html", template=t)

    nome = (request.form.get("nome") or "").strip()
    tipo_raw = (request.form.get("tipo_doc") or "").strip()
    conteudo = (request.form.get("template_body") or "").strip()
    is_active = bool(request.form.get("is_active"))

    try:
        if not nome or not tipo_raw or not conteudo:
            raise ValueError("Preencha todos os campos obrigatórios.")
        tipo = TipoDocumento(tipo_raw)

        # Linter: validar blocos condicionais conhecidos
        blocos = _listar_blocos_usados(conteudo)
        blocos_desconhecidos = [
            b for b in blocos if b not in BLOCOS_PERMITIDOS
        ]
        if blocos_desconhecidos:
            raise ValueError(
                "Blocos condicionais desconhecidos: "
                + ", ".join(blocos_desconhecidos)
            )

        t.nome = nome
        t.tipo_doc = tipo
        t.template_body = conteudo
        t.is_active = is_active
        db.session.commit()
        flash("Template atualizado com sucesso.", "success")
        return redirect(url_for("admin_templates_bp.index"))
    except Exception as e:
        db.session.rollback()
        flash(str(e), "error")
        return render_template("admin/templates/form.html", template=t)


@admin_templates_bp.route("/<int:tid>/deletar", methods=["POST", "DELETE"])
@login_required
@admin_required
def delete(tid: int):  # pragma: no cover - thin controller
    t = db.session.get(TemplateDocumento, tid)
    if not t:
        abort(404)
    try:
        db.session.delete(t)
        db.session.commit()
        flash("Template removido.", "success")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "error")
    # Resposta compatível com HTMX (hx-delete)
    if request.method == "DELETE" or request.headers.get("HX-Request"):
        return Response("", status=204)
    return redirect(url_for("admin_templates_bp.index"))
