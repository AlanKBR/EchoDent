import pytest
from decimal import Decimal
from app.services import financeiro_service
from app.models import StatusPlanoEnum


def test_fluxo_financeiro_completo(client, app, monkeypatch):
    # 1. Login como Admin
    resp = client.get('/__dev/login_as/admin', follow_redirects=True)
    assert resp.status_code == 200
    
    # 2. Criar Paciente
    paciente_data = {
        'nome_completo': 'Paciente Teste',
        'cpf': '12345678901',
        'data_nascimento': '1990-01-01',
        'telefone': '11999999999',
        'email': 'teste@exemplo.com',
        'cep': '01001000',
        'logradouro': 'Rua Teste',
        'numero': '123',
        'bairro': 'Centro',
        'cidade': 'São Paulo',
        'estado': 'SP',
    }
    resp = client.post('/pacientes/novo', data=paciente_data, follow_redirects=True)
    assert resp.status_code == 200
    # Captura paciente_id (busca no DB)
    with app.app_context():
        from app.models import Paciente
        paciente = Paciente.query.filter_by(cpf='12345678901').first()
        assert paciente is not None
        paciente_id = paciente.id

    # 3. Criar Plano de Tratamento (PROPOSTO)
    # Mock Procedimento.query.get para retornar um procedimento fake
    class MockProcedimento:
        id = 999
        nome = 'Limpeza'
        valor = Decimal('100.00')
        is_active = True
    def fake_get(_):
        return MockProcedimento()
    with app.app_context():
        from app.models import Procedimento
        monkeypatch.setattr(Procedimento.query, 'get', fake_get)
    plano_data = {
        'procedimento_id': '999',
        'valor_cobrado': '100.00',
    }
    resp = client.post(f'/financeiro/novo_plano/{paciente_id}', data=plano_data, follow_redirects=True)
    assert resp.status_code in (200, 302)
    # Captura plano_id (busca no DB)
    with app.app_context():
        from app.models import PlanoTratamento
        plano = PlanoTratamento.query.filter_by(paciente_id=paciente_id).order_by(PlanoTratamento.id.desc()).first()
        assert plano is not None
        plano_id = plano.id
        assert plano.status == StatusPlanoEnum.PROPOSTO
        assert plano.valor_total == Decimal('100.00')

    # 4. Aprovar Plano
    resp = client.post(f'/financeiro/plano/{plano_id}/aprovar', follow_redirects=True)
    assert resp.status_code in (200, 302)
    with app.app_context():
        plano = PlanoTratamento.query.get(plano_id)
        assert plano.status == StatusPlanoEnum.APROVADO

    # 5. Adicionar Pagamento Parcial
    pagamento_data = {'valor': '60.00', 'metodo_pagamento': 'Pix'}
    resp = client.post(f'/financeiro/plano/{plano_id}/pagar', data=pagamento_data, follow_redirects=True)
    assert resp.status_code in (200, 302)
    with app.app_context():
        from app.models import LancamentoFinanceiro
        lanc = LancamentoFinanceiro.query.filter_by(plano_id=plano_id).first()
        assert lanc is not None
        assert lanc.valor_pago == Decimal('60.00')

    # 6. Verificar Saldo Final e Status de Pagamento
    with app.app_context():
        resultado = financeiro_service.get_saldo_plano_calculado(plano_id)
        assert resultado['saldo_devedor'] == Decimal('40.00')
        planos = financeiro_service.get_planos_by_paciente(paciente_id)
        plano_atualizado = [p for p in planos if p.id == plano_id][0]
        assert getattr(plano_atualizado, 'status_pagamento', None) == 'Parcial'
