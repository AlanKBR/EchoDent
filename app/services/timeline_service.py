from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import SQLAlchemyError


from app import db
from app.models import TimelineEvento, TimelineContexto


def create_timeline_evento(
    evento_tipo: str,
    descricao: str,
    usuario_id: Optional[int],
    paciente_id: Optional[int] = None,
) -> bool:
    """
    Cria um novo evento na timeline (paciente ou sistema).
    Se paciente_id for fornecido, contexto é PACIENTE; senão, SISTEMA.
    Esta função DEVE ser atômica.
    Retorna True em caso de sucesso; False se ocorrer erro (com rollback).
    """
    try:
        contexto = TimelineContexto.PACIENTE if paciente_id is not None else TimelineContexto.SISTEMA
        evento = TimelineEvento()
        evento.paciente_id = int(paciente_id) if paciente_id is not None else None
        evento.usuario_id = int(usuario_id) if usuario_id is not None else None
        evento.evento_tipo = str(evento_tipo)
        evento.descricao = str(descricao)
        evento.evento_contexto = contexto
        db.session.add(evento)
        db.session.commit()
        return True
    except (SQLAlchemyError, ValueError, TypeError) as e:
        db.session.rollback()
        # Logaria o erro em um serviço de logging estruturado; print para DEV.
        print(f"Erro ao salvar evento na timeline: {e}")  # noqa: T201
        return False
