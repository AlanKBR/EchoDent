from app import db
from app.models import TimelineEvento, TimelineContexto
from app.services import timeline_service

def test_create_timeline_evento_sistema(app):
    with app.app_context():
        # Deve criar evento de sistema (paciente_id=None)
        ok = timeline_service.create_timeline_evento(
            evento_tipo="SISTEMA",
            descricao="Caixa fechado pelo admin.",
            usuario_id=1,
            paciente_id=None,
        )
        assert ok is True
        evento = db.session.query(TimelineEvento).order_by(TimelineEvento.id.desc()).first()
        assert evento is not None
        assert evento.evento_tipo == "SISTEMA"
        assert evento.descricao == "Caixa fechado pelo admin."
        assert evento.evento_contexto == TimelineContexto.SISTEMA
        assert evento.paciente_id is None
