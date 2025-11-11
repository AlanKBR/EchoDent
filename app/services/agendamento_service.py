from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time, timedelta

from app import db
from app.models import (
    Agendamento,
    CalendarEvent,
    Paciente,
    StatusAgendamentoEnum,
)

from .agenda_service import format_dt_iso


def get_agendamentos_do_dia(data: date_cls | None = None) -> list[Agendamento]:
    """Retorna os agendamentos cujo start_time cai no dia informado.

    Se ``data`` for None, usa a data de hoje (timezone naive,
    UTC local conforme SQLite).
    """
    if data is None:
        data = date_cls.today()
    start_dt = datetime.combine(data, time.min)
    next_day = data + timedelta(days=1)
    end_exclusive = datetime.combine(next_day, time.min)

    # BETWEEN start_dt (inclusive) e next day (exclusive)
    return (
        Agendamento.query.filter(
            Agendamento.start_time >= start_dt,
            Agendamento.start_time < end_exclusive,
        )
        .order_by(Agendamento.start_time.asc())
        .all()
    )


def update_agendamento_status(
    agendamento_id: int, novo_status_str: str
) -> Agendamento:
    """Atualiza o status do agendamento.

    :param agendamento_id: ID do agendamento
    :param novo_status_str: Nome do status (ex: "SALA_ESPERA")
    :raises LookupError: se o agendamento não existir
    :raises ValueError: se o status for inválido
    :return: Agendamento atualizado
    """
    ag = db.session.get(Agendamento, int(agendamento_id))
    if not ag:
        raise LookupError(f"Agendamento {agendamento_id} não encontrado")

    if not isinstance(novo_status_str, str) or not novo_status_str:
        raise ValueError("Status inválido")

    try:
        enum_val = StatusAgendamentoEnum[novo_status_str.upper()]
    except KeyError as exc:
        raise ValueError(f"Status desconhecido: {novo_status_str}") from exc

    ag.status = enum_val
    db.session.add(ag)
    db.session.commit()
    return ag


# ----------------------------------
# Agenda — Search Range e Busca de Pacientes (cross-bind)
# ----------------------------------


def _apply_event_filters(
    q, dentist_ids: list[int], include_unassigned: bool, qstr: str
):
    """Aplica filtros comuns usados na listagem de eventos."""
    if dentist_ids:
        q = q.filter(
            db.or_(
                CalendarEvent.dentista_id.in_(dentist_ids),
                db.and_(
                    db.literal(include_unassigned),
                    CalendarEvent.dentista_id.is_(None),
                ),
            )
        )
    else:
        if include_unassigned:
            q = q.filter(CalendarEvent.dentista_id.is_(None))
        else:
            # Força resultado vazio
            return q.filter(db.literal(False))

    if qstr:
        like = f"%{qstr}%"
        q = q.filter(
            db.or_(
                CalendarEvent.title.ilike(like),
                CalendarEvent.notes.ilike(like),
            )
        )
    return q


def get_event_search_range(
    dentist_ids: list[int], include_unassigned: bool, qstr: str
) -> dict[str, str | None | int]:
    """Retorna min(start), max(COALESCE(end,start)) e count para os filtros.

    Formato compatível com o frontend:
    {"min": ISO|None, "max": ISO|None, "count": int}
    """
    qy = db.session.query(
        db.func.min(CalendarEvent.start),
        db.func.max(db.func.coalesce(CalendarEvent.end, CalendarEvent.start)),
        db.func.count(CalendarEvent.id),
    )
    qy = _apply_event_filters(
        qy.select_from(CalendarEvent), dentist_ids, include_unassigned, qstr
    )
    row = qy.one()
    min_dt, max_dt, count_val = row[0], row[1], int(row[2] or 0)
    if not count_val:
        return {"min": None, "max": None, "count": 0}
    return {
        "min": format_dt_iso(min_dt),
        "max": format_dt_iso(max_dt),
        "count": count_val,
    }


def search_pacientes_by_name(query_str: str, limit: int = 10) -> list[str]:
    """Autocomplete: retorna até `limit` nomes iniciando por `query_str`.

    Leitura cross-bind: Paciente está no bind default.
    Retorna lista de strings (nomes), conforme esperado pelo datalist.
    """
    q = (query_str or "").strip()
    if not q:
        return []
    like = f"{q}%"
    rows = (
        db.session.query(Paciente.nome_completo)
        .filter(Paciente.nome_completo.ilike(like))
        .order_by(Paciente.nome_completo.asc())
        .limit(limit)
        .all()
    )
    names: list[str] = []
    for r in rows:
        try:
            nm = str(r[0]).strip()
            if nm:
                names.append(nm)
        except Exception:
            continue
    return names


def get_paciente_telefone(nome_completo: str) -> str:
    """Retorna telefone do paciente por nome exato; vazio se não encontrado."""
    name = (nome_completo or "").strip()
    if not name:
        return ""
    row = (
        db.session.query(Paciente.telefone)
        .filter(Paciente.nome_completo == name)
        .order_by(Paciente.id.desc())
        .first()
    )
    if not row:
        return ""
    try:
        val = row[0]
        return (val or "").strip()
    except Exception:
        return ""
