from decimal import Decimal

import pytest

from app import db
from app.models import (
    ItemPlano,
    LancamentoFinanceiro,
    Paciente,
    PlanoTratamento,
    Procedimento,
    RoleEnum,
    Usuario,
)
from app.services import (
    financeiro_service,
    odontograma_service,
    paciente_service,
)

# app_ctx fixture moved to tests/conftest.py


def test_service_sanitization_rule_paciente_nome_trim(app_ctx):
    """
    Valida [AGENTS §7] Sanitização nos services.
    Assume que 'flask dev-sync-db' JÁ FOI executado e o DB está disponível.
    """
    # 1) Arrange (Inputs com espaços e campos opcionais)
    form_data = {
        "nome_completo": "   Nome Sujo   ",
        "telefone": "  1199999-0000  ",
    }

    # 2) Act (service direto)
    novo = paciente_service.create_paciente(form_data=form_data, usuario_id=1)

    # 3) Assert (estado no DB)
    p = db.session.get(Paciente, novo.id)
    assert p is not None
    assert p.nome_completo == "Nome Sujo"  # trim aplicado
    assert p.telefone == "1199999-0000"  # trim aplicado


def _get_any_paciente_and_dentista_ids():
    pac = db.session.query(Paciente).first()
    dent = db.session.query(Usuario).filter(Usuario.role == "DENTISTA").first()
    assert pac is not None, "Seeder didn't create a Paciente."
    assert dent is not None, "Seeder didn't create a Usuario dentista."
    return pac.id, dent.id


def test_regra_precos_congelados(app_ctx):
    """[AGENTS §4] Preços Congelados

    - Cria Procedimento com valor_padrao=100.00
    - Cria plano com item baseado no Procedimento (congela valor)
    - Altera valor_padrao do Procedimento para 999.00
    - Garante que item.valor_cobrado permanece 100.00
    """
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Limpeza",
        valor_padrao=Decimal("100.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )

    # alterar preço mestre após criação (não deve afetar o item já criado)
    proc_db = db.session.get(Procedimento, proc.id)
    assert proc_db is not None
    proc_db.valor_padrao = Decimal("999.00")
    db.session.commit()

    # recarregar plano e item
    plano_db = db.session.get(PlanoTratamento, plano.id)
    assert plano_db is not None
    assert len(plano_db.itens) == 1
    item: ItemPlano = plano_db.itens[0]
    assert Decimal(str(item.valor_cobrado)) == Decimal("100.00")


def test_regra_plano_aprovado_selado(app_ctx):
    """[AGENTS §4] Plano APROVADO selado (não permite edição).

    - Cria plano PROPOSTO
    - Aprova plano
    - Tenta atualizar com update_plano_proposto (deve falhar)
    """
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Restauração",
        valor_padrao=Decimal("150.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    with pytest.raises(ValueError):
        financeiro_service.update_plano_proposto(
            plano_id=plano.id,
            items_data=[],
            usuario_id=1,
        )


def test_regra_trava_de_caixa_estorno(app_ctx):
    """[AGENTS §7] Trava de Caixa impede estorno em dia fechado.

    - Cria plano e aprova
    - Adiciona lançamento (pagamento)
    - Fecha o caixa na data do lançamento
    - Tenta estornar (deve falhar)
    """
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Profilaxia",
        valor_padrao=Decimal("80.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    lanc = financeiro_service.add_lancamento(
        plano_id=plano.id,
        valor=Decimal("50.00"),
        metodo_pagamento="DINHEIRO",
        usuario_id=1,
    )
    # Garantir data do lançamento via reload
    lanc_db = db.session.get(LancamentoFinanceiro, lanc.id)
    assert lanc_db is not None and lanc_db.data_lancamento is not None
    dia = lanc_db.data_lancamento.date()

    # Fechar o caixa do dia (idempotente para testes): ignorar segunda chamada
    try:
        financeiro_service.fechar_caixa_dia(
            data_caixa=dia,
            saldo_apurado=Decimal("0.00"),
            usuario_id=1,
        )
    except ValueError:
        pass

    with pytest.raises(ValueError):
        financeiro_service.add_lancamento_estorno(
            lancamento_original_id=lanc.id,
            motivo_estorno="Teste",
            usuario_id=1,
        )


def test_regra_soma_burra_saldo_dinamico(app_ctx):
    """[AGENTS §4] Soma Burra dinâmica

    - Plano 500, pagamento 100 => saldo 400
    - Ajuste +50 => saldo 450
    """
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Proced 500",
        valor_padrao=Decimal("500.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    financeiro_service.add_lancamento(
        plano_id=plano.id,
        valor=Decimal("100.00"),
        metodo_pagamento="PIX",
        usuario_id=1,
    )
    comp1 = financeiro_service.get_saldo_plano_calculado(plano.id)
    assert comp1["saldo_devedor"] == Decimal("400.00")

    financeiro_service.add_lancamento_ajuste(
        plano_id=plano.id,
        valor=Decimal("50.00"),
        notas_motivo="Taxa",
        usuario_id=1,
    )
    comp2 = financeiro_service.get_saldo_plano_calculado(plano.id)
    assert comp2["saldo_devedor"] == Decimal("450.00")


def test_regra_soma_burra_saldo_negativo_credito(app_ctx):
    """[AGENTS §4] Soma Burra com crédito (saldo negativo)."""
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Proced 100",
        valor_padrao=Decimal("100.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    financeiro_service.add_lancamento(
        plano_id=plano.id,
        valor=Decimal("150.00"),
        metodo_pagamento="CARTAO",
        usuario_id=1,
    )
    comp = financeiro_service.get_saldo_plano_calculado(plano.id)
    assert comp["saldo_devedor"] == Decimal("-50.00")


from app.models import LogAuditoria, TimelineEvento  # noqa: E402


def test_regra_timeline_double_write(app_ctx):
    """[AGENTS §7] Timeline recebe evento após ação de service.

    Medimos após criar o plano, para isolar o evento de aprovação (+1).
    """
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="P50",
        valor_padrao=Decimal("50.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    before = db.session.query(TimelineEvento).count()
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )
    after = db.session.query(TimelineEvento).count()
    assert after == before + 1


def test_regra_auditoria_evento_criacao(app_ctx):
    """[AGENTS §7] Auditoria registra criação de entidade."""
    before = db.session.query(LogAuditoria).count()

    form_data = {
        "nome_completo": "Paciente Audit",
        "telefone": "  1198888-7777  ",
    }
    novo = paciente_service.create_paciente(form_data=form_data, usuario_id=1)
    assert novo.id is not None

    after = db.session.query(LogAuditoria).count()
    # Pelo menos 1 log 'create' (pode haver mais dependendo de side-effects)
    assert after >= before + 1


def test_regra_odontograma_snapshot_admin_guard(app_ctx):
    """[AGENTS §3] Snapshot inicial imutável, sobrescrita apenas por ADMIN.

    Cenário:
    - Captura snapshot inicial sem sobrescrita (sucesso)
    - Nova captura sem force_overwrite (deve falhar)
    - Tentativa de sobrescrita com usuário NÃO-ADMIN (deve falhar)
    - Sobrescrita com ADMIN (sucesso)
    """
    # Arrange: obter paciente e dois usuários (um admin e um não-admin)
    pac = db.session.query(Paciente).first()
    assert pac is not None, "Seeder não criou Paciente."

    user_non_admin = (
        db.session.query(Usuario)
        .filter(Usuario.role.in_(["DENTISTA", "SECRETARIA"]))
        .first()
    )
    if user_non_admin is None:
        user_non_admin = Usuario(
            username="user_na",
            password_hash="x",
            role=RoleEnum.DENTISTA,
        )
        db.session.add(user_non_admin)
        db.session.commit()

    user_admin = (
        db.session.query(Usuario).filter(Usuario.role == "ADMIN").first()
    )
    if user_admin is None:
        user_admin = Usuario(
            username="user_admin",
            password_hash="x",
            role=RoleEnum.ADMIN,
        )
        db.session.add(user_admin)
        db.session.commit()

    # Act/Assert: primeira captura (sem overwrite) deve funcionar
    ok1 = odontograma_service.snapshot_odontograma_inicial(
        paciente_id=pac.id, usuario_id=user_non_admin.id, force_overwrite=False
    )
    assert ok1 is True

    # Segunda captura sem overwrite deve falhar
    with pytest.raises(ValueError):
        odontograma_service.snapshot_odontograma_inicial(
            paciente_id=pac.id,
            usuario_id=user_non_admin.id,
            force_overwrite=False,
        )

    # Tentativa de overwrite por não-admin deve falhar
    with pytest.raises(ValueError):
        odontograma_service.snapshot_odontograma_inicial(
            paciente_id=pac.id,
            usuario_id=user_non_admin.id,
            force_overwrite=True,
        )

    # Overwrite por ADMIN deve funcionar
    ok2 = odontograma_service.snapshot_odontograma_inicial(
        paciente_id=pac.id, usuario_id=user_admin.id, force_overwrite=True
    )
    assert ok2 is True


def test_regra_financeiro_ajuste_motivo_obrigatorio(app_ctx):
    """[AGENTS §4] Ajuste exige motivo obrigatório no service."""
    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Proc Ajuste",
        valor_padrao=Decimal("200.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    # Motivo None
    with pytest.raises(ValueError):
        financeiro_service.add_lancamento_ajuste(
            plano_id=plano.id,
            valor=Decimal("10.00"),
            notas_motivo=None,
            usuario_id=1,
        )

    # Motivo vazio/branco
    with pytest.raises(ValueError):
        financeiro_service.add_lancamento_ajuste(
            plano_id=plano.id,
            valor=Decimal("10.00"),
            notas_motivo="   ",
            usuario_id=1,
        )


def test_regra_parcelas_status_dinamico(app_ctx):
    """[AGENTS §4] Carnê: status dinâmico Paga/Parcial/Pendente por soma.

    - Plano 300, 3 parcelas de ~100
    - Pagamento 150 => [Paga, Parcial, Pendente]
    - Pagamento +150 => [Paga, Paga, Paga]
    """
    from datetime import date

    paciente_id, dentista_id = _get_any_paciente_and_dentista_ids()

    proc = Procedimento(
        nome="Proc 300",
        valor_padrao=Decimal("300.00"),
        is_active=True,
    )
    db.session.add(proc)
    db.session.commit()

    plano = financeiro_service.create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=[{"procedimento_id": proc.id}],
        usuario_id=1,
    )
    financeiro_service.approve_plano(
        plano_id=plano.id,
        desconto=0,
        usuario_id=1,
    )

    # Gera 3 parcelas a partir de hoje
    financeiro_service.gerar_parcelamento_previsto(
        plano_id=plano.id,
        num_parcelas=3,
        data_inicio=date.today(),
        usuario_id=1,
    )

    # Sem pagamentos ainda, tudo Pendente
    det0 = financeiro_service.get_carne_detalhado(plano.id)
    assert [d["status"] for d in det0] == ["Pendente", "Pendente", "Pendente"]

    # Pagamento 150 => [Paga, Parcial, Pendente]
    financeiro_service.add_lancamento(
        plano_id=plano.id,
        valor=Decimal("150.00"),
        metodo_pagamento="PIX",
        usuario_id=1,
    )
    det1 = financeiro_service.get_carne_detalhado(plano.id)
    assert [d["status"] for d in det1] == ["Paga", "Parcial", "Pendente"]

    # Pagamento +150 => tudo Paga
    financeiro_service.add_lancamento(
        plano_id=plano.id,
        valor=Decimal("150.00"),
        metodo_pagamento="PIX",
        usuario_id=1,
    )
    det2 = financeiro_service.get_carne_detalhado(plano.id)
    assert [d["status"] for d in det2] == ["Paga", "Paga", "Paga"]
