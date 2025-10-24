from __future__ import annotations

from datetime import date as date_cls, datetime, time, timedelta

from app import db
from app.models import Agendamento, StatusAgendamentoEnum


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
