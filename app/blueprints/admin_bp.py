from datetime import datetime
from decimal import Decimal

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
from flask_login import current_user, login_required

from app.services import financeiro_service, log_service, settings_service
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
            usuario_id=current_user.id,
        )
        flash("Caixa fechado com sucesso!", "success")
        return redirect(url_for("admin_bp.fechar_caixa_form"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin_bp.fechar_caixa_form"))


@admin_bp.route("/configuracoes", methods=["GET"])
@login_required
@admin_required
def configuracoes():
    settings = settings_service.get_all_settings()
    return render_template("admin/configuracoes.html", settings=settings)


@admin_bp.route("/configuracoes/update", methods=["POST"])
@login_required
@admin_required
def configuracoes_update():
    # Atualização atômica em lote (whitelist e sanitização no service)
    settings_service.update_settings_bulk(request.form.to_dict())
    # Resposta HTMX: redireciona para recarregar a página
    return Response(
        status=204,
        headers={"HX-Redirect": url_for("admin_bp.configuracoes")},
    )


@admin_bp.route("/devlogs", methods=["GET"])
@login_required
@admin_required
def devlogs():
    page = request.args.get("page", 1, type=int)
    per_page = 25
    pagination = log_service.get_logs_paginated(page=page, per_page=per_page)
    return render_template("admin/devlogs.html", pagination=pagination)


# Rota de detalhe de log
@admin_bp.route("/devlogs/<int:log_id>", methods=["GET"])
@login_required
@admin_required
def view_log_detail(log_id):
    log = log_service.get_log_by_id(log_id)
    if not log:
        abort(404)
    return render_template("admin/devlog_detail.html", log=log)


@admin_bp.route("/devlogs/purge", methods=["POST"])
@login_required
@admin_required
def purge_devlogs():
    log_service.purge_all_logs()
    # Resposta HTMX: redireciona para recarregar a página de logs
    return ("", 204, {"HX-Redirect": "/admin/devlogs"})
