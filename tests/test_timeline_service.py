import pytest

from app import db
from app.models import Paciente
from app.services import paciente_service, timeline_service


@pytest.mark.usefixtures("app_ctx")
def test_create_evento_updates_paciente_denormalization():
    # Arrange: criar paciente mínimo via service (aplica sanitização)
    novo = paciente_service.create_paciente(
        form_data={"nome_completo": "Paciente TL Test"}, usuario_id=1
    )
    assert novo.id is not None

    # Act: criar evento de timeline diretamente
    ok = timeline_service.create_timeline_evento(
        evento_tipo="PAGAMENTO",  # será usado como descricao_curta
        descricao="Pagamento PIX",
        usuario_id=1,
        paciente_id=novo.id,
    )
    assert ok is True

    # Assert: recarregar paciente e validar denormalização
    p = db.session.get(Paciente, novo.id)
    assert p is not None
    assert p.ultima_interacao_at is not None
    # descricao_curta usa o tipo do evento
    assert p.ultima_interacao_desc == "PAGAMENTO"
