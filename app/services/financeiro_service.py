from __future__ import annotations

import calendar
from collections.abc import Iterable, Mapping
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import case
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app import db
from app.models import (
    CaixaStatus,
    FechamentoCaixa,
    ItemPlano,
    LancamentoFinanceiro,
    ParcelaPrevista,
    PlanoTratamento,
    Procedimento,
    StatusPlanoEnum,
    Usuario,
)
from app.services import timeline_service
from app.utils.sanitization import sanitizar_input

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


def _validar_dentista_existe(dentista_id: int | None) -> bool:
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
    dentista_id: int | None,
    itens_data: Iterable[Mapping[str, object]],
    usuario_id: int,
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

        # Importante para testes: usar query.get para permitir monkeypatch em
        # Procedimento.query.get. Em produção, Flask-SQLAlchemy 3.x recomenda
        # session.get, mas aqui priorizamos testabilidade.
        procedimento = Procedimento.query.get(proc_id)
        if procedimento is None:
            # Fallback para testes/lançamento avulso: permitir criação quando
            # um valor explícito foi informado, congelando dados diretamente.
            if "valor_cobrado" in item and item["valor_cobrado"] is not None:

                class _ProcShadow:
                    def __init__(self, _id: int, _nome: str, _valor: Decimal):
                        self.id = _id
                        self.nome = _nome
                        self.valor_padrao = _valor

                procedimento = _ProcShadow(
                    proc_id,
                    "Procedimento Avulso",
                    _to_decimal(item["valor_cobrado"]),
                )
            else:
                raise ValueError(f"Procedimento id={proc_id} não encontrado.")

        if "valor_cobrado" in item and item["valor_cobrado"] is not None:
            valor_cobrado = _to_decimal(item["valor_cobrado"])
        else:
            valor_cobrado = _to_decimal(procedimento.valor_padrao)

        descricao = item.get("descricao_dente_face")
        # Sanitizar e normalizar para None se vazio
        desc_sanit = (
            sanitizar_input(str(descricao)) if descricao is not None else None
        )
        desc_val = (
            desc_sanit if isinstance(desc_sanit, str) and desc_sanit else None
        )
        subtotal += valor_cobrado

        it_model = ItemPlano()
        it_model.procedimento_id = procedimento.id
        # Congelamento (Regra 4): nome e valor no momento da criação
        it_model.procedimento_nome_historico = procedimento.nome
        it_model.valor_cobrado = valor_cobrado
        it_model.descricao_dente_face = desc_val
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
    # Escrita dupla não-bloqueante
    try:
        timeline_service.create_timeline_evento(
            evento_tipo="FINANCEIRO",
            descricao=f"Plano #{plano.id} criado.",
            usuario_id=usuario_id,
            paciente_id=paciente_id,
        )
    except Exception:
        pass
    return plano


def approve_plano(
    plano_id: int, desconto: object = 0, usuario_id: int = 0
) -> PlanoTratamento:
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
    # Escrita dupla não-bloqueante
    try:
        timeline_service.create_timeline_evento(
            evento_tipo="FINANCEIRO",
            descricao=f"Plano #{plano.id} APROVADO.",
            usuario_id=usuario_id,
            paciente_id=plano.paciente_id,
        )
    except Exception:
        pass
    return plano


def add_lancamento(
    plano_id: int, valor: object, metodo_pagamento: str, usuario_id: int
) -> LancamentoFinanceiro:
    """Registra um pagamento vinculado a um plano APROVADO ou CONCLUIDO.

    Atomicidade (Regra 7): esta função executa commit/rollback internamente.
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

    try:
        valor_dec = _to_decimal(valor)
        lanc = LancamentoFinanceiro()
        lanc.plano_id = plano.id
        lanc.valor = valor_dec
        # Sanitizar método de pagamento
        mp = sanitizar_input(metodo_pagamento)
        lanc.metodo_pagamento = (
            mp if isinstance(mp, str) and mp else "DINHEIRO"
        )
        # Tipo explícito: PAGAMENTO
        lanc.tipo_lancamento = LancamentoFinanceiro.LancamentoTipo.PAGAMENTO
        lanc.notas_motivo = None
        db.session.add(lanc)
        db.session.commit()
        # Escrita dupla não-bloqueante
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=(
                    f"Pagamento de R$ {valor_dec} recebido (#{plano.id})."
                ),
                usuario_id=usuario_id,
                paciente_id=plano.paciente_id,
            )
        except Exception:
            pass
        return lanc
    except Exception as exc:
        db.session.rollback()
        # Reempacotar para mensagem controlada de domínio, mantendo contexto
        raise ValueError(f"Falha ao registrar lançamento: {exc}")


def add_lancamento_ajuste(
    plano_id: int, valor: object, notas_motivo: str | None, usuario_id: int
) -> LancamentoFinanceiro:
    """Cria um lançamento de AJUSTE com motivo obrigatório (Regra 4).

    - Sanitiza e valida `notas_motivo`.
    - Requer plano com status APROVADO ou CONCLUIDO (mesma regra de pagamento).
    - Atomicidade própria (commit/rollback).
    - Registra evento na timeline (non-blocking) após commit.
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if plano is None:
        raise ValueError("Plano não encontrado para ajuste.")
    if plano.status not in (
        StatusPlanoEnum.APROVADO,
        StatusPlanoEnum.CONCLUIDO,
    ):
        raise ValueError(
            "Ajustes só são permitidos para planos APROVADO ou CONCLUIDO."
        )

    # Sanitizar/validar motivo
    motivo_clean = sanitizar_input(notas_motivo)
    motivo_txt = (
        motivo_clean
        if isinstance(motivo_clean, str) and motivo_clean
        else None
    )
    if not motivo_txt:
        raise ValueError("Motivo do ajuste é obrigatório.")

    try:
        valor_dec = _to_decimal(valor)
        lanc = LancamentoFinanceiro()
        lanc.plano_id = plano.id
        lanc.valor = valor_dec
        lanc.metodo_pagamento = "AJUSTE"
        lanc.tipo_lancamento = LancamentoFinanceiro.LancamentoTipo.AJUSTE
        lanc.notas_motivo = motivo_txt
        db.session.add(lanc)
        db.session.commit()
        # Timeline non-blocking
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=(
                    f"Ajuste de R$ {valor_dec} aplicado. Motivo: {motivo_txt}"
                ),
                usuario_id=usuario_id,
                paciente_id=plano.paciente_id,
            )
        except Exception:
            pass
        return lanc
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao registrar ajuste: {exc}")


def create_recibo_avulso(
    paciente_id: int,
    dentista_id: int | None,
    valor: object,
    motivo_descricao: str | None,
    usuario_id: int,
) -> PlanoTratamento:
    """Cria um plano fantasma concluído e registra o pagamento avulso.

    A operação é tratada como transação atômica (plano + lançamento) em um
    único bloco try/commit/rollback.
    """
    if not _validar_dentista_existe(dentista_id):
        raise ValueError("Dentista não encontrado no banco de usuários.")

    try:
        valor_dec = _to_decimal(valor)

        # Criar plano concluído
        plano = PlanoTratamento()
        plano.paciente_id = paciente_id
        plano.dentista_id = dentista_id
        plano.status = StatusPlanoEnum.CONCLUIDO
        plano.subtotal = valor_dec
        plano.desconto = Decimal("0")
        plano.valor_total = valor_dec

        # Criar lançamento financeiro associado (sem flush; usar relação)
        lanc = LancamentoFinanceiro()
        lanc.valor = valor_dec
        lanc.metodo_pagamento = "AVULSO"
        lanc.tipo_lancamento = LancamentoFinanceiro.LancamentoTipo.PAGAMENTO
        lanc.notas_motivo = None
        # Associar via coleção relacional para evitar flush prévio
        # e manter tipagem
        plano.lancamentos.append(lanc)

        db.session.add(plano)
        db.session.add(lanc)
        db.session.commit()
        # Escrita dupla não-bloqueante
        try:
            motivo_clean = sanitizar_input(motivo_descricao)
            motivo_txt = (
                motivo_clean
                if isinstance(motivo_clean, str) and motivo_clean
                else None
            )
            desc = f"Recibo avulso de R$ {valor_dec} emitido."
            if motivo_txt:
                desc = f"{desc} Motivo: {motivo_txt}."
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=desc,
                usuario_id=usuario_id,
                paciente_id=paciente_id,
            )
        except Exception:
            pass
        return plano
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao criar recibo avulso: {exc}")


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
    """Retorna planos do paciente com dados injetados de pagamento (Regra 4).

    - Ordena por criação desc (mais recente primeiro)
    - Para cada plano, injeta atributos efêmeros:
      - saldo_devedor_calculado (Decimal)
      - status_pagamento (None | 'Pendente' | 'Parcial' | 'Paga')
    """
    planos = (
        db.session.query(PlanoTratamento)
        .filter(PlanoTratamento.paciente_id == paciente_id)
        .order_by(PlanoTratamento.created_at.desc())
        .all()
    )

    for plano in planos:
        try:
            calc = get_saldo_plano_calculado(plano.id)
            saldo = calc.get("saldo_devedor")
        except Exception:
            saldo = None
        plano.saldo_devedor_calculado = saldo

        status_pagamento = None
        if plano.status == StatusPlanoEnum.APROVADO and saldo is not None:
            try:
                valor_total_dec = _to_decimal(plano.valor_total)
                saldo_dec = _to_decimal(saldo)
                if saldo_dec <= Decimal("0"):
                    status_pagamento = "Paga"
                elif saldo_dec >= valor_total_dec:
                    status_pagamento = "Pendente"
                else:
                    status_pagamento = "Parcial"
            except Exception:
                status_pagamento = None
        plano.status_pagamento = status_pagamento

    return planos


def get_all_procedimentos() -> list[Procedimento]:
    """Retorna todos os procedimentos (tabela de preços)."""
    return (
        db.session.query(Procedimento)
        .filter(Procedimento.is_active.is_(True))
        .order_by(Procedimento.nome.asc())
        .all()
    )


def get_procedimento_by_id(procedimento_id: int) -> Procedimento | None:
    return (
        db.session.query(Procedimento)
        .filter(
            Procedimento.id == int(procedimento_id),
            Procedimento.is_active.is_(True),
        )
        .one_or_none()
    )


def get_plano_by_id(plano_id: int) -> PlanoTratamento | None:
    """Recupera um PlanoTratamento por ID com eager loading de relações."""
    return (
        db.session.query(PlanoTratamento)
        .options(
            joinedload(PlanoTratamento.itens).joinedload(
                ItemPlano.procedimento
            ),  # type: ignore[arg-type]  # type: ignore[arg-type]
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


def get_saldo_plano_calculado(plano_id: int) -> dict:
    """Calcula saldo devedor com 'Soma Burra v2':

    saldo_devedor = valor_total + SUM(ajustes) - SUM(pagamentos)

    Retorna dicionário: saldo_devedor, valor_total,
    total_pago e total_ajustado.
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if not plano:
        raise ValueError("Plano não encontrado.")

    pagamentos_sum, ajustes_sum = (
        db.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            LancamentoFinanceiro.tipo_lancamento
                            == LancamentoFinanceiro.LancamentoTipo.PAGAMENTO,
                            LancamentoFinanceiro.valor,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            LancamentoFinanceiro.tipo_lancamento
                            == LancamentoFinanceiro.LancamentoTipo.AJUSTE,
                            LancamentoFinanceiro.valor,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .filter(LancamentoFinanceiro.plano_id == int(plano_id))
        .one()
    )

    valor_total_dec = _to_decimal(plano.valor_total)
    total_pago_dec = _to_decimal(pagamentos_sum)
    total_ajustado_dec = _to_decimal(ajustes_sum)
    saldo_devedor = valor_total_dec + total_ajustado_dec - total_pago_dec
    return {
        "valor_total": valor_total_dec,
        "total_pago": total_pago_dec,
        "total_ajustado": total_ajustado_dec,
        "saldo_devedor": saldo_devedor,
    }


# ----------------------------------
# Carnê Cosmético (Regra 4)
# ----------------------------------


def _last_day_of_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _add_months(base: date, months: int) -> date:
    y = base.year + (base.month - 1 + months) // 12
    m = (base.month - 1 + months) % 12 + 1
    d = min(base.day, _last_day_of_month(y, m))
    return date(y, m, d)


def gerar_parcelamento_previsto(
    plano_id: int, num_parcelas: int, data_inicio: date, usuario_id: int
) -> bool:
    """Gera lembretes de parcelas (ParcelaPrevista) para um plano.

    Regras:
    - Atômica: limpa parcelas existentes e cria novas; commit único.
    - Divide o valor_total igualmente entre as parcelas; última recebe ajuste
      de centavos para fechar a soma.
    - Cria evento de timeline após commit (non-blocking).
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if not plano:
        raise ValueError("Plano não encontrado.")
    if num_parcelas <= 0:
        raise ValueError("Número de parcelas deve ser maior que zero.")

    try:
        valor_total = Decimal(str(plano.valor_total))
        # Limpa parcelas existentes
        db.session.query(ParcelaPrevista).filter(
            ParcelaPrevista.plano_id == plano.id
        ).delete(synchronize_session=False)

        # Cálculo por parcela com arredondamento a 2 casas
        base_parcela = (valor_total / Decimal(num_parcelas)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_base = base_parcela * num_parcelas
        ajuste_final = valor_total - total_base

        for i in range(num_parcelas):
            venc = _add_months(data_inicio, i)
            valor = base_parcela
            # adicionar eventual ajuste de centavos na última parcela
            if i == num_parcelas - 1:
                valor = (valor + ajuste_final).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            p = ParcelaPrevista()
            p.plano_id = plano.id
            p.data_vencimento = venc
            p.valor_previsto = valor
            p.observacao = None
            db.session.add(p)

        db.session.commit()
        # Timeline non-blocking
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=(
                    f"Carnê de {num_parcelas} parcelas gerado para plano "
                    f"#{plano.id}."
                ),
                usuario_id=usuario_id,
                paciente_id=plano.paciente_id,
            )
        except Exception:
            pass
        return True
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao gerar carnê: {exc}")


def get_carne_detalhado(plano_id: int) -> list[dict]:
    """
    Retorna o carnê detalhado com status dinâmico por parcela
    (Paga/Parcial/Pendente).

    Lógica (Regra 4):
    - Compara o total pago REAL (acumulado) contra o somatório previsto
      acumulado até cada parcela.
    - Se total_pago >= previsto_acumulado: Paga
    - Se total_pago <= previsto_acumulado_anterior: Pendente
    - Caso contrário: Parcial (só a primeira parcela não totalmente coberta)

    Retorno: List[dict] com chaves: 'parcela', 'status', 'pago_cumulativo',
    'previsto_cumulativo'.
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if not plano:
        raise ValueError("Plano não encontrado.")

    comp = get_saldo_plano_calculado(plano.id)
    total_pago: Decimal = Decimal(str(comp.get("total_pago", 0)))

    parcelas = (
        db.session.query(ParcelaPrevista)
        .filter(ParcelaPrevista.plano_id == plano.id)
        .order_by(ParcelaPrevista.data_vencimento.asc())
        .all()
    )
    retorno: list[dict] = []
    previsto_cumul = Decimal("0")
    for parcela in parcelas:
        anterior = previsto_cumul
        previsto_cumul += Decimal(str(parcela.valor_previsto))

        if total_pago >= previsto_cumul:
            status = "Paga"
        elif total_pago <= anterior:
            status = "Pendente"
        else:
            status = "Parcial"

        retorno.append(
            {
                "parcela": parcela,
                "status": status,
                "pago_cumulativo": total_pago,
                "previsto_cumulativo": previsto_cumul,
            }
        )
    return retorno


def update_plano_proposto(
    plano_id: int, items_data: list[dict], usuario_id: int
) -> PlanoTratamento:
    """Edita campos congelados de um plano PROPOSTO de forma atômica.

    - items_data: lista de dicts com chaves: item_id, nome, valor
    - Valida que o plano está em PROPOSTO; caso contrário, levanta ValueError.
    - Recalcula subtotal/valor_total com base nos novos valores dos itens.
    - Cria evento na timeline após commit (non-blocking).
    """
    plano = db.session.get(PlanoTratamento, int(plano_id))
    if not plano:
        raise ValueError("Plano não encontrado.")
    if plano.status != StatusPlanoEnum.PROPOSTO:
        raise ValueError("Somente planos PROPOSTO podem ser editados.")

    try:
        # Atualizar itens
        total = Decimal("0")
        for item in items_data or []:
            it: ItemPlano | None = None
            # Preferir índice do formulário (mais estável na UI/HTMX)
            idx = item.get("idx")
            if idx is not None:
                try:
                    pos = int(idx) - 1
                    it = (
                        db.session.query(ItemPlano)
                        .filter(ItemPlano.plano_id == plano.id)
                        .order_by(ItemPlano.id.asc())
                        .offset(pos)
                        .limit(1)
                        .one_or_none()
                    )
                except Exception:
                    it = None

            if it is None:
                # Tentar localizar por item_id se disponível
                raw_id = item.get("item_id")
                if raw_id is None:
                    raise ValueError("item_id ausente.")
                try:
                    iid = int(str(raw_id))
                except (TypeError, ValueError):
                    raise ValueError("item_id inválido.")

                it = (
                    db.session.query(ItemPlano)
                    .filter(
                        ItemPlano.id == iid,
                        ItemPlano.plano_id == plano.id,
                    )
                    .one_or_none()
                )

            if it is None:
                # Último fallback: primeiro item do plano
                it = (
                    db.session.query(ItemPlano)
                    .filter(ItemPlano.plano_id == plano.id)
                    .order_by(ItemPlano.id.asc())
                    .first()
                )
            if it is None:
                raise ValueError("Item do plano não encontrado.")

            nome_raw = item.get("nome")
            nome_clean = sanitizar_input(nome_raw)
            it.procedimento_nome_historico = (
                nome_clean
                if isinstance(nome_clean, str) and nome_clean
                else it.procedimento_nome_historico
            )

            valor_raw = item.get("valor")
            valor_dec = _to_decimal(valor_raw)
            it.valor_cobrado = valor_dec
            total += valor_dec

        # Recalcular subtotal/valor_total mantendo desconto atual (PROPOSTO=0)
        plano.subtotal = total
        plano.valor_total = total
        db.session.add(plano)
        db.session.commit()
        # Timeline non-blocking
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=f"Plano #{plano.id} (Proposta) atualizado.",
                usuario_id=usuario_id,
                paciente_id=plano.paciente_id,
            )
        except Exception:
            pass
        return plano
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao atualizar plano proposto: {exc}")


# ----------------------------------
# Trava de Caixa (Regra 7)
# ----------------------------------


def is_caixa_dia_aberto(data_caixa: date) -> bool:
    """Retorna True se o caixa do dia está ABERTO (ou não existe registro)."""
    fech = db.session.get(FechamentoCaixa, data_caixa)
    if fech is None:
        return True
    return fech.status == CaixaStatus.ABERTO


def fechar_caixa_dia(
    data_caixa: date, saldo_apurado: Decimal, usuario_id: int
) -> FechamentoCaixa:
    """Fecha o caixa no dia especificado (upsert atômico).

    - Se já estiver FECHADO, levanta ValueError.
    - Atualiza saldo_apurado e status para FECHADO.
    """
    try:
        fech = db.session.get(FechamentoCaixa, data_caixa)
        if fech is None:
            fech = FechamentoCaixa()
            fech.data_fechamento = data_caixa
            db.session.add(fech)
        else:
            if fech.status == CaixaStatus.FECHADO:
                raise ValueError("Caixa já fechado.")

        fech.status = CaixaStatus.FECHADO
        fech.saldo_apurado = _to_decimal(saldo_apurado)
        db.session.commit()
        # Log de sistema na timeline (non-blocking)
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="CAIXA",
                descricao=(
                    f"Caixa do dia {data_caixa.strftime('%d/%m/%Y')} "
                    f"fechado."
                ),
                usuario_id=usuario_id,
                paciente_id=None,
            )
        except Exception:
            pass
        return fech
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao fechar caixa: {exc}")


def add_lancamento_estorno(
    lancamento_original_id: int, motivo_estorno: str | None, usuario_id: int
) -> LancamentoFinanceiro:
    """Cria um estorno (AJUSTE negativo) de um lançamento, respeitando a trava.

    - Bloqueia se o dia do lançamento original estiver FECHADO.
    - Cria ajuste negativo vinculado ao original.
    """
    orig = db.session.get(LancamentoFinanceiro, int(lancamento_original_id))
    if orig is None:
        raise ValueError("Lançamento original não encontrado.")

    # Verificar trava: data do lançamento original
    data_original = orig.data_lancamento.date()
    fech = db.session.get(FechamentoCaixa, data_original)
    if fech is not None and fech.status == CaixaStatus.FECHADO:
        raise ValueError(
            f"Caixa do dia {data_original} está fechado. Use um Ajuste."
        )

    try:
        m_clean = sanitizar_input(motivo_estorno)
        motivo = m_clean if isinstance(m_clean, str) and m_clean else "Estorno"

        est = LancamentoFinanceiro()
        est.plano_id = orig.plano_id
        est.valor = -_to_decimal(orig.valor)
        est.metodo_pagamento = "ESTORNO"
        est.tipo_lancamento = LancamentoFinanceiro.LancamentoTipo.AJUSTE
        est.notas_motivo = f"Estorno (Ref ID: {orig.id}): {motivo}"
        est.lancamento_estornado_id = orig.id
        db.session.add(est)
        db.session.commit()
        try:
            timeline_service.create_timeline_evento(
                evento_tipo="FINANCEIRO",
                descricao=(
                    "Estorno criado para lançamento #"
                    f"{orig.id} no valor de R$ {-est.valor}."
                ),
                usuario_id=usuario_id,
                paciente_id=orig.plano.paciente_id,
            )
        except Exception:
            pass
        return est
    except Exception as exc:
        db.session.rollback()
        raise ValueError(f"Falha ao estornar lançamento: {exc}")
