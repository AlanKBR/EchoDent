

import pytest
import datetime
from unittest.mock import patch


def test_fechar_caixa_dia_log_timeline(db_session):
    from app.models import FechamentoCaixa
    d1 = datetime.date(2025, 10, 26)
    saldo = Decimal("123.45")
    usuario_id = 42
    with patch("app.services.timeline_service.create_timeline_evento") as mock_log:
        fech = fechar_caixa_dia(d1, saldo, usuario_id=usuario_id)
        assert isinstance(fech, FechamentoCaixa)
        mock_log.assert_called_once_with(
            evento_tipo="CAIXA",
            descricao=f"Caixa do dia {d1.strftime('%d/%m/%Y')} fechado.",
            usuario_id=usuario_id,
            paciente_id=None,
        )

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
    ItemPlano,
)
from app.services.financeiro_service import (
    create_plano,
    approve_plano,
    add_lancamento,
    create_recibo_avulso,
    get_saldo_devedor_paciente,
    add_lancamento_ajuste,
    get_saldo_plano_calculado,
    get_planos_by_paciente,
    gerar_parcelamento_previsto,
    get_carne_detalhado,
    update_plano_proposto,
    fechar_caixa_dia,
    add_lancamento_estorno,
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
        usuario_id=1,
    )

    # Assert: plano criado como PROPOSTO
    assert plano.status == StatusPlanoEnum.PROPOSTO
    assert Decimal(plano.subtotal) == Decimal("300.00")
    assert Decimal(plano.valor_total) == Decimal("300.00")

    # Act 2: aprovar com desconto
    plano_aprovado = approve_plano(
        plano_id=plano.id,
        desconto=Decimal("50.00"),
        usuario_id=1,
    )

    # Assert: status APROVADO e valor_total correto
    assert plano_aprovado.status == StatusPlanoEnum.APROVADO
    assert Decimal(plano_aprovado.valor_total) == Decimal("250.00")

    # Act 3: lançar pagamento parcial
    add_lancamento(
        plano_id=plano_aprovado.id,
        valor=Decimal("80.00"),
        metodo_pagamento="PIX",
        usuario_id=1,
    )

    # Assert: saldo = valor_total - pagamento_parcial
    saldo = get_saldo_devedor_paciente(paciente_id=paciente.id)
    assert saldo == Decimal("170.00")


def test_create_plano_denormaliza_nome_e_valor(db_session):
    # Arrange: seed with a procedimento de teste
    dentista = Usuario()
    dentista.username = f"dentista_{uuid4().hex[:8]}"
    dentista.password_hash = "hash"
    dentista.role = RoleEnum.DENTISTA
    db.session.add(dentista)

    paciente = Paciente()
    paciente.nome_completo = "Paciente Freeze"
    db.session.add(paciente)

    proc = Procedimento()
    proc.nome = "Restauração Teste"
    proc.valor_padrao = Decimal("150.00")
    db.session.add(proc)
    db.session.commit()

    # Act: criar plano sem informar valor_cobrado (usa valor_padrao)
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )

    # Assert: plano PROPOSTO e item com nome/valor congelados
    assert plano.status == StatusPlanoEnum.PROPOSTO
    items = (
        db.session.query(ItemPlano)
        .filter(ItemPlano.plano_id == plano.id)
        .all()
    )
    assert len(items) == 1
    item = items[0]
    assert item.procedimento_nome_historico == "Restauração Teste"
    assert Decimal(item.valor_cobrado) == Decimal("150.00")


def test_get_planos_by_paciente_injeta_status_pagamento(db_session):
    # Arrange
    dentista, paciente, procedimento = _seed_basics()

    # Plano 1: PROPOSTO (sem pagamentos) -> status_pagamento None
    plano1 = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("100.00"),
            }
        ],
        usuario_id=1,
    )

    # Plano 2: APROVADO sem pagamentos -> Pendente
    plano2 = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("200.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano2.id, Decimal("0.00"), usuario_id=1)

    # Plano 3: APROVADO com pagamento parcial -> Parcial
    plano3 = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("300.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano3.id, Decimal("0.00"), usuario_id=1)
    add_lancamento(plano3.id, Decimal("50.00"), "PIX", usuario_id=1)

    # Plano 4: APROVADO com pagamentos >= total -> Paga
    plano4 = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("120.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano4.id, Decimal("0.00"), usuario_id=1)
    add_lancamento(plano4.id, Decimal("120.00"), "DINHEIRO", usuario_id=1)

    # Act
    planos = get_planos_by_paciente(paciente.id)

    # Assert: find each and check injected attrs
    by_id = {p.id: p for p in planos}
    assert by_id[plano1.id].status.name == "PROPOSTO"
    assert getattr(by_id[plano1.id], "status_pagamento", None) is None

    assert by_id[plano2.id].status.name == "APROVADO"
    assert getattr(by_id[plano2.id], "status_pagamento") == "Pendente"

    assert by_id[plano3.id].status.name == "APROVADO"
    assert getattr(by_id[plano3.id], "status_pagamento") == "Parcial"

    assert by_id[plano4.id].status.name == "APROVADO"
    assert getattr(by_id[plano4.id], "status_pagamento") == "Paga"


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
        usuario_id=1,
    )

    # Sanity check
    assert plano.status == StatusPlanoEnum.PROPOSTO

    # Act + Assert: tentar lançar pagamento antes de aprovar deve falhar
    with pytest.raises(ValueError):
        add_lancamento(
            plano_id=plano.id,
            valor=Decimal("50.00"),
            metodo_pagamento="DINHEIRO",
            usuario_id=1,
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
        usuario_id=1,
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


def test_ajuste_happy_path(db_session):
    # Arrange: criar plano aprovado
    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("100.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)

    # Act: aplicar ajuste negativo de 20 com motivo válido
    lanc = add_lancamento_ajuste(
        plano_id=plano.id,
        valor=Decimal("-20.00"),
        notas_motivo="Desconto fidelidade",
        usuario_id=1,
    )

    # Assert: lançamento criado e saldo ajustado (Soma Burra v2)
    assert isinstance(lanc, LancamentoFinanceiro)
    res = get_saldo_plano_calculado(plano.id)
    # saldo = total + SUM(ajustes) - SUM(pagamentos)
    assert res["saldo_devedor"] == Decimal("80.00")


def test_ajuste_falha_motivo_invalido(db_session):
    # Arrange: plano aprovado
    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("50.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)

    # Act + Assert: motivo vazio deve falhar
    with pytest.raises(ValueError):
        add_lancamento_ajuste(
            plano_id=plano.id,
            valor=Decimal("10.00"),
            notas_motivo="  ",
            usuario_id=1,
        )


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
            usuario_id=1,
        )


def test_get_carne_detalhado_cenario1_todas_pendentes(db_session):
    # 3 parcelas de 100, total pago = 0 => todas Pendente
    from datetime import date

    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("300.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)
    gerar_parcelamento_previsto(plano.id, 3, date(2025, 1, 1), usuario_id=1)

    lista = get_carne_detalhado(plano.id)
    assert len(lista) == 3
    assert [x["status"] for x in lista] == ["Pendente", "Pendente", "Pendente"]


def test_get_carne_detalhado_cenario2_parcial_no_meio(db_session):
    # 3 parcelas de 100, total pago = 150 => Paga, Parcial, Pendente
    from datetime import date

    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("300.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)
    gerar_parcelamento_previsto(plano.id, 3, date(2025, 1, 1), usuario_id=1)
    add_lancamento(plano.id, Decimal("150.00"), "PIX", usuario_id=1)

    lista = get_carne_detalhado(plano.id)
    assert len(lista) == 3
    assert [x["status"] for x in lista] == ["Paga", "Parcial", "Pendente"]


def test_get_carne_detalhado_cenario3_todas_pagas(db_session):
    # 3 parcelas de 100, total pago = 300 => todas Paga
    from datetime import date

    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("300.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)
    gerar_parcelamento_previsto(plano.id, 3, date(2025, 1, 1), usuario_id=1)
    add_lancamento(plano.id, Decimal("300.00"), "DINHEIRO", usuario_id=1)

    lista = get_carne_detalhado(plano.id)
    assert len(lista) == 3
    assert [x["status"] for x in lista] == ["Paga", "Paga", "Paga"]


def test_update_plano_proposto_happy_path(db_session):
    # Cria plano PROPOSTO com um item e atualiza nome/valor
    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("100.00"),
            }
        ],
        usuario_id=1,
    )
    # Atualiza item
    item = (
        db.session.query(ItemPlano)
        .filter(ItemPlano.plano_id == plano.id)
        .one()
    )
    update_plano_proposto(
        plano_id=plano.id,
        items_data=[
            {
                "item_id": item.id,
                "nome": "Novo Nome",
                "valor": Decimal("150.00"),
            }
        ],
        usuario_id=1,
    )
    db.session.refresh(item)
    db.session.refresh(plano)
    assert item.procedimento_nome_historico == "Novo Nome"
    assert Decimal(item.valor_cobrado) == Decimal("150.00")
    assert Decimal(plano.valor_total) == Decimal("150.00")


def test_update_plano_proposto_bloqueia_aprovado(db_session):
    dentista, paciente, procedimento = _seed_basics()
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("100.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0"), usuario_id=1)
    item = (
        db.session.query(ItemPlano)
        .filter(ItemPlano.plano_id == plano.id)
        .one()
    )
    old_nome = item.procedimento_nome_historico
    old_valor = Decimal(item.valor_cobrado)
    with pytest.raises(ValueError):
        update_plano_proposto(
            plano_id=plano.id,
            items_data=[
                {
                    "item_id": item.id,
                    "nome": "Edit Bloqueado",
                    "valor": Decimal("130.00"),
                }
            ],
            usuario_id=1,
        )
    # Dados não devem ter mudado
    db.session.refresh(item)
    assert item.procedimento_nome_historico == old_nome
    assert Decimal(item.valor_cobrado) == old_valor


def test_trava_caixa_estorno_bloqueado_e_sucesso(db_session):
    pass
def test_is_caixa_dia_aberto(db_session):
    from app.services.financeiro_service import is_caixa_dia_aberto, fechar_caixa_dia
    from app.models import FechamentoCaixa, CaixaStatus
    from datetime import date
    d1 = date(2025, 12, 1)
    d2 = date(2025, 12, 2)
    # Nenhum registro: deve retornar True
    assert is_caixa_dia_aberto(d1) is True
    # Fechar caixa d1
    fechar_caixa_dia(d1, saldo_apurado=Decimal('0.00'), usuario_id=1)
    # Agora d1 deve retornar False (fechado)
    assert is_caixa_dia_aberto(d1) is False
    # d2 ainda sem registro: True
    assert is_caixa_dia_aberto(d2) is True
    # Criar registro ABERTO manualmente para d2
    fc = FechamentoCaixa()
    fc.data_fechamento = d2
    fc.status = CaixaStatus.ABERTO
    fc.saldo_apurado = 0
    from app import db
    db.session.add(fc)
    db.session.commit()
    assert is_caixa_dia_aberto(d2) is True
    # Fechar d2
    fechar_caixa_dia(d2, saldo_apurado=Decimal('0.00'), usuario_id=1)
    assert is_caixa_dia_aberto(d2) is False
    # Setup: criar dois lançamentos em dias distintos
    from datetime import datetime, date as _date

    dentista, paciente, procedimento = _seed_basics()

    # Plano Aprovado para criar lançamentos
    plano = create_plano(
        paciente_id=paciente.id,
        dentista_id=dentista.id,
        itens_data=[
            {
                "procedimento_id": procedimento.id,
                "valor_cobrado": Decimal("200.00"),
            }
        ],
        usuario_id=1,
    )
    approve_plano(plano.id, Decimal("0.00"), usuario_id=1)

    # Lançamento Dia 1
    l1 = add_lancamento(plano.id, Decimal("50.00"), "PIX", usuario_id=1)
    # Ajustar data para Dia 1
    d1 = _date(2025, 1, 10)
    l1.data_lancamento = datetime(d1.year, d1.month, d1.day, 9, 0, 0)
    db.session.add(l1)
    db.session.commit()

    # Fechar caixa do Dia 1 e tentar estorno (deve bloquear)
    fechar_caixa_dia(d1, Decimal("0.00"), usuario_id=1)
    import pytest

    with pytest.raises(ValueError):
        add_lancamento_estorno(l1.id, "Erro operador", usuario_id=1)

    # Lançamento Dia 2 (caixa aberto)
    l2 = add_lancamento(plano.id, Decimal("80.00"), "DINHEIRO", usuario_id=1)
    d2 = _date(2025, 1, 11)
    l2.data_lancamento = datetime(d2.year, d2.month, d2.day, 10, 0, 0)
    db.session.add(l2)
    db.session.commit()

    # Estornar com sucesso (Dia 2 aberto)
    est = add_lancamento_estorno(l2.id, "Cliente desistiu", usuario_id=1)
    assert isinstance(est, LancamentoFinanceiro)
    assert Decimal(est.valor) == Decimal("-80.00")
    assert est.lancamento_estornado_id == l2.id
