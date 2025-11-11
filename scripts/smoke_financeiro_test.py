from app import create_app, db
from app.models import Paciente, Procedimento, RoleEnum, Usuario
from app.services.financeiro_service import (
    add_lancamento,
    approve_plano,
    create_plano,
    create_recibo_avulso,
    get_saldo_devedor_paciente,
)


def main() -> None:
    app = create_app()
    with app.app_context():
        # Create base data
        # Get or create a dentist user to avoid unique constraint issues
        u = db.session.query(Usuario).filter_by(username="dent_teste").first()
        if not u:
            u = Usuario()
            u.username = "dent_teste"
            u.password_hash = "x"
            u.role = RoleEnum.DENTISTA
            db.session.add(u)
            db.session.commit()
        dent_id = u.id

        p = Paciente()
        p.nome_completo = "Paciente Teste"
        db.session.add(p)
        proc = Procedimento()
        proc.nome = "Limpeza"
        proc.valor_padrao = 100
        db.session.add(proc)
        db.session.commit()

        # Create plan
        plano = create_plano(
            paciente_id=p.id,
            dentista_id=dent_id,
            itens_data=[{"procedimento_id": proc.id}],
        )
        print(
            "Plano criado:",
            plano.id,
            plano.status,
            plano.subtotal,
            plano.valor_total,
        )

        # Approve plan with discount 10
        plano = approve_plano(plano.id, desconto=10)
        print(
            "Plano aprovado:",
            plano.id,
            plano.status,
            plano.desconto,
            plano.valor_total,
        )

        # Add payment 50 and commit
        lanc = add_lancamento(plano.id, 50, "DINHEIRO")
        db.session.commit()
        print("Lançamento:", lanc.id, lanc.valor)

        saldo = get_saldo_devedor_paciente(p.id)
        print("Saldo devedor:", saldo)

        # Create recibo avulso (phantom plan + payment)
        plano_avulso = create_recibo_avulso(
            paciente_id=p.id,
            dentista_id=dent_id,
            valor=30,
            motivo_descricao="Venda de escova",
        )
        print(
            "Recibo avulso plano:",
            plano_avulso.id,
            plano_avulso.status,
            plano_avulso.valor_total,
        )

        saldo2 = get_saldo_devedor_paciente(p.id)
        print("Saldo devedor após avulso:", saldo2)


if __name__ == "__main__":
    main()
