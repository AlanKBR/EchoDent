from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request

from .. import db
from ..models import CalendarEvent, RoleEnum, Usuario
from ..services import agendamento_service, holiday_service
from ..services.agenda_service import format_dt_iso, parse_iso_to_utc

agenda_bp = Blueprint("agenda_bp", __name__)


@agenda_bp.get("/agenda")
def agenda_page():
    """Página principal da Agenda (FullCalendar).

    Nota: A UI/JS será incorporada gradualmente. Por enquanto, renderiza um
    placeholder que confirma a rota e a integração.
    """
    return render_template("pages/agenda.html")


# ---- API (stub inicial, para validação de wiring) ----


@agenda_bp.get("/api/agenda/events")
def api_list_events():
    """Lista eventos num intervalo opcional (start/end em ISO-8601 UTC).

    Se query params `start` e/ou `end` forem informados, aplica filtro por
    sobreposição: (ev.end >= start AND ev.start <= end). Se `end` for nulo
    no banco, considera-se um evento pontual em `start`.
    """
    start_qs = request.args.get("start")
    end_qs = request.args.get("end")

    q = db.session.query(CalendarEvent)

    # Aplica filtro por intervalo quando possível
    try:
        start_dt = parse_iso_to_utc(start_qs) if start_qs else None
    except Exception:
        return jsonify({"error": "invalid start"}), 400
    try:
        end_dt = parse_iso_to_utc(end_qs) if end_qs else None
    except Exception:
        return jsonify({"error": "invalid end"}), 400

    if start_dt is not None and end_dt is not None:
        # overlap: ev.start <= end AND COALESCE(ev.end, ev.start) >= start
        q = q.filter(CalendarEvent.start <= end_dt).filter(
            db.func.coalesce(
                CalendarEvent.end,
                CalendarEvent.start,
            )
            >= start_dt
        )
    elif start_dt is not None:
        q = q.filter(
            db.func.coalesce(
                CalendarEvent.end,
                CalendarEvent.start,
            )
            >= start_dt
        )
    elif end_dt is not None:
        q = q.filter(CalendarEvent.start <= end_dt)

    # Optional filters: dentists (CSV ids), include_unassigned (1/true),
    # q (search)
    dentists_param = (request.args.get("dentists") or "").strip()
    include_unassigned = (request.args.get("include_unassigned") or "").strip()
    qstr = (request.args.get("q") or "").strip()

    dentist_ids: list[int] = []
    if dentists_param:
        try:
            dentist_ids = [
                int(x)
                for x in dentists_param.split(",")
                if x.strip().isdigit()
            ]
        except Exception:
            dentist_ids = []

    if dentist_ids:
        # Include events matching selected dentists
        q = q.filter(
            db.or_(
                CalendarEvent.dentista_id.in_(dentist_ids),
                db.and_(
                    db.literal(include_unassigned in {"1", "true", "True"}),
                    CalendarEvent.dentista_id.is_(None),
                ),
            )
        )
    else:
        # No dentists selected -> return only unassigned if flagged;
        # otherwise return empty set
        if include_unassigned in {"1", "true", "True"}:
            q = q.filter(CalendarEvent.dentista_id.is_(None))
        else:
            # Force empty result quickly
            return jsonify([])

    if qstr:
        like = f"%{qstr}%"
        q = q.filter(
            db.or_(
                CalendarEvent.title.ilike(like),
                CalendarEvent.notes.ilike(like),
            )
        )

    events = q.all()
    items = []
    for ev in events:
        items.append(
            {
                "id": ev.id,
                "title": ev.title,
                "start": format_dt_iso(ev.start),
                "end": format_dt_iso(ev.end) if ev.end else None,
                "allDay": bool(ev.all_day),
                "color": ev.color,
                "extendedProps": {
                    "notes": ev.notes or "",
                    "dentista_id": ev.dentista_id,
                    # compat: antigo nome utilizado no frontend
                    "profissional_id": ev.dentista_id,
                    "paciente_id": ev.paciente_id,
                },
            }
        )
    return jsonify(items)


@agenda_bp.get("/api/agenda/events/search_range")
def api_events_search_range():
    """Retorna min/max e contagem para busca (q + filtros)."""
    dentists_param = (request.args.get("dentists") or "").strip()
    include_unassigned_param = (
        request.args.get("include_unassigned") or ""
    ).strip()
    qstr = (request.args.get("q") or "").strip()

    dentist_ids: list[int] = []
    if dentists_param:
        try:
            dentist_ids = [
                int(x)
                for x in dentists_param.split(",")
                if x.strip().isdigit()
            ]
        except Exception:
            dentist_ids = []

    include_unassigned = include_unassigned_param in {"1", "true", "True"}
    res = agendamento_service.get_event_search_range(
        dentist_ids, include_unassigned, qstr
    )
    return jsonify(res)


@agenda_bp.get("/api/agenda/holidays/year")
def api_holidays_year():
    """Retorna feriados por ano (cacheados em memória no service)."""
    try:
        year = int((request.args.get("year") or "0").strip())
    except Exception:
        return jsonify({"error": "invalid year"}), 400
    if not year:
        return jsonify([])
    data = holiday_service.get_holidays_by_year(year)
    return jsonify(data)


@agenda_bp.post("/api/agenda/holidays/refresh")
def api_holidays_refresh():
    payload = request.get_json(silent=True) or {}
    try:
        year = int(payload.get("year") or 0)
    except Exception:
        return jsonify({"status": "error", "message": "Ano inválido"})
    if not year:
        return jsonify({"status": "error", "message": "Ano inválido"})
    state = payload.get("state") or None
    res = holiday_service.refresh_holidays(year, state)
    code = 200
    if isinstance(res, dict) and res.get("status") == "error":
        code = 400
    return jsonify(res), code


@agenda_bp.get("/api/agenda/settings/invertexto_token")
def api_settings_token_get():
    has = bool(holiday_service.get_invertexto_token())
    return jsonify({"hasToken": has})


@agenda_bp.post("/api/agenda/settings/invertexto_token")
def api_settings_token_set():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify({"status": "error", "message": "Token vazio"}), 400
    holiday_service.set_invertexto_token(token)
    return jsonify({"status": "success"})


@agenda_bp.delete("/api/agenda/settings/invertexto_token")
def api_settings_token_del():
    holiday_service.clear_invertexto_token()
    return jsonify({"status": "success"})


@agenda_bp.post("/api/agenda/cache/clear")
def api_cache_clear():
    holiday_service.clear_holiday_cache()
    return ("", 204)


@agenda_bp.get("/api/agenda/buscar_nomes")
def api_buscar_nomes():
    q = (request.args.get("q") or "").strip()
    nomes = agendamento_service.search_pacientes_by_name(q)
    return jsonify(nomes)


@agenda_bp.get("/api/agenda/buscar_telefone")
def api_buscar_telefone():
    nome = (request.args.get("nome") or "").strip()
    tel = agendamento_service.get_paciente_telefone(nome)
    return jsonify({"telefone": tel})


@agenda_bp.post("/api/agenda/events")
def api_create_event():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    start_str = data.get("start")
    end_str = data.get("end")
    all_day = bool(data.get("allDay") or False)
    color = data.get("color")
    notes = data.get("notes") or None
    dentista_id = data.get("dentista_id")
    paciente_id = data.get("paciente_id")

    if not start_str:
        return jsonify({"error": "start is required"}), 400

    start_dt = parse_iso_to_utc(start_str, assume_all_day=all_day)
    end_dt = (
        parse_iso_to_utc(end_str, assume_all_day=all_day) if end_str else None
    )

    if end_dt is not None and end_dt < start_dt:
        return jsonify({"error": "end before start"}), 400

    ev = CalendarEvent()
    ev.title = title
    ev.start = start_dt
    ev.end = end_dt
    ev.all_day = all_day
    ev.color = color
    ev.notes = notes
    # Cross-bind references: validar apenas tipos, não FK
    try:
        ev.dentista_id = int(dentista_id) if dentista_id is not None else None
    except Exception:
        return jsonify({"error": "invalid dentista_id"}), 400
    try:
        ev.paciente_id = int(paciente_id) if paciente_id is not None else None
    except Exception:
        return jsonify({"error": "invalid paciente_id"}), 400
    db.session.add(ev)
    db.session.commit()

    # responder no formato esperado pelo frontend (status + evento completo)
    event_obj = {
        "id": ev.id,
        "title": ev.title,
        "start": format_dt_iso(ev.start),
        "end": format_dt_iso(ev.end) if ev.end else None,
        "allDay": bool(ev.all_day),
        "color": ev.color,
        "extendedProps": {
            "notes": ev.notes or "",
            "dentista_id": ev.dentista_id,
            "profissional_id": ev.dentista_id,
            "paciente_id": ev.paciente_id,
        },
    }
    return jsonify({"status": "success", "event": event_obj}), 201


@agenda_bp.patch("/api/agenda/events/<int:event_id>")
def api_update_event(event_id: int):
    data = request.get_json(silent=True) or {}
    ev = db.session.get(CalendarEvent, event_id)
    if not ev:
        return jsonify({"error": "not found"}), 404

    if "title" in data:
        ev.title = (data.get("title") or "").strip()
    if "start" in data:
        all_day_flag = bool(data.get("allDay") or ev.all_day)
        ev.start = parse_iso_to_utc(
            data.get("start"), assume_all_day=all_day_flag
        )
    if "end" in data:
        val = data.get("end")
        ev.end = (
            parse_iso_to_utc(
                val,
                assume_all_day=bool(data.get("allDay") or ev.all_day),
            )
            if val
            else None
        )
    if "allDay" in data:
        ev.all_day = bool(data.get("allDay"))
    if "color" in data:
        ev.color = data.get("color")
    if "notes" in data:
        ev.notes = data.get("notes")
    if "dentista_id" in data:
        try:
            dent_val = data.get("dentista_id")
            ev.dentista_id = int(dent_val) if dent_val is not None else None
        except Exception:
            return jsonify({"error": "invalid dentista_id"}), 400
    if "paciente_id" in data:
        try:
            pac_val = data.get("paciente_id")
            ev.paciente_id = int(pac_val) if pac_val is not None else None
        except Exception:
            return jsonify({"error": "invalid paciente_id"}), 400

    # Sanity: end >= start
    if ev.end is not None and ev.end < ev.start:
        return jsonify({"error": "end before start"}), 400

    db.session.commit()
    return jsonify({"status": "success"})


@agenda_bp.delete("/api/agenda/events/<int:event_id>")
def api_delete_event(event_id: int):
    ev = db.session.get(CalendarEvent, event_id)
    if not ev:
        return jsonify({"status": "success"})
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"status": "success"})


@agenda_bp.get("/api/agenda/dentists")
def api_list_dentists():
    """Lista dentistas ativos (bind users)."""
    q = (
        db.session.query(Usuario)
        .filter(Usuario.role == RoleEnum.DENTISTA)
        .filter(Usuario.is_active == True)  # noqa: E712
        .order_by(Usuario.nome_completo.nullslast())
    )
    items = []
    for u in q.all():
        items.append(
            {
                "id": u.id,
                "nome": u.nome_completo or u.username,
                "color": u.color,
            }
        )
    return jsonify(items)


@agenda_bp.get("/api/agenda/partials/<path:partial_path>")
def api_agenda_partials(partial_path: str):
    """Renderiza parciais HTML para a Agenda (HTMX-friendly).

    Procura em templates/agenda/partials/<partial_path>.html.
    """
    # Segurança básica: impedir path traversal
    if ".." in partial_path or partial_path.startswith("/"):
        abort(404)
    template_name = f"agenda/partials/{partial_path}.html"
    try:
        return render_template(template_name)
    except Exception:
        abort(404)
