from __future__ import annotations

from decimal import Decimal

from app import db
from app.models import (
    Paciente,
    TimelineEvento,
    Usuario,
    Procedimento,
    RoleEnum,
)
from app.services.financeiro_service import create_plano


def _login_dev_admin(client):
    r = client.get("/__dev/login_as/admin")
    assert r.status_code in (200, 302)


def test_paciente_detalhe_is_shell_and_tabs_load_fragments(client, app):
    _login_dev_admin(client)

    # Create a patient and one timeline event
    with app.app_context():
        p = Paciente()
        p.nome_completo = "Paciente Historico"
        db.session.add(p)
        db.session.commit()

        ev = TimelineEvento()
        ev.paciente_id = p.id
        ev.usuario_id = None
        ev.evento_tipo = "CLINICO"
        ev.descricao = "Check-in realizado"
        db.session.add(ev)
        db.session.commit()
        pid = p.id

    # Request the detail page (shell)
    resp = client.get(f"/pacientes/{pid}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Shell should NOT contain the event text (loaded via tab)
    assert "Check-in realizado" not in html
    # It should contain the tab links and container
    assert "tab-content-container" in html

    # Load Histórico tab fragment
    r_hist = client.get(f"/pacientes/{pid}/tab/historico")
    assert r_hist.status_code == 200
    frag_hist = r_hist.get_data(as_text=True)
    assert "Check-in realizado" in frag_hist

    # Seed a plan to test Planejamento tab
    with app.app_context():
        dent = Usuario()
        dent.username = "dent_tab"
        dent.password_hash = "x"
        dent.role = RoleEnum.DENTISTA
        db.session.add(dent)

        proc = Procedimento()
        proc.nome = "Profilaxia Tab"
        proc.valor_padrao = Decimal("123.00")
        db.session.add(proc)
        db.session.commit()

        create_plano(
            paciente_id=pid,
            dentista_id=dent.id,
            itens_data=[
                {
                    "procedimento_id": proc.id,
                    "valor_cobrado": Decimal("123.00"),
                }
            ],
            usuario_id=1,
        )

    r_plan = client.get(f"/pacientes/{pid}/tab/planejamento")
    assert r_plan.status_code == 200
    frag_plan = r_plan.get_data(as_text=True)
    assert "Planejamento Financeiro" in frag_plan
    assert "Profilaxia Tab" in frag_plan
