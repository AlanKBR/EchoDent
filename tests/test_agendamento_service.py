from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app import db
from app.models import (
    Agendamento,
    Paciente,
    RoleEnum,
    StatusAgendamentoEnum,
    Usuario,
)
from app.services import agendamento_service


@pytest.fixture()
def seeded_agendamentos(db_session):
    """Cria 1 usuario (dentista), 1 paciente e 3 agendamentos
    (ontem/hoje/amanha).

    Retorna um dict com ids úteis, incluindo o agendamento de hoje.
    """
    # Usuario (bind: users)
    dentista = Usuario()
    dentista.username = f"dent_{uuid.uuid4().hex[:8]}"
    dentista.password_hash = "hash"
    dentista.role = RoleEnum.DENTISTA
    dentista.nome_completo = "Dr. Tester"
    dentista.cro_registro = "CRO-12345"
    db.session.add(dentista)

    # Paciente (bind: default)
    paciente = Paciente()
    paciente.nome_completo = "Paciente Teste"
    db.session.add(paciente)
    db.session.commit()  # get IDs

    today = dt.date.today()
    ontem = today - dt.timedelta(days=1)
    amanha = today + dt.timedelta(days=1)

    # Horários seguros (meio-dia evita bordas)
    meio_dia = dt.time(12, 0, 0)
    start_ontem = dt.datetime.combine(ontem, meio_dia)
    start_hoje = dt.datetime.combine(today, meio_dia)
    start_amanha = dt.datetime.combine(amanha, meio_dia)

    # Cria 3 agendamentos (default status MARCADO)
    ag_ontem = Agendamento()
    ag_ontem.paciente_id = paciente.id
    ag_ontem.dentista_id = dentista.id
    ag_ontem.start_time = start_ontem
    ag_ontem.end_time = start_ontem + dt.timedelta(hours=1)

    ag_hoje = Agendamento()
    ag_hoje.paciente_id = paciente.id
    ag_hoje.dentista_id = dentista.id
    ag_hoje.start_time = start_hoje
    ag_hoje.end_time = start_hoje + dt.timedelta(hours=1)

    ag_amanha = Agendamento()
    ag_amanha.paciente_id = paciente.id
    ag_amanha.dentista_id = dentista.id
    ag_amanha.start_time = start_amanha
    ag_amanha.end_time = start_amanha + dt.timedelta(hours=1)

    db.session.add_all([ag_ontem, ag_hoje, ag_amanha])
    db.session.commit()

    return {
        "dentista_id": dentista.id,
        "paciente_id": paciente.id,
        "hoje_id": ag_hoje.id,
        "ontem_id": ag_ontem.id,
        "amanha_id": ag_amanha.id,
    }


def test_get_agendamentos_do_dia_filtra_corretamente(seeded_agendamentos):
    # Quando
    ags = agendamento_service.get_agendamentos_do_dia()

    # Entao: somente o de hoje
    assert isinstance(ags, list)
    assert len(ags) == 1
    assert ags[0].id == seeded_agendamentos["hoje_id"]


def test_update_agendamento_status_success(seeded_agendamentos):
    ag_id = seeded_agendamentos["hoje_id"]

    # Quando
    agendamento_service.update_agendamento_status(ag_id, "SALA_ESPERA")

    # Entao
    ag = db.session.get(Agendamento, ag_id)
    assert ag is not None
    assert ag.status == StatusAgendamentoEnum.SALA_ESPERA


def test_update_agendamento_status_invalid_string(seeded_agendamentos):
    ag_id = seeded_agendamentos["hoje_id"]

    # Quando/Entao
    with pytest.raises(ValueError):
        agendamento_service.update_agendamento_status(
            ag_id, "STATUS_QUE_NAO_EXISTE"
        )
