import pytest

from app import db
from app.models import Paciente


@pytest.fixture
def paciente_ficha(app_ctx):
    # Dentro de app_ctx que usa o mesmo app da fixture 'client'
    p = Paciente(nome_completo="Paciente Ficha")
    db.session.add(p)
    db.session.commit()
    return p


def test_post_atualizar_ficha_atomic(client, paciente_ficha):
    # Autenticar via rota dev (habilitada em TESTING)
    client.get("/__dev/login_as/admin")

    form = {
        "nome_completo": "  Novo Nome  ",
        "alergias": "  Aspirina  ",
    }
    resp = client.post(f"/pacientes/{paciente_ficha.id}/atualizar", data=form)
    assert resp.status_code in (200, 204)
    # Verificar commit aplicado
    p_db = db.session.get(Paciente, paciente_ficha.id)
    assert p_db.nome_completo == "Novo Nome"
    assert p_db.anamnese is not None
    assert p_db.anamnese.alergias == "Aspirina"


def test_get_ficha_returns_html(client, paciente_ficha):
    # Autenticar para acessar rota protegida
    client.get("/__dev/login_as/admin")
    resp = client.get(f"/pacientes/{paciente_ficha.id}/ficha")
    assert resp.status_code == 200
    assert b"ficha-paciente-container" in resp.data
    # Deve conter alerta inicial (AUSENTE/PENDENTE/DESATUALIZADA)
    assert (
        b"Anamnese AUSENTE" in resp.data
        or b"Anamnese PENDENTE" in resp.data
        or b"Anamnese DESATUALIZADA" in resp.data
    )
