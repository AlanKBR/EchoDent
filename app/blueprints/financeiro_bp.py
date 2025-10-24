from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from app import db

from app.services.paciente_service import get_paciente_by_id
from app.services.financeiro_service import (
    get_all_procedimentos,
    get_procedimento_by_id,
    create_plano,
    get_plano_by_id,
    approve_plano,
    add_lancamento,
    get_saldo_devedor_plano,
    create_recibo_avulso,
)


financeiro_bp = Blueprint("financeiro_bp", __name__, url_prefix="/financeiro")


@financeiro_bp.route("/novo_plano/<int:paciente_id>", methods=["GET"])  # shell
@login_required
def novo_plano_form(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    procedimentos = get_all_procedimentos()
    return render_template(
        "financeiro/form_plano.html",
        paciente=paciente,
        procedimentos=procedimentos,
    )


@financeiro_bp.route("/add_procedimento_fragment", methods=["GET"])  # htmx
@login_required
def add_procedimento_fragment():  # pragma: no cover - thin controller
    proc_id = request.args.get("procedimento_select") or request.args.get(
        "procedimento_id"
    )
    if not proc_id:
        return "", 204
    procedimento = get_procedimento_by_id(int(proc_id))
    if not procedimento:
        return "", 204
    return render_template(
        "financeiro/_item_plano_row.html", procedimento=procedimento
    )


@financeiro_bp.route(
    "/novo_plano/<int:paciente_id>", methods=["POST"]
)  # submit
@login_required
def novo_plano_submit(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    dentista_id = getattr(current_user, "id", None)
    proc_ids = request.form.getlist("procedimento_id")
    valores = request.form.getlist("valor_cobrado")
    itens_data = []
    for i, pid in enumerate(proc_ids):
        valor = valores[i] if i < len(valores) else None
        if not pid:
            continue
        itens_data.append(
            {
                "procedimento_id": int(pid),
                "valor_cobrado": valor,
            }
        )

    if not itens_data:
        flash("Adicione ao menos um procedimento ao orçamento.", "danger")
        return redirect(
            url_for("financeiro_bp.novo_plano_form", paciente_id=paciente_id)
        )

    create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=itens_data,
    )
    flash("Orçamento criado com sucesso.", "success")
    return redirect(url_for("paciente_bp.detalhe", paciente_id=paciente_id))


@financeiro_bp.route("/plano/<int:plano_id>", methods=["GET"])  # detalhe
@login_required
def plano_detalhe(plano_id: int):  # pragma: no cover - thin controller
    plano = get_plano_by_id(plano_id)
    if not plano:
        flash("Plano não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    try:
        saldo = get_saldo_devedor_plano(plano_id)
    except Exception:
        saldo = None

    return render_template(
        "financeiro/detalhe_plano.html",
        plano=plano,
        saldo=saldo,
    )


@financeiro_bp.route(
    "/plano/<int:plano_id>/aprovar", methods=["POST"]
)
@login_required
def aprovar_plano(plano_id: int):  # pragma: no cover - thin controller
    desconto = request.form.get("desconto") or 0
    try:
        approve_plano(plano_id, desconto)
        flash("Plano aprovado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(
        url_for("financeiro_bp.plano_detalhe", plano_id=plano_id)
    )


@financeiro_bp.route(
    "/plano/<int:plano_id>/pagar", methods=["POST"]
)
@login_required
def pagar_plano(plano_id: int):  # pragma: no cover - thin controller
    valor = request.form.get("valor")
    metodo = request.form.get("metodo_pagamento") or "DINHEIRO"
    if not valor:
        flash("Informe um valor para pagamento.", "danger")
        return redirect(
            url_for("financeiro_bp.plano_detalhe", plano_id=plano_id)
        )
    try:
        add_lancamento(plano_id, valor, metodo)
        db.session.commit()
        flash("Pagamento registrado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(
        url_for("financeiro_bp.plano_detalhe", plano_id=plano_id)
    )


@financeiro_bp.route(
    "/recibo_avulso/<int:paciente_id>", methods=["GET", "POST"]
)
@login_required
def recibo_avulso(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    if request.method == "GET":
        return render_template(
            "financeiro/form_recibo_avulso.html", paciente=paciente
        )

    # POST
    dentista_id = getattr(current_user, "id", None)
    valor = request.form.get("valor")
    motivo = request.form.get("motivo_descricao")
    if not valor or not motivo:
        flash("Informe valor e motivo do recibo.", "danger")
        return redirect(
            url_for("financeiro_bp.recibo_avulso", paciente_id=paciente_id)
        )
    try:
        create_recibo_avulso(paciente_id, dentista_id, valor, motivo)
        flash("Recibo avulso registrado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("paciente_bp.detalhe", paciente_id=paciente_id))
