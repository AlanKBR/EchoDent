from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime
from app.services import financeiro_service
from app.utils.decorators import admin_required

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")

@admin_bp.route("/caixa/fechar", methods=["GET"])
@login_required
@admin_required
def fechar_caixa_form():
    return render_template("admin/_fechamento_caixa_form.html")

@admin_bp.route("/caixa/fechar", methods=["POST"])
@login_required
@admin_required
def fechar_caixa_submit():
    data_caixa = request.form.get("data_caixa")
    saldo_apurado = request.form.get("saldo_apurado")
    try:
        if not data_caixa or not saldo_apurado:
            raise ValueError("Preencha todos os campos.")
        # Converter data e saldo
        data_caixa = datetime.strptime(data_caixa, "%Y-%m-%d").date()
        saldo_apurado = Decimal(saldo_apurado)
        financeiro_service.fechar_caixa_dia(
            data_caixa=data_caixa,
            saldo_apurado=saldo_apurado,
            usuario_id=current_user.id
        )
        flash("Caixa fechado com sucesso!", "success")
        return redirect(url_for("admin_bp.fechar_caixa_form"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin_bp.fechar_caixa_form"))
