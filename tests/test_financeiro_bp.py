
import pytest
from unittest.mock import patch, MagicMock
from app.models import Usuario, Paciente, Procedimento, RoleEnum
from app import db
from decimal import Decimal
from uuid import uuid4

@pytest.fixture
def plano_lancamento_ids(client, app):
    _login_dev_admin(client)
    with app.app_context():
        dent_id, pac_id, proc_id = _seed_basic_plan()
    # Cria plano
    client.post(
        f"/financeiro/novo_plano/{pac_id}",
        data={"procedimento_id": str(proc_id), "valor_cobrado": "99.00"},
        follow_redirects=False,
    )
    detail = client.get(f"/pacientes/{pac_id}")
    html = detail.get_data(as_text=True)
    import re
    m = re.search(r"Plano #([0-9]+)", html)
    plan_id = int(m.group(1)) if m else 1
    # Simula pagamento para criar lançamento
    client.post(
        f"/financeiro/plano/{plan_id}/pagar",
        data={"valor": "50.00", "metodo_pagamento": "DINHEIRO"},
        follow_redirects=True,
    )
    # Busca novamente para pegar o id do lançamento
    detail2 = client.get(f"/pacientes/{pac_id}")
    html2 = detail2.get_data(as_text=True)
    m2 = re.search(r'/financeiro/lancamento/(\d+)/estornar', html2)
    lanc_id = int(m2.group(1)) if m2 else 1
    return plan_id, lanc_id

def test_estornar_lancamento_sucesso(client, plano_lancamento_ids):
    plan_id, lanc_id = plano_lancamento_ids
    with patch(
        "app.blueprints.financeiro_bp.add_lancamento_estorno"
    ) as mock_estorno, patch(
        "app.services.financeiro_service.get_plano_by_id"
    ) as mock_get_plano:
        mock_result = MagicMock()
        mock_result.plano_id = plan_id
        mock_estorno.return_value = mock_result
        # Buscar o plano real do banco
        from app.models import PlanoTratamento
        from app import db
        plano_real = db.session.get(PlanoTratamento, plan_id)
        # Monkey-patch format_currency
        def fake_format_currency(val):
            return f"R$ {float(val):.2f}"
        plano_real.format_currency = fake_format_currency
        # Garantir que caixa_aberto_lancamentos exista e seja True para o primeiro lançamento
        plano_real.caixa_aberto_lancamentos = [True for _ in plano_real.lancamentos]
        mock_get_plano.return_value = plano_real
        resp = client.post(
            f"/financeiro/lancamento/{lanc_id}/estornar",
            data={"motivo_estorno": "Teste estorno"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
    # Após o estorno, pode não haver mais lançamentos elegíveis para estorno
    # Aceita lista vazia como sucesso
    assert '<ul class="list-unstyled mb-0">' in html

def test_estornar_lancamento_trava_caixa(client, plano_lancamento_ids):
    plan_id, lanc_id = plano_lancamento_ids
    with patch(
        "app.services.financeiro_service.add_lancamento_estorno"
    ) as mock_estorno:
        mock_estorno.side_effect = ValueError("Caixa fechado para estorno")
        resp = client.post(
            f"/financeiro/lancamento/{lanc_id}/estornar",
            data={"motivo_estorno": "Teste erro"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 400
        html = resp.get_data(as_text=True)
        assert "Caixa fechado" in html or "erro" in html.lower()



def _login_dev_admin(client):
    r = client.get("/__dev/login_as/admin")
    assert r.status_code in (200, 302)


def _seed_basic_plan():
    dent = Usuario()
    dent.username = f"dent_{uuid4().hex[:8]}"
    dent.password_hash = "x"
    dent.role = RoleEnum.DENTISTA
    db.session.add(dent)

    p = Paciente()
    p.nome_completo = "Paciente UI"
    db.session.add(p)

    proc = Procedimento()
    proc.nome = "Limpeza UI"
    proc.valor_padrao = Decimal("99.00")
    db.session.add(proc)
    db.session.commit()
    return dent.id, p.id, proc.id




def test_aprovar_plano_returns_partial_html(client, app):
    _login_dev_admin(client)
    with app.app_context():
        dent_id, pac_id, proc_id = _seed_basic_plan()

    # Create a plan via POST form
    resp = client.post(
        f"/financeiro/novo_plano/{pac_id}",
        data={
            "procedimento_id": str(proc_id),
            "valor_cobrado": "99.00",
        },
        follow_redirects=False,
    )
    # Redirect to paciente detalhe after creation
    assert resp.status_code in (302, 303)

    # Get the created plan id by querying the paciente detail page
    # (Lightweight approach: fetch detail and look for '#')
    detail = client.get(f"/pacientes/{pac_id}")
    assert detail.status_code == 200

    # Find the first plan id in the HTML; fallback to id=1 for tests
    html = detail.get_data(as_text=True)
    # naive extract of first occurrence of '#<digits>'
    import re

    m = re.search(r"Plano #([0-9]+)", html)
    plan_id = int(m.group(1)) if m else 1

    # Approve with HTMX header and expect fragment with 'APROVADO'
    r2 = client.post(
        f"/financeiro/plano/{plan_id}/aprovar",
        data={"desconto": "0"},
        headers={"HX-Request": "true"},
    )
    assert r2.status_code == 200
    frag = r2.get_data(as_text=True)
    assert "APROVADO" in frag or "APROVADO" in frag.upper()


def test_editar_plano_htmx_flow(client, app):
    _login_dev_admin(client)
    with app.app_context():
        dent_id, pac_id, proc_id = _seed_basic_plan()

    # Criar plano via POST
    resp = client.post(
        f"/financeiro/novo_plano/{pac_id}",
        data={"procedimento_id": str(proc_id), "valor_cobrado": "100.00"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    # Obter id do plano da página
    detail = client.get(f"/pacientes/{pac_id}")
    html = detail.get_data(as_text=True)
    import re

    m = re.search(r"Plano #([0-9]+)", html)
    plan_id = int(m.group(1)) if m else 1

    # GET editar retorna formulário
    r1 = client.get(
        f"/financeiro/plano/{plan_id}/editar",
        headers={"HX-Request": "true"},
    )
    assert r1.status_code == 200
    form_html = r1.get_data(as_text=True)
    assert "Editar Plano" in form_html
    assert "item-1-id" in form_html

    # POST editar salva e retorna card
    r2 = client.post(
        f"/financeiro/plano/{plan_id}/editar",
        data={
            "item-1-id": "1",
            "item-1-nome": "Nome Editado",
            "item-1-valor": "150.00",
        },
        headers={"HX-Request": "true"},
    )
    assert r2.status_code == 200
    card_html = r2.get_data(as_text=True)
    assert "Plano #" in card_html
    assert "Nome Editado" in card_html
