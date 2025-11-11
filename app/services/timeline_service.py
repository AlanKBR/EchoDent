from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Paciente, TimelineContexto, TimelineEvento


def create_timeline_evento(
    evento_tipo: str,
    descricao: str,
    usuario_id: int | None,
    paciente_id: int | None = None,
) -> bool:
    """
    Cria um novo evento na timeline (paciente ou sistema).
    Se paciente_id for fornecido, contexto é PACIENTE; senão, SISTEMA.
    Esta função DEVE ser atômica.
    Retorna True em caso de sucesso; False se ocorrer erro (com rollback).
    """
    try:
        contexto = (
            TimelineContexto.PACIENTE
            if paciente_id is not None
            else TimelineContexto.SISTEMA
        )
        evento = TimelineEvento()
        evento.paciente_id = (
            int(paciente_id) if paciente_id is not None else None
        )
        evento.usuario_id = int(usuario_id) if usuario_id is not None else None
        evento.evento_tipo = str(evento_tipo)
        evento.descricao = str(descricao)
        evento.evento_contexto = contexto
        db.session.add(evento)

        # Garante que timestamps server_default sejam materializados
        db.session.flush()  # não comita; apenas emite INSERT pendente

        # Denormalização: atualizar campos rápidos no Paciente (se aplicável)
        if paciente_id is not None:
            paciente = db.session.get(Paciente, int(paciente_id))
            if paciente is not None:
                # timestamp do evento recém-criado; se não materializado,
                # cairá em None e será tratado no commit
                paciente.ultima_interacao_at = evento.timestamp
                # descrição curta: usamos o tipo do evento como rótulo legível
                paciente.ultima_interacao_desc = str(evento.evento_tipo)

        db.session.commit()
        return True
    except (SQLAlchemyError, ValueError, TypeError) as e:
        db.session.rollback()
        # Logaria o erro em um serviço de logging estruturado; print para DEV.
        print(f"Erro ao salvar evento na timeline: {e}")  # noqa: T201
        return False
