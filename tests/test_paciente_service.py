from __future__ import annotations

import pytest

from app import db
from app.models import Paciente, Anamnese
from app.services.paciente_service import update_anamnese


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

    update_anamnese(p.id, form_data)

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

    update_anamnese(p.id, form_data)

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
    )

    a2 = _get_anamnese(p.id)
    assert a2.has_red_flags is False
