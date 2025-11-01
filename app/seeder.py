from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import db
from app.models import (
    Usuario,
    Paciente,
    Anamnese,
    Agendamento,
    Tenant,
    RoleEnum,
    AnamneseStatus,
    TemplateDocumento,
    TipoDocumento,
)


def seed_public() -> None:
    print("INFO: [seed_public] Iniciando seed no schema public...")
    try:
        # Desabilitar auditoria durante seed do schema public
        # (logs são específicos do tenant e não são necessários aqui)
        db.session.info["_audit_disabled"] = True
    # Opcional: garantir visibilidade ao tenant_default
    # caso haja acessos indiretos
        db.session.execute(
            text("SET SESSION search_path TO tenant_default, public")
        )
        tenant = Tenant(
            schema_name="tenant_default",
            display_name="Clínica Padrão",
            is_active=True,
        )
        db.session.add(tenant)
        db.session.commit()
        print("INFO: [seed_public] Tenant principal criado.")
    except Exception as e:
        db.session.rollback()
        print(f"ERRO: [seed_public] Falha: {e}")
        raise
    finally:
        # Reabilitar auditoria após concluir
        db.session.info.pop("_audit_disabled", None)


def seed_tenant_default() -> None:
    print("INFO: [seed_tenant_default] Iniciando seed no tenant_default...")
    try:
        # Garantir search_path para a sessão atual
        db.session.execute(
            text("SET SESSION search_path TO tenant_default, public")
        )

        # Usuário dentista
        dentista = Usuario(
            username="dentista_teste",
            role=RoleEnum.DENTISTA,
            nome_completo="Dr. Dentista Teste",
            is_active=True,
            password_hash=generate_password_hash("senha123"),
        )
        db.session.add(dentista)

        # Paciente
        paciente = Paciente(
            nome_completo="Paciente Teste",
            data_nascimento=date(1990, 1, 1),
            telefone="(11) 99999-0000",
            email="paciente@teste.com",
            apelido="Paciente Apelido Teste",
        )
        db.session.add(paciente)
        db.session.flush()  # IDs disponíveis sem fechar a transação

        # Anamnese do paciente
        anamnese = Anamnese(
            paciente_id=paciente.id,
            alergias="Nenhuma",
            medicamentos_uso_continuo="Não",
            historico_doencas="Nenhum",
            status=AnamneseStatus.CONCLUIDA,
            data_atualizacao=datetime.now(timezone.utc),
        )
        db.session.add(anamnese)

        # Agendamento de teste
        now = datetime.now(timezone.utc)
        agendamento = Agendamento(
            paciente_id=paciente.id,
            dentista_id=dentista.id,
            start_time=now + timedelta(days=1, hours=9),
            end_time=now + timedelta(days=1, hours=10),
        )
        db.session.add(agendamento)

        db.session.commit()

        # -----------------------------
        # Templates de documento padrão
        # -----------------------------
        # Criar somente se não existirem registros desse tipo
        existentes = db.session.query(TemplateDocumento).count()
        if existentes == 0:
            atestado = TemplateDocumento(
                nome="Atestado Simples",
                tipo_doc=TipoDocumento.ATESTADO,
                template_jinja=(
                    "Atesto que {{ paciente.nome_completo }} necessita de "
                    "{{ dias_repouso }} dias de repouso por motivos clínicos."
                ),
                is_active=True,
            )
            receita = TemplateDocumento(
                nome="Receita Simples",
                tipo_doc=TipoDocumento.RECEITA,
                template_jinja=(
                    "Uso interno:\n"
                    "1. {{ nome_remedio }}\n"
                    "   {{ posologia_remedio }}"
                ),
                is_active=True,
            )
            db.session.add(atestado)
            db.session.add(receita)
            db.session.commit()
            print(
                "INFO: [seed_tenant_default] "
                "Templates padrão de documentos criados."
            )
        else:
            print(
                "INFO: [seed_tenant_default] "
                f"{existentes} template(s) de documentos já existem, "
                "pulando criação."
            )
        print("INFO: [seed_tenant_default] Semeadura concluída com sucesso.")
    except Exception as e:
        db.session.rollback()
        print(f"ERRO: [seed_tenant_default] Falha: {e}")
        raise
