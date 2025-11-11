import pytest

from app import db
from app.models import Usuario
from app.services import user_preferences_service


@pytest.mark.usefixtures("app_ctx")
def test_user_preferences_get_returns_default_for_new_user():
    # Arrange: obter um usuário existente (semente deve prover)
    user = db.session.query(Usuario).first()
    assert user is not None

    # Act
    cols = user_preferences_service.get_paciente_lista_colunas(user.id)

    # Assert: chaves e tipos
    expected_keys = {
        "telefone",
        "email",
        "idade",
        "sexo",
        "data_ultimo_registro",
        "status_anamnese",
        "cpf",
        "cidade",
    }
    assert expected_keys.issubset(set(cols.keys()))
    assert all(isinstance(v, bool) for v in cols.values())


@pytest.mark.usefixtures("app_ctx")
def test_user_preferences_update_and_get_roundtrip():
    # Arrange
    user = db.session.query(Usuario).first()
    assert user is not None

    payload = {
        "telefone": False,
        "email": True,
        "idade": True,
        "sexo": True,
        "data_ultimo_registro": False,
        "status_anamnese": False,
        "cpf": True,
        "cidade": False,
    }

    # Act
    ok = user_preferences_service.update_paciente_lista_colunas(
        user.id, payload
    )
    assert ok is True

    cols = user_preferences_service.get_paciente_lista_colunas(user.id)

    # Assert: os valores enviados devem ser refletidos
    for k, v in payload.items():
        assert cols[k] == v
