from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.models import Anamnese, AnamneseStatus, Paciente
from app.services.paciente_service import (
    get_anamnese_status,
    update_ficha_anamnese_atomic,
)


@pytest.fixture
def paciente_base(app_ctx):
    p = Paciente(nome_completo="Teste Status")
    db.session.add(p)
    db.session.flush()
    # criar anamnese vazia pendente
    a = Anamnese(paciente_id=p.id)
    db.session.add(a)
    db.session.commit()
    return p


def test_anamnese_status_pendente(app_ctx, paciente_base):
    p = db.session.get(Paciente, paciente_base.id)
    st = get_anamnese_status(p)
    assert st["status"] == "PENDENTE"
    assert st["mostrar_alerta"] is True


def test_anamnese_status_desatualizada(app_ctx, paciente_base):
    # Atualiza anamnese para concluída mas com data antiga (>180d)
    a = paciente_base.anamnese
    assert a is not None
    a.status = AnamneseStatus.CONCLUIDA
    a.data_atualizacao = datetime.now(timezone.utc) - timedelta(days=200)
    db.session.commit()
    st = get_anamnese_status(paciente_base)
    assert st["status"] == "DESATUALIZADA"
    assert st["mostrar_alerta"] is True


def test_anamnese_status_valida(app_ctx, paciente_base):
    a = paciente_base.anamnese
    assert a is not None
    a.status = AnamneseStatus.CONCLUIDA
    a.data_atualizacao = datetime.now(timezone.utc) - timedelta(days=30)
    db.session.commit()
    st = get_anamnese_status(paciente_base)
    assert st["status"] == "VALIDA"
    assert st["mostrar_alerta"] is False


def test_update_ficha_anamnese_atomic_sanitiza(app_ctx):
    p = Paciente(nome_completo="   Nome Sujo   ")
    db.session.add(p)
    db.session.commit()
    form = {
        "nome_completo": "   Novo Nome   ",
        "telefone": " 1111 2222  ",
        "alergias": "  Dipirona  ",
    }
    update_ficha_anamnese_atomic(
        paciente_id=p.id,
        form_data=form,
        usuario_id=1,
    )
    p_db = db.session.get(Paciente, p.id)
    assert p_db.nome_completo == "Novo Nome"
    assert p_db.telefone == "1111 2222"
    a = p_db.anamnese
    assert a is not None
    assert a.alergias == "Dipirona"
    # confirmação de status concluída e data atual
    assert a.status == AnamneseStatus.CONCLUIDA
    assert a.data_atualizacao is not None
