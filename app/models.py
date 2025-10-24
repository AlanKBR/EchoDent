from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone

"""Model definitions for EchoDent.

Note: We intentionally do not use Flask-Login's UserMixin here to avoid a
name collision with the mandatory soft-delete column `is_active`. Flask-Login
only requires the User class to expose `is_authenticated`, `is_active`,
`is_anonymous`, and `get_id` attributes at runtime. The ORM column `is_active`
fulfills that contract by evaluating to a truthy/falsey value, and helper
properties/methods can be added later if/when authentication is wired.
"""

from . import db


# ----------------------------------
# Enums
# ----------------------------------


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    DENTISTA = "DENTISTA"
    SECRETARIA = "SECRETARIA"


# Estados de Plano de Tratamento
class StatusPlanoEnum(str, Enum):
    PROPOSTO = "PROPOSTO"
    APROVADO = "APROVADO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


# Estados do Agendamento
class StatusAgendamentoEnum(str, Enum):
    MARCADO = "MARCADO"
    CONFIRMADO = "CONFIRMADO"
    SALA_ESPERA = "SALA_ESPERA"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


# ----------------------------------
# Models
# ----------------------------------


class Usuario(db.Model):
    __bind_key__ = "users"
    __tablename__ = "usuarios"
    __table_args__ = {"info": {"bind_key": "users"}}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(RoleEnum, name="role_enum"), nullable=False)

    # Dados de perfil profissional do prescritor
    nome_completo = db.Column(db.String(200), nullable=True)
    cro_registro = db.Column(db.String(100), nullable=True)

    # Soft-delete: manter usuários por questões legais e auditoria
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text("1"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario {self.username} ({self.role})>"

    # Flask-Login protocol without inheriting UserMixin
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - trivial
        return True

    @property
    def is_anonymous(self) -> bool:  # pragma: no cover - trivial
        return False

    def get_id(self) -> str:  # pragma: no cover - trivial
        return str(self.id)


class Paciente(db.Model):
    __tablename__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(200), nullable=False)

    # Campos básicos de cadastro
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(
        db.String(14), unique=True, nullable=True
    )  # formato: 000.000.000-00
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Endereço
    cep = db.Column(db.String(9), nullable=True)  # 00000-000
    logradouro = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(120), nullable=True)
    cidade = db.Column(db.String(120), nullable=True)
    estado = db.Column(db.String(2), nullable=True)

    # Relacionamentos
    anamnese = db.relationship(
        "Anamnese",
        uselist=False,
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    planos_tratamento = db.relationship(
        "PlanoTratamento",
        back_populates="paciente",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Mídias associadas ao paciente (RX, documentos, imagens)
    media = db.relationship(
        "MediaPaciente",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )

    # Agendamentos do paciente
    agendamentos = db.relationship(
        "Agendamento",
        cascade="all, delete-orphan",
        backref="paciente",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Paciente {self.nome_completo}>"


class Anamnese(db.Model):
    __tablename__ = "anamneses"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("pacientes.id"),
        nullable=False,
        unique=True,  # garante 1-para-1 no nível do banco
    )

    alergias = db.Column(db.Text, nullable=True)
    medicamentos_uso_continuo = db.Column(db.Text, nullable=True)
    historico_doencas = db.Column(db.Text, nullable=True)
    has_red_flags = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.text("0"),
    )

    # Backref para paciente (um-para-um)
    paciente = db.relationship(
        "Paciente",
        back_populates="anamnese",
        uselist=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Anamnese paciente_id={self.paciente_id}>"


class Procedimento(db.Model):
    __tablename__ = "procedimentos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    valor_padrao = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Procedimento {self.nome}>"


class PlanoTratamento(db.Model):
    __tablename__ = "planos_tratamento"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False
    )

    # Referência ao dentista (users.db). Nao usar ForeignKey entre binds.
    dentista_id = db.Column(db.Integer, nullable=True)

    status = db.Column(
        db.Enum(StatusPlanoEnum, name="status_plano_enum"),
        nullable=False,
        default=StatusPlanoEnum.PROPOSTO,
        server_default=db.text("'PROPOSTO'"),
    )

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    desconto = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=db.text("0"),
    )
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    paciente = db.relationship("Paciente", back_populates="planos_tratamento")

    itens = db.relationship(
        "ItemPlano",
        back_populates="plano",
        cascade="all, delete-orphan",
    )

    lancamentos = db.relationship(
        "LancamentoFinanceiro",
        back_populates="plano",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PlanoTratamento id={self.id} paciente={self.paciente_id}>"


class ItemPlano(db.Model):
    __tablename__ = "itens_plano"

    id = db.Column(db.Integer, primary_key=True)
    plano_id = db.Column(
        db.Integer, db.ForeignKey("planos_tratamento.id"), nullable=False
    )
    procedimento_id = db.Column(
        db.Integer, db.ForeignKey("procedimentos.id"), nullable=False
    )
    valor_cobrado = db.Column(db.Numeric(10, 2), nullable=False)
    descricao_dente_face = db.Column(db.String(50), nullable=True)

    plano = db.relationship("PlanoTratamento", back_populates="itens")
    # Relacionamento direto para facilitar exibição do nome do procedimento
    procedimento = db.relationship("Procedimento")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ItemPlano plano_id={self.plano_id} "
            f"proc_id={self.procedimento_id}>"
        )


class LancamentoFinanceiro(db.Model):
    __tablename__ = "lancamentos_financeiros"

    id = db.Column(db.Integer, primary_key=True)
    plano_id = db.Column(
        db.Integer, db.ForeignKey("planos_tratamento.id"), nullable=False
    )
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pagamento = db.Column(db.String(50), nullable=False)
    data_lancamento = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )

    plano = db.relationship("PlanoTratamento", back_populates="lancamentos")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lancamento plano_id={self.plano_id} valor={self.valor}>"


# ----------------------------------
# Audit Log (history bind)
# ----------------------------------


class LogAuditoria(db.Model):
    __bind_key__ = "history"
    __tablename__ = "log_auditoria"
    __table_args__ = {"info": {"bind_key": "history"}}

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # Referência cruzada a usuarios.id (outro bind); não usar ForeignKey
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(
        db.String(20), nullable=False
    )  # create | update | delete
    model_name = db.Column(db.String(200), nullable=False)
    model_id = db.Column(db.Integer, nullable=False)
    changes_json = db.Column(db.Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LogAuditoria {self.action} {self.model_name}({self.model_id})>"
        )


class MediaPaciente(db.Model):
    __tablename__ = "media_pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False
    )
    # Caminho relativo sob instance/media_storage/
    # Ex.: "1/panoramica_2025.jpg"
    file_path = db.Column(db.String(500), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    paciente = db.relationship("Paciente", back_populates="media")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MediaPaciente paciente_id={self.paciente_id} "
            f"path={self.file_path}>"
        )


class Agendamento(db.Model):
    __tablename__ = "agendamentos"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False
    )
    # Referência ao dentista (users.db). Não usar ForeignKey entre binds.
    dentista_id = db.Column(db.Integer, nullable=True)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    status = db.Column(
        db.Enum(StatusAgendamentoEnum, name="status_agendamento_enum"),
        nullable=False,
        default=StatusAgendamentoEnum.MARCADO,
        server_default=db.text("'MARCADO'"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Agendamento id={self.id} paciente_id={self.paciente_id} "
            f"{self.start_time} - {self.end_time} status={self.status}>"
        )
