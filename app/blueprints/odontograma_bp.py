from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.services import odontograma_service
from app.utils.decorators import admin_required


odontograma_bp = Blueprint("odontograma_bp", __name__)


@odontograma_bp.route(
    "/paciente/<int:paciente_id>/odontograma_estado", methods=["GET"]
)  # json api
@login_required
def get_odontograma_estado(paciente_id: int):  # pragma: no cover - thin
    data = odontograma_service.get_estado_odontograma_completo(paciente_id)
    return jsonify(data)


@odontograma_bp.route(
    "/paciente/<int:paciente_id>/odontograma_estado/bulk", methods=["POST"]
)
@login_required
def post_odontograma_estado_bulk(paciente_id: int):  # pragma: no cover - thin
    payload = request.get_json(silent=True) or {}
    try:
        odontograma_service.update_odontograma_bulk(
            paciente_id=paciente_id,
            updates_map=payload,
            usuario_id=getattr(current_user, "id", 0),
        )
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@odontograma_bp.route(
    "/paciente/<int:paciente_id>/odontograma_snapshot", methods=["POST"]
)
@login_required
def post_odontograma_snapshot(paciente_id: int):  # pragma: no cover - thin
    try:
        odontograma_service.snapshot_odontograma_inicial(
            paciente_id=paciente_id,
            usuario_id=getattr(current_user, "id", 0),
            force_overwrite=False,
        )
        # Return a small HTML fragment suitable for HTMX insertion
        return (
            "<div class=\"alert alert-success\">Snapshot salvo.</div>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    except Exception as exc:
        return (
            f"<div class=\"alert alert-danger\">{str(exc)}</div>",
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )


@odontograma_bp.route(
    "/paciente/<int:paciente_id>/odontograma_snapshot/force", methods=["POST"]
)
@login_required
@admin_required
def post_odontograma_snapshot_force(
    paciente_id: int,
):  # pragma: no cover - thin
    try:
        odontograma_service.snapshot_odontograma_inicial(
            paciente_id=paciente_id,
            usuario_id=getattr(current_user, "id", 0),
            force_overwrite=True,
        )
        html_ok = (
            "<div class=\"alert alert-success\">"
            "Snapshot salvo (Sobrescrito)."
            "</div>"
        )
        return (
            html_ok,
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    except Exception as exc:
        return (
            f"<div class=\"alert alert-danger\">{str(exc)}</div>",
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )
