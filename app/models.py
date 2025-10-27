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


# Status da Anamnese (Regra 7)
class AnamneseStatus(str, Enum):
    PENDENTE = "PENDENTE"
    CONCLUIDA = "CONCLUIDA"


# Status do Fechamento de Caixa (Regra 7)
class CaixaStatus(str, Enum):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"


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
    # Cor preferida do profissional (exibição na Agenda) — formato #RRGGBB
    color = db.Column(db.String(20), nullable=True)

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

    # Eventos de timeline de UX (Tela 5)
    timeline_eventos = db.relationship(
        "TimelineEvento",
        back_populates="paciente",
        lazy="dynamic",
        order_by="desc(TimelineEvento.timestamp)",
        cascade="all, delete-orphan",
    )

    # Snapshot inicial e estados vivos do odontograma (Regra 3)
    odontograma_inicial_json = db.Column(db.JSON, nullable=True)
    odontograma_inicial_data = db.Column(
        db.DateTime(timezone=True), nullable=True
    )
    odontograma_estados = db.relationship(
        "OdontogramaDenteEstado",
        back_populates="paciente",
        cascade="all, delete-orphan",
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
    status = db.Column(
        db.Enum(AnamneseStatus, name="anamnese_status_enum"),
        nullable=False,
        default=AnamneseStatus.PENDENTE,
        server_default=db.text("'PENDENTE'"),
    )

    # Timestamp da última atualização (UTC, timezone-aware)
    data_atualizacao = db.Column(db.DateTime(timezone=True), nullable=True)

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
    # Soft-delete: preservar histórico/auditoria (Regra 7)
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

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

    # Carnê Cosmético (ParcelaPrevista) - lembretes visuais (Regra 4)
    parcelas_previstas = db.relationship(
        "ParcelaPrevista",
        back_populates="plano",
        cascade="all, delete-orphan",
        lazy="dynamic",
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
    # Nome do procedimento congelado no momento da criação (Regra 4)
    procedimento_nome_historico = db.Column(
        db.String(255),
        nullable=False,
        server_default=db.text("'Procedimento não definido'"),
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
    # Diferenciar pagamento vs ajuste (Regra 4)

    class LancamentoTipo(str, Enum):
        PAGAMENTO = "PAGAMENTO"
        AJUSTE = "AJUSTE"

    tipo_lancamento = db.Column(
        db.Enum(LancamentoTipo, name="lancamento_tipo_enum"),
        nullable=False,
        default=LancamentoTipo.PAGAMENTO,
        server_default=db.text("'PAGAMENTO'"),
    )
    # Motivo livre para ajustes (obrigatório no service quando AJUSTE)
    notas_motivo = db.Column(db.Text, nullable=True)
    data_lancamento = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )

    plano = db.relationship("PlanoTratamento", back_populates="lancamentos")

    # Estorno: referência ao lançamento original (self-FK)
    lancamento_estornado_id = db.Column(
        db.Integer,
        db.ForeignKey("lancamentos_financeiros.id"),
        nullable=True,
        index=True,
    )
    lancamento_original = db.relationship(
        "LancamentoFinanceiro",
        remote_side=[id],
        backref="estornos",
        foreign_keys=[lancamento_estornado_id],
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lancamento plano_id={self.plano_id} valor={self.valor}>"

    # Compat: alguns testes e UIs esperam a propriedade `valor_pago`
    # como alias legível para o campo `valor`.
    @property
    def valor_pago(self):  # pragma: no cover - simples alias
        return self.valor


class ParcelaPrevista(db.Model):
    """Lembrete visual de parcelas previstas para um plano (Carnê Cosmético).

    Observações:
    - Não possui campo de status; status é calculado dinamicamente (Regra 4).
    - Mantida no bind default, com FK real para planos_tratamento.id.
    """

    __tablename__ = "parcela_prevista"

    id = db.Column(db.Integer, primary_key=True)
    plano_id = db.Column(
        db.Integer, db.ForeignKey("planos_tratamento.id"), nullable=False
    )
    data_vencimento = db.Column(db.Date, nullable=False)
    valor_previsto = db.Column(db.Numeric(10, 2), nullable=False)
    observacao = db.Column(db.String(100), nullable=True)

    plano = db.relationship(
        "PlanoTratamento", back_populates="parcelas_previstas"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ParcelaPrevista plano_id={self.plano_id} "
            f"venc={self.data_vencimento} valor={self.valor_previsto}>"
        )


class OdontogramaDenteEstado(db.Model):
    """Estado vivo do odontograma por dente.

    Mantido no bind default junto ao Paciente para permitir FK real e
    garantir unicidade (paciente_id, tooth_id).
    """

    __tablename__ = "odontograma_dente_estado"
    __table_args__ = (
        db.UniqueConstraint(
            "paciente_id", "tooth_id", name="uq_paciente_tooth_id"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(
        db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True
    )
    # FDI tooth id (e.g., "11", "48")
    tooth_id = db.Column(db.String(3), nullable=False, index=True)
    # JSON de estado conforme frontend (three_utils.js)
    estado_json = db.Column(db.JSON, nullable=False)

    paciente = db.relationship(
        "Paciente", back_populates="odontograma_estados"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<OdontogramaDenteEstado paciente_id={self.paciente_id} "
            f"tooth={self.tooth_id}>"
        )


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


# ----------------------------------
# Timeline UX (default bind)
# ----------------------------------


# Contexto da Timeline (PACIENTE ou SISTEMA)
class TimelineContexto(Enum):
    PACIENTE = "PACIENTE"
    SISTEMA = "SISTEMA"


class TimelineEvento(db.Model):
    """Evento legível para a timeline do paciente (Tela 5).

    Populado via 'escrita dupla' pela camada de services (Regra 7).
    Mantido no bind default (mesmo banco de Paciente) para FK real.
    Suporta eventos de paciente e de sistema/admin.
    """

    __tablename__ = "timeline_evento"

    id = db.Column(db.Integer, primary_key=True)

    # FK real, pois está no mesmo bind do modelo Paciente
    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("pacientes.id"),
        nullable=True,  # Agora permite NULL para eventos de sistema
        index=True,
    )

    # Referência lógica ao usuário (outro bind); não usar FK cross-bind
    usuario_id = db.Column(db.Integer, nullable=True, index=True)

    # Timestamp em UTC (timezone-aware)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        index=True,
    )

    # Categoria para filtragem e ícones na UI
    evento_tipo = db.Column(db.String(50), nullable=False, index=True)

    # Descrição legível exibida ao usuário
    descricao = db.Column(db.Text, nullable=False)

    # Contexto do evento (PACIENTE ou SISTEMA)
    evento_contexto = db.Column(
        db.Enum(TimelineContexto, name="timeline_contexto_enum"),
        nullable=False,
        default=TimelineContexto.PACIENTE,
        server_default="PACIENTE",
    )

    # Relacionamento reverso
    paciente = db.relationship("Paciente", back_populates="timeline_eventos")

    def __repr__(self) -> str:  # pragma: no cover
        short = (self.descricao or "")[:30]
        return f"<TimelineEvento {self.id} [{self.evento_tipo}] {short}>"


# ----------------------------------
# Agenda/Calendário (bind dedicado)
# ----------------------------------


class CalendarEvent(db.Model):
    """Evento de calendário independente do fluxo de agendamentos.

    Observações importantes:
    - Usa bind dedicado (calendario) para permitir evolução isolada.
    - Não define ForeignKeys cruzando binds (ver diretriz Multi-Bind).
    - Campos de data/hora usam timezone=True e devem armazenar UTC.
    """

    __bind_key__ = "calendario"
    __tablename__ = "calendar_events"
    __table_args__ = {"info": {"bind_key": "calendario"}}

    id = db.Column(db.Integer, primary_key=True)

    # Título e notas livres
    title = db.Column(
        db.String(500),
        nullable=False,
        default="",
        server_default=db.text("''"),
    )
    notes = db.Column(db.Text, nullable=True)

    # Datas em UTC, timezone-aware
    start = db.Column(db.DateTime(timezone=True), nullable=False)
    end = db.Column(db.DateTime(timezone=True), nullable=True)
    all_day = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text("0")
    )

    # Aparência e autoria
    color = db.Column(db.String(20), nullable=True)  # ex.: #0d6efd
    # Referência lógica ao usuário (outro bind): users.usuarios.id
    dentista_id = db.Column(db.Integer, nullable=True)

    # Referência opcional ao paciente (sem FK cross-bind)
    paciente_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<CalendarEvent id={self.id} title={self.title!r} "
            f"start={self.start} end={self.end}>"
        )


# ----------------------------------
# Feriados (bind calendario)
# ----------------------------------


class Holiday(db.Model):
    """Feriados e pontos facultativos por ano/UF.

    Observações:
    - Opera no bind dedicado 'calendario'.
    - Campo `date` (YYYY-MM-DD) armazenado como string e usado como PK.
    - Campos com timezone-aware conforme diretrizes (updated_at UTC).
    - Não utiliza FKs cross-bind.
    """

    __bind_key__ = "calendario"
    __tablename__ = "holiday"
    __table_args__ = {"info": {"bind_key": "calendario"}}

    # YYYY-MM-DD
    date = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    level = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(10), nullable=True)  # UF opcional
    year = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="invertexto")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Holiday {self.date} {self.name} ({self.level}/{self.type})>"


# ----------------------------------
# Fechamento de Caixa (default bind)
# ----------------------------------


class FechamentoCaixa(db.Model):
    """Controle de fechamento diário do caixa.

    - Usado para travar estornos em dias já fechados (Regra 7).
    """

    __tablename__ = "fechamento_caixa"

    data_fechamento = db.Column(db.Date, primary_key=True)
    status = db.Column(
        db.Enum(CaixaStatus, name="caixa_status_enum"),
        nullable=False,
        default=CaixaStatus.ABERTO,
        server_default=db.text("'ABERTO'"),
    )
    saldo_apurado = db.Column(db.Numeric(10, 2), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FechamentoCaixa {self.data_fechamento} {self.status}>"
