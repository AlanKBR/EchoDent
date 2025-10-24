from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app import db
from app.models import (
    Usuario,
    Paciente,
    Procedimento,
    PlanoTratamento,
    LancamentoFinanceiro,
    StatusPlanoEnum,
    RoleEnum,
)
from app.services.financeiro_service import (
    create_plano,
    approve_plano,
    add_lancamento,
    create_recibo_avulso,
    get_saldo_devedor_paciente,
)


def _seed_basics():
    """Create a Usuario (dentista), a Paciente, and a Procedimento.

    Returns a tuple: (dentista, paciente, procedimento)
    """
    dentista = Usuario()
    dentista.username = f"dentista_{uuid4().hex[:8]}"
    dentista.password_hash = "hash"
    dentista.role = RoleEnum.DENTISTA
    db.session.add(dentista)

    paciente = Paciente()
    paciente.nome_completo = "Paciente Teste"
    db.session.add(paciente)

    procedimento = Procedimento()
    procedimento.nome = "Limpeza"
    procedimento.valor_padrao = Decimal("200.00")
    db.session.add(procedimento)

    db.session.commit()
    return dentista, paciente, procedimento


def test_fluxo_de_ouro_completo(db_session):
    # Arrange
    dentista, paciente, procedimento = _seed_basics()

    # Act 1: criar plano com um item e valor controlado
    itens = [
        {
            "procedimento_id": procedimento.id,
            "valor_cobrado": Decimal("300.00"),
            "descricao_dente_face": None,
        }
    ]
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=itens,
    )

    # Assert: plano criado como PROPOSTO
    assert plano.status == StatusPlanoEnum.PROPOSTO
    assert Decimal(plano.subtotal) == Decimal("300.00")
    assert Decimal(plano.valor_total) == Decimal("300.00")

    # Act 2: aprovar com desconto
    plano_aprovado = approve_plano(
        plano_id=plano.id,
        desconto=Decimal("50.00"),
    )

    # Assert: status APROVADO e valor_total correto
    assert plano_aprovado.status == StatusPlanoEnum.APROVADO
    assert Decimal(plano_aprovado.valor_total) == Decimal("250.00")

    # Act 3: lançar pagamento parcial
    add_lancamento(
        plano_id=plano_aprovado.id,
        valor=Decimal("80.00"),
        metodo_pagamento="PIX",
    )

    # Assert: saldo = valor_total - pagamento_parcial
    saldo = get_saldo_devedor_paciente(paciente_id=paciente.id)
    assert saldo == Decimal("170.00")


def test_falha_pagamento_plano_proposto(db_session):
    # Arrange
    dentista, paciente, procedimento = _seed_basics()
    itens = [
        {
            "procedimento_id": procedimento.id,
            "valor_cobrado": Decimal("150.00"),
        }
    ]
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=itens,
    )

    # Sanity check
    assert plano.status == StatusPlanoEnum.PROPOSTO

    # Act + Assert: tentar lançar pagamento antes de aprovar deve falhar
    with pytest.raises(ValueError):
        add_lancamento(
            plano_id=plano.id,
            valor=Decimal("50.00"),
            metodo_pagamento="DINHEIRO",
        )


def test_recibo_avulso_gera_saldo_zero(db_session):
    # Arrange
    dentista, paciente, _ = _seed_basics()

    # Act: criar recibo avulso (plano concluído + pagamento igual)
    plano = create_recibo_avulso(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        valor=Decimal("120.00"),
        motivo_descricao="Venda escova",
    )

    # Assert: plano concluído com valor_total correto
    assert isinstance(plano, PlanoTratamento)
    assert plano.status == StatusPlanoEnum.CONCLUIDO
    assert Decimal(plano.valor_total) == Decimal("120.00")

    # Assert: foi criado lançamento financeiro para o mesmo plano e valor
    lanc = (
        db.session.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.plano_id == plano.id)
        .one()
    )
    assert Decimal(lanc.valor) == Decimal("120.00")
    assert lanc.metodo_pagamento == "AVULSO"

    # Assert: saldo do paciente permanece zero (operação autobalanceada)
    saldo = get_saldo_devedor_paciente(paciente_id=paciente.id)
    assert saldo == Decimal("0")


def test_falha_criar_plano_dentista_invalido(db_session):
    # Arrange: apenas paciente e procedimento válidos
    _, paciente, procedimento = _seed_basics()
    itens = [
        {
            "procedimento_id": procedimento.id,
            "valor_cobrado": Decimal("100.00"),
        }
    ]

    # Act + Assert: dentista inexistente deve falhar por validação cross-bind
    with pytest.raises(ValueError):
        create_plano(
            paciente_id=paciente.id,
            dentista_id=9999,
            itens_data=itens,
        )
