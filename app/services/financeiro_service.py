from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping, Optional

from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    Usuario,
    PlanoTratamento,
    LancamentoFinanceiro,
    ItemPlano,
    StatusPlanoEnum,
    Procedimento,
)


# ----------------------------------
# Helpers (Multi-bind validation)
# ----------------------------------


def _to_decimal(value: object) -> Decimal:
    """Best-effort conversion to Decimal with 2 decimal places.

    Accepts Decimal, int, float, or str. Leaves Decimal untouched.
    """
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        raise ValueError("Valor numérico inválido")


def _validar_dentista_existe(dentista_id: Optional[int]) -> bool:
    """Valida referencialmente se o dentista existe no bind 'users'."""
    if dentista_id is None:
        return False
    # Flask‑SQLAlchemy 3.x: session.get(Model, pk)
    return db.session.get(Usuario, dentista_id) is not None


# ----------------------------------
# Core Financeiro (Fluxo de Ouro)
# ----------------------------------


def create_plano(
    paciente_id: int,
    dentista_id: Optional[int],
    itens_data: Iterable[Mapping[str, object]],
) -> PlanoTratamento:
    """Cria um Plano de Tratamento (orçamento) e seus itens.

    itens_data: iterável de dicts com chaves:
      - procedimento_id (obrigatório)
      - valor_cobrado (opcional; utiliza Procedimento.valor_padrao se ausente)
      - descricao_dente_face (opcional)
    """
    if not _validar_dentista_existe(dentista_id):
        raise ValueError("Dentista não encontrado no banco de usuários.")

    itens_data = list(itens_data or [])
    if not itens_data:
        raise ValueError(
            "É necessário informar ao menos um item para o plano."
        )

    subtotal = Decimal("0")
    itens_models: list[ItemPlano] = []

    for item in itens_data:
        proc_raw = item.get("procedimento_id")
        if proc_raw is None:
            raise ValueError("Item sem 'procedimento_id'.")
        try:
            proc_id = int(str(proc_raw))
        except (TypeError, ValueError):
            raise ValueError("procedimento_id inválido.")

        procedimento = db.session.get(Procedimento, proc_id)
        if procedimento is None:
            raise ValueError(f"Procedimento id={proc_id} não encontrado.")

        if "valor_cobrado" in item and item["valor_cobrado"] is not None:
            valor_cobrado = _to_decimal(item["valor_cobrado"])
        else:
            valor_cobrado = _to_decimal(procedimento.valor_padrao)

        descricao = item.get("descricao_dente_face")
        subtotal += valor_cobrado

        it_model = ItemPlano()
        it_model.procedimento_id = procedimento.id
        it_model.valor_cobrado = valor_cobrado
        it_model.descricao_dente_face = (
            str(descricao) if descricao else None
        )
        itens_models.append(it_model)

    # Inicialmente PROPOSTO: valor_total pode iniciar igual ao subtotal
    plano = PlanoTratamento()
    plano.paciente_id = paciente_id
    plano.dentista_id = dentista_id
    plano.status = StatusPlanoEnum.PROPOSTO
    plano.subtotal = subtotal
    plano.desconto = Decimal("0")
    plano.valor_total = subtotal
    for it in itens_models:
        plano.itens.append(it)

    db.session.add(plano)
    db.session.commit()
    return plano


def approve_plano(plano_id: int, desconto: object = 0) -> PlanoTratamento:
    """Aprova um plano PROPOSTO, aplicando desconto e liberando pagamentos."""
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if plano is None:
        raise ValueError("Plano não encontrado.")
    if plano.status != StatusPlanoEnum.PROPOSTO:
        raise ValueError("Somente planos PROPOSTO podem ser aprovados.")

    desconto_dec = _to_decimal(desconto)
    valor_total = _to_decimal(plano.subtotal) - desconto_dec
    # Não permitir valor_total negativo
    if valor_total < Decimal("0"):
        raise ValueError("Desconto não pode exceder o subtotal do plano.")

    plano.desconto = desconto_dec
    plano.valor_total = valor_total
    plano.status = StatusPlanoEnum.APROVADO

    db.session.add(plano)
    db.session.commit()
    return plano


def add_lancamento(
    plano_id: int, valor: object, metodo_pagamento: str
) -> LancamentoFinanceiro:
    """Registra um pagamento vinculado a um plano APROVADO ou CONCLUIDO.

    Nota: Esta função apenas adiciona e faz flush; não faz commit para
    permitir transações atômicas (ex.: recibo avulso cria plano + lançamento e
    commita ao final).
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if plano is None:
        raise ValueError("Plano não encontrado para lançamento.")
    if plano.status not in (
        StatusPlanoEnum.APROVADO,
        StatusPlanoEnum.CONCLUIDO,
    ):
        raise ValueError(
            "Lançamentos só são permitidos para planos APROVADO ou CONCLUIDO."
        )

    valor_dec = _to_decimal(valor)
    lanc = LancamentoFinanceiro()
    lanc.plano_id = plano.id
    lanc.valor = valor_dec
    lanc.metodo_pagamento = str(metodo_pagamento)
    db.session.add(lanc)
    # flush para garantir ID disponível sem encerrar transação
    db.session.flush()
    return lanc


def create_recibo_avulso(
    paciente_id: int,
    dentista_id: Optional[int],
    valor: object,
    motivo_descricao: Optional[str],
) -> PlanoTratamento:
    """Cria um plano fantasma concluído e registra o pagamento avulso.

    A operação é tratada como transação atômica (plano + lançamento).
    """
    if not _validar_dentista_existe(dentista_id):
        raise ValueError("Dentista não encontrado no banco de usuários.")

    valor_dec = _to_decimal(valor)
    plano = PlanoTratamento()
    plano.paciente_id = paciente_id
    plano.dentista_id = dentista_id
    plano.status = StatusPlanoEnum.CONCLUIDO
    plano.subtotal = valor_dec
    plano.desconto = Decimal("0")
    plano.valor_total = valor_dec

    # Não há campo de observação no modelo, então opcionalmente, poderíamos
    # anexar uma nota no primeiro ItemPlano. Como não é obrigatório, omitimos.

    db.session.add(plano)
    db.session.flush()  # garante plano.id

    # Registrar o lançamento imediatamente
    add_lancamento(
        plano_id=plano.id,
        valor=valor_dec,
        metodo_pagamento="AVULSO",
    )

    db.session.commit()
    return plano


def get_saldo_devedor_paciente(paciente_id: int) -> Decimal:
    """Retorna o saldo devedor: total_devido - total_pago para o paciente."""
    # total_devido = SUM(valor_total) em planos APROVADO ou CONCLUIDO
    total_devido = (
        db.session.query(
            func.coalesce(func.sum(PlanoTratamento.valor_total), 0)
        )
        .filter(
            PlanoTratamento.paciente_id == paciente_id,
            PlanoTratamento.status.in_(
                [StatusPlanoEnum.APROVADO, StatusPlanoEnum.CONCLUIDO]
            ),
        )
        .scalar()
    )

    # total_pago = SUM(lanc.valor) join com PlanoTratamento para filtrar
    # paciente
    total_pago = (
        db.session.query(
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)
        )
        .join(
            PlanoTratamento,
            LancamentoFinanceiro.plano_id == PlanoTratamento.id,
        )
        .filter(PlanoTratamento.paciente_id == paciente_id)
        .scalar()
    )

    # Garantir Decimal
    total_devido_dec = _to_decimal(total_devido)
    total_pago_dec = _to_decimal(total_pago)
    return total_devido_dec - total_pago_dec


def get_planos_by_paciente(paciente_id: int) -> list[PlanoTratamento]:
    """Retorna todos os planos do paciente, do mais novo para o mais antigo.

    Como não há timestamp de criação no modelo, ordenamos por id desc como
    aproximação natural de recência.
    """
    return (
        db.session.query(PlanoTratamento)
        .filter(PlanoTratamento.paciente_id == paciente_id)
        .order_by(PlanoTratamento.created_at.desc())
        .all()
    )


def get_all_procedimentos() -> list[Procedimento]:
    """Retorna todos os procedimentos (tabela de preços)."""
    return (
        db.session.query(Procedimento)
        .order_by(Procedimento.nome.asc())
        .all()
    )


def get_procedimento_by_id(procedimento_id: int) -> Optional[Procedimento]:
    return db.session.get(Procedimento, int(procedimento_id))


def get_plano_by_id(plano_id: int) -> Optional[PlanoTratamento]:
    """Recupera um PlanoTratamento por ID com eager loading de relações."""
    return (
        db.session.query(PlanoTratamento)
        .options(
            joinedload(PlanoTratamento.itens)  # type: ignore[arg-type]
            .joinedload(ItemPlano.procedimento),  # type: ignore[arg-type]
            joinedload(PlanoTratamento.lancamentos),  # type: ignore[arg-type]
        )
        .filter(PlanoTratamento.id == int(plano_id))
        .one_or_none()
    )


def get_saldo_devedor_plano(plano_id: int) -> Decimal:
    """Saldo devedor do plano: valor_total - total_pago."""
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if not plano:
        raise ValueError("Plano não encontrado.")

    total_pago = (
        db.session.query(
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)
        )
        .filter(LancamentoFinanceiro.plano_id == plano_id)
        .scalar()
    )

    total_pago_dec = _to_decimal(total_pago)
    return _to_decimal(plano.valor_total) - total_pago_dec
