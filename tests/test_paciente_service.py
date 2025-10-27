from __future__ import annotations

import pytest

from app import db
from app.models import Paciente, Anamnese
from app.services.paciente_service import update_anamnese
from app.services import paciente_service
from app.models import AnamneseStatus
from datetime import datetime, timedelta, timezone


@pytest.fixture()
def _seed_paciente_with_anamnese(app):
    def _make():
        p = Paciente()
        p.nome_completo = "Paciente Anamnese"
        db.session.add(p)
        db.session.flush()
        a = Anamnese()
        a.paciente_id = p.id
        db.session.add(a)
        db.session.commit()
        return p

    return _make


def _get_anamnese(paciente_id: int) -> Anamnese:
    return db.session.query(Anamnese).filter_by(paciente_id=paciente_id).one()


def test_update_anamnese_no_red_flags(
    db_session, _seed_paciente_with_anamnese
):
    p = _seed_paciente_with_anamnese()

    form_data = {
        # Safe value should be normalized to None (no red flag)
        "alergias": "Nenhuma",
        # Boolean-like safe field
        "doenca_cardiaca": "nao",
        # Ensure others are empty
        "medicamentos": "",
        "historico_doencas": "",
    }

    update_anamnese(p.id, form_data, 1)

    a = _get_anamnese(p.id)
    assert a.has_red_flags is False


def test_update_anamnese_with_red_flags(
    db_session, _seed_paciente_with_anamnese
):
    p = _seed_paciente_with_anamnese()

    form_data = {
        # Non-empty allergy should trigger a flag
        "alergias": "Penicilina",
        # Explicit yes on a boolean-like field also triggers
        "doenca_cardiaca": "sim",
    }

    update_anamnese(p.id, form_data, 1)

    a = _get_anamnese(p.id)
    assert a.has_red_flags is True


def test_update_anamnese_red_flag_removed(
    db_session, _seed_paciente_with_anamnese
):
    p = _seed_paciente_with_anamnese()

    # First set a red flag
    update_anamnese(
        p.id,
        {
            "alergias": "Penicilina",
            "doenca_cardiaca": "sim",
        },
        1,
    )
    a = _get_anamnese(p.id)
    assert a.has_red_flags is True

    # Then update with safe info
    update_anamnese(
        p.id,
        {
            "alergias": "Nenhuma",
            "doenca_cardiaca": "nao",
            "medicamentos": "",
            "historico_doencas": "",
        },
        1,
    )

    a2 = _get_anamnese(p.id)
    assert a2.has_red_flags is False


def test_create_paciente_sanitizes_strings(db_session):
    from app.services.paciente_service import create_paciente

    form_data = {
        "nome_completo": "  Teste Nome  ",
        "email": "  user@example.com  ",
        "logradouro": "  Rua A  ",
        "complemento": "   ",  # deve virar None
    }

    p = create_paciente(form_data, 1)

    # Verificar trims e normalização para None
    assert p.nome_completo == "Teste Nome"
    assert p.email == "user@example.com"
    assert p.logradouro == "Rua A"
    assert p.complemento is None


def test_update_anamnese_sets_status_and_timestamp(
    db_session, _seed_paciente_with_anamnese
):
    p = _seed_paciente_with_anamnese()

    form_data = {
        "alergias": "Nenhuma",
        "medicamentos": "",
        "historico_doencas": "",
    }

    before = datetime.now(timezone.utc) - timedelta(seconds=10)
    update_anamnese(p.id, form_data, 1)
    a: Anamnese = _get_anamnese(p.id)

    assert a.status == AnamneseStatus.CONCLUIDA
    assert a.data_atualizacao is not None
    # Timestamp should be close to 'now' (after 'before')
    # Normalize timezone if naive (defensive)
    dt = a.data_atualizacao
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    assert dt > before


def test_check_anamnese_alert_status_scenarios(db_session):
    # Cenário 1: AUSENTE (sem anamnese)
    p1 = Paciente()
    p1.nome_completo = "Paciente 1"
    db.session.add(p1)
    db.session.commit()
    assert paciente_service.check_anamnese_alert_status(p1) == "AUSENTE"

    # Cenário 2: PENDENTE (default)
    p2 = Paciente()
    p2.nome_completo = "Paciente 2"
    db.session.add(p2)
    db.session.flush()
    a2 = Anamnese()  # status default PENDENTE, sem data
    a2.paciente_id = p2.id
    db.session.add(a2)
    db.session.commit()
    assert paciente_service.check_anamnese_alert_status(p2) == "PENDENTE"

    # Cenário 3: PENDENTE (sem data) mesmo com status CONCLUIDA
    p3 = Paciente()
    p3.nome_completo = "Paciente 3"
    db.session.add(p3)
    db.session.flush()
    a3 = Anamnese()
    a3.paciente_id = p3.id
    a3.status = AnamneseStatus.CONCLUIDA
    a3.data_atualizacao = None
    db.session.add(a3)
    db.session.commit()
    assert paciente_service.check_anamnese_alert_status(p3) == "PENDENTE"

    # Cenário 4: EXPIRADA (181 dias atrás)
    p4 = Paciente()
    p4.nome_completo = "Paciente 4"
    db.session.add(p4)
    db.session.flush()
    a4 = Anamnese()
    a4.paciente_id = p4.id
    a4.status = AnamneseStatus.CONCLUIDA
    # 181 dias atrás deve ser EXPIRADA
    a4.data_atualizacao = datetime.now(timezone.utc) - timedelta(days=181)
    db.session.add(a4)
    db.session.commit()
    assert paciente_service.check_anamnese_alert_status(p4) == "EXPIRADA"

    # Cenário 5: OK (179 dias atrás)
    p5 = Paciente()
    p5.nome_completo = "Paciente 5"
    db.session.add(p5)
    db.session.flush()
    a5 = Anamnese()
    a5.paciente_id = p5.id
    a5.status = AnamneseStatus.CONCLUIDA
    a5.data_atualizacao = datetime.now(timezone.utc) - timedelta(days=179)
    db.session.add(a5)
    db.session.commit()
    assert paciente_service.check_anamnese_alert_status(p5) is None
