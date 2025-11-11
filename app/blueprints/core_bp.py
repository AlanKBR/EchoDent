from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import RoleEnum, StatusAgendamentoEnum
from app.services import agendamento_service

core_bp = Blueprint("core_bp", __name__)


@core_bp.route("/", methods=["GET"])
def index():  # pragma: no cover - thin controller
    """Raiz do app.

    - Usuário não autenticado: redireciona para a página de login.
    - Usuário autenticado: redireciona para o dashboard apropriado.
    """
    if getattr(current_user, "is_authenticated", False):
        return redirect(url_for("core_bp.dashboard"))
    return redirect(url_for("auth_bp.login"))


@core_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():  # pragma: no cover - thin controller
    role = getattr(current_user, "role", None)
    if role in (RoleEnum.SECRETARIA, RoleEnum.ADMIN):
        return render_template("dashboard_secretaria.html")
    if role == RoleEnum.DENTISTA:
        return render_template("dashboard_dentista.html")
    # fallback
    return render_template("dashboard_secretaria.html")


@core_bp.route("/dashboard/sala_espera_widget", methods=["GET"])
@login_required
def sala_espera_widget():  # pragma: no cover - thin controller
    agendamentos = agendamento_service.get_agendamentos_do_dia()
    return render_template(
        "core/_sala_espera_widget.html",
        agendamentos=agendamentos,
        StatusAgendamentoEnum=StatusAgendamentoEnum,
    )
