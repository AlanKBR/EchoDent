from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import StatusAgendamentoEnum
from app.services import agendamento_service


agendamento_bp = Blueprint("agendamento_bp", __name__)


@agendamento_bp.route(
    "/agendamento/<int:agendamento_id>/status", methods=["POST"]
)
@login_required
def update_status(agendamento_id: int):  # pragma: no cover - thin controller
    novo_status = request.form.get("status", "")
    agendamento_service.update_agendamento_status(agendamento_id, novo_status)
    agendamentos = agendamento_service.get_agendamentos_do_dia()
    return render_template(
        "core/_sala_espera_widget.html",
        agendamentos=agendamentos,
        StatusAgendamentoEnum=StatusAgendamentoEnum,
    )
