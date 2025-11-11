import importlib
import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import (
    Agendamento,
    Anamnese,
    AnamneseStatus,
    CalendarEvent,
    CategoriaEnum,
    ClinicaInfo,
    GlobalSetting,
    Paciente,
    Procedimento,
    RoleEnum,
    SexoEnum,
    TemplateDocumento,
    Tenant,
    TipoDocumento,
    UserPreferences,
    Usuario,
)
from app.services.timeline_service import create_timeline_evento


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

        # Criar tenant principal (idempotente)
        existing_tenant = Tenant.query.filter_by(
            schema_name="tenant_default"
        ).first()
        if not existing_tenant:
            tenant = Tenant()
            tenant.schema_name = "tenant_default"
            tenant.display_name = "Clínica Padrão"
            tenant.is_active = True
            db.session.add(tenant)

        # Criar configurações de tema default
        theme_settings = [
            ("THEME_PRIMARY_COLOR", "#0d6efd"),  # Bootstrap blue
            ("THEME_SECONDARY_COLOR", "#6c757d"),
            ("THEME_USE_SYSTEM_COLOR", "false"),
        ]
        for k, v in theme_settings:
            existing = GlobalSetting.query.filter_by(key=k).first()
            if not existing:
                setting = GlobalSetting()
                setting.key = k
                setting.value = v
                db.session.add(setting)

        db.session.commit()
        if existing_tenant:
            print("INFO: [seed_public] Tenant principal já existe.")
        else:
            print("INFO: [seed_public] Tenant principal criado.")
        print("INFO: [seed_public] Configurações de tema criadas.")
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

        # Usuários padrão (get_or_create): ADMIN, DENTISTA, SECRETARIA
        # SENHA PADRÃO PARA TODOS: "dev123" (desenvolvimento apenas!)
        def ensure_user(username: str, role: RoleEnum, nome: str) -> Usuario:
            existing = Usuario.query.filter_by(username=username).first()
            if existing:
                return existing
            u = Usuario()
            u.username = username
            u.role = role
            u.nome_completo = nome
            u.is_active = True
            u.password_hash = generate_password_hash("dev123")  # DEV ONLY!
            # Dados extras para dentista
            if role == RoleEnum.DENTISTA:
                u.cro_registro = "CRO-TESTE-0001"
                u.color = "#0d6efd"
            db.session.add(u)
            db.session.flush()
            return u

        admin = ensure_user("admin", RoleEnum.ADMIN, "Dev Admin")
        dentista = ensure_user(
            "dentista", RoleEnum.DENTISTA, "Dr. Dev Dentista"
        )
        # Dentistas adicionais para diversidade de seed
        dentista2 = ensure_user(
            "dentista2", RoleEnum.DENTISTA, "Dra. Dev Endo"
        )
        dentista3 = ensure_user("dentista3", RoleEnum.DENTISTA, "Dr. Dev Orto")
        # Ajustar cores para diferenciar visualmente na agenda
        try:
            if dentista.color == "#0d6efd":
                dentista2.color = "#16a34a"  # verde
                dentista3.color = "#dc2626"  # vermelho
        except Exception:
            pass
        secretaria = ensure_user(
            "secretaria", RoleEnum.SECRETARIA, "Dev Secretária"
        )

        print("INFO: [seed_tenant_default] Usuários criados:")
        print("  - ADMIN: username='admin', password='dev123'")
        print("  - DENTISTA: username='dentista', password='dev123'")
        print("  - SECRETARIA: username='secretaria', password='dev123'")

        # Marcar variáveis como usadas (para linter)
        _ = (admin, secretaria)

        # ClinicaInfo (singleton)
        clinica_info = ClinicaInfo.query.first()
        if not clinica_info:
            clinica_info = ClinicaInfo()
            clinica_info.id = 1
            clinica_info.nome_clinica = "Clínica OdontoTeste"
            clinica_info.cnpj = "00.000.000/0000-00"
            clinica_info.cro_clinica = "CRO-XX-00000"
            clinica_info.telefone = "(11) 3000-0000"
            clinica_info.email = "contato@odontoteste.com.br"
            clinica_info.cep = "01000-000"
            clinica_info.logradouro = "Rua Exemplo"
            clinica_info.numero = "123"
            clinica_info.bairro = "Centro"
            clinica_info.cidade = "São Paulo"
            clinica_info.estado = "SP"
            clinica_info.horario_funcionamento = {
                "seg": "08:00-18:00",
                "ter": "08:00-18:00",
                "qua": "08:00-18:00",
                "qui": "08:00-18:00",
                "sex": "08:00-17:00",
                "sab": None,
                "dom": None,
            }
            db.session.add(clinica_info)
            db.session.flush()
            print("INFO: [seed_tenant_default] ClinicaInfo criada.")
        else:
            print(
                "INFO: [seed_tenant_default] "
                "ClinicaInfo já existe, pulando criação."
            )

        # UserPreferences para cada usuário
        for user in Usuario.query.all():
            prefs = UserPreferences.query.filter_by(usuario_id=user.id).first()
            if not prefs:
                prefs = UserPreferences()
                prefs.usuario_id = user.id
                prefs.notificacoes_enabled = True
                db.session.add(prefs)
            # Preencher defaults úteis para a lista de pacientes (se ausente)
            if not prefs.paciente_lista_colunas:
                prefs.paciente_lista_colunas = {
                    "telefone": True,
                    "email": True,
                    "idade": False,
                    "sexo": False,
                    "data_ultimo_registro": True,
                    "status_anamnese": True,
                    "cpf": False,
                    "cidade": False,
                }
        db.session.flush()
        print("INFO: [seed_tenant_default] UserPreferences criadas.")

        # Paciente principal
        paciente = Paciente()
        paciente.nome_completo = "Paciente Teste"
        paciente.data_nascimento = date(1990, 1, 1)
        paciente.telefone = "(11) 99999-0000"
        paciente.email = "paciente@teste.com"
        paciente.apelido = "Paciente Apelido Teste"
        paciente.sexo = SexoEnum.MASCULINO
        db.session.add(paciente)
        db.session.flush()  # IDs disponíveis sem fechar a transação

        # Segundo paciente para variações de agenda
        paciente2 = Paciente()
        paciente2.nome_completo = "Paciente Orto"
        paciente2.data_nascimento = date(2005, 6, 15)
        paciente2.telefone = "(11) 98888-1111"
        paciente2.email = "paciente2@teste.com"
        paciente2.apelido = "Orto"
        paciente2.sexo = SexoEnum.FEMININO
        db.session.add(paciente2)
        db.session.flush()

        # Anamnese do paciente
        anamnese = Anamnese()
        anamnese.paciente_id = paciente.id
        anamnese.alergias = "Nenhuma"
        anamnese.medicamentos_uso_continuo = "Não"
        anamnese.historico_doencas = "Nenhum"
        anamnese.status = AnamneseStatus.CONCLUIDA
        anamnese.data_atualizacao = datetime.now(timezone.utc)
        db.session.add(anamnese)

        anamnese2 = Anamnese()
        anamnese2.paciente_id = paciente2.id
        anamnese2.alergias = "Pólen"
        anamnese2.medicamentos_uso_continuo = "Antialérgico"
        anamnese2.historico_doencas = "Rinite"
        anamnese2.status = AnamneseStatus.CONCLUIDA
        anamnese2.data_atualizacao = datetime.now(timezone.utc)
        db.session.add(anamnese2)

        # Agendamento de teste
        now = datetime.now(timezone.utc)
        agendamento = Agendamento()
        agendamento.paciente_id = paciente.id
        agendamento.dentista_id = dentista.id
        agendamento.start_time = now + timedelta(days=1, hours=9)
        agendamento.end_time = now + timedelta(days=1, hours=10)
        db.session.add(agendamento)

        db.session.commit()

        # Denormalização inicial: registrar um evento na timeline
        # para o paciente. Isso preenche ultima_interacao_at e
        # ultima_interacao_desc (evento "PAGAMENTO" de exemplo).
        create_timeline_evento(
            evento_tipo="PAGAMENTO",
            descricao="Pagamento de teste registrado no seed",
            usuario_id=secretaria.id if secretaria else None,
            paciente_id=paciente.id,
        )
        create_timeline_evento(
            evento_tipo="ANAMNESE",
            descricao="Anamnese inicial preenchida (Paciente Orto)",
            usuario_id=secretaria.id if secretaria else None,
            paciente_id=paciente2.id,
        )

        # -------------------------------------------------
        # CalendarEvent (Agenda) — Seed Dinâmico (§9.1 UTC)
        # -------------------------------------------------
        # Idempotência simples: limpar eventos anteriores
        try:
            CalendarEvent.query.delete()
            db.session.flush()
        except Exception as purge_err:
            print(
                "WARN: Falha ao limpar CalendarEvent existentes: "
                f"{purge_err}"
            )

        # Gerar eventos relativos à data atual em UTC, cobrindo:
        # - Semana atual (curtos, sobrepostos, variados)
        # - Mês passado (histórico)
        # - Próximo mês (planejamento)
        # - Futuro distante (6 meses) e passado distante (90 dias)
        # Tipos: timed, all_day, multiday, cross-midnight, sem cor,
        # com/sem notas, com/sem dentista, eventos ligados a dois pacientes.
        now_utc = datetime.now(timezone.utc)
        today_midnight = now_utc.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        def dt_at(day_offset: int, hour: int, minute: int = 0) -> datetime:
            base = today_midnight + timedelta(days=day_offset)
            return base.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

        def add_event(
            title: str,
            start_dt: datetime,
            end_dt: datetime | None = None,
            all_day: bool = False,
            dent: Usuario | None = None,
            pac: Paciente | None = None,
            notes: str | None = None,
            color: str | None = None,
        ) -> None:
            ev = CalendarEvent()
            ev.title = title
            ev.start = start_dt  # timezone-aware (UTC)
            ev.end = end_dt
            ev.all_day = all_day
            ev.dentista_id = dent.id if dent else None
            ev.paciente_id = pac.id if pac else None
            ev.notes = notes
            ev.color = color
            db.session.add(ev)

        # Paleta de cores para eventos (variações realistas)
        palette = {
            "azul": "#2563eb",  # Consultas normais
            "verde": "#16a34a",  # Retornos/Follow-ups
            "vermelho": "#dc2626",  # Urgências
            "roxo": "#9333ea",  # Procedimentos especiais
            "laranja": "#ea580c",  # Avaliações
            "amarelo": "#fbbf24",  # Bloqueios/Administrativo
            "cinza": "#64748b",  # Eventos genéricos
            "rosa": "#ec4899",  # Ortodontia
            "ciano": "#0891b2",  # Implantes
            "indigo": "#4f46e5",  # Endodontia
        }
        d_list = [dentista, dentista2, dentista3]

        # ========================================
        # SEMANA ATUAL - Eventos Variados
        # ========================================

        # HOJE - Manhã
        add_event(
            "Maria Silva",
            dt_at(0, 8),
            dt_at(0, 9),
            False,
            d_list[0],
            paciente,
            (
                "Limpeza (Profilaxia + Aplicação de Flúor)\n"
                "Tel: (11) 98765-4321\n"
                "Paciente pontual, histórico de boa higiene."
            ),
            palette["verde"],
        )

        add_event(
            "João Santos",
            dt_at(0, 9, 30),
            dt_at(0, 11),
            False,
            d_list[0],
            paciente2,
            (
                "Restauração D47 (MOD)\n"
                "Resina composta\n"
                "Material: Filtek Z350\n"
                "Anestesia tópica + lidocaína 2%"
            ),
            palette["azul"],
        )

        # Evento urgente sobrepondo horário
        add_event(
            "🚨 Ana Costa (URGÊNCIA)",
            dt_at(0, 10),
            dt_at(0, 10, 30),
            False,
            d_list[2],
            None,
            (
                "Dor aguda dente 36\n"
                "Tel: (11) 99123-4567\n"
                "Paciente sem agendamento\n"
                "Avaliar pulpite"
            ),
            palette["vermelho"],
        )

        add_event(
            "Carlos Mendes",
            dt_at(0, 11, 30),
            dt_at(0, 12),
            False,
            d_list[1],
            paciente,
            (
                "Manutenção Ortodôntica (6º mês)\n"
                "Trocar elásticos\n"
                "Avaliar espaçamento D12-D11"
            ),
            palette["rosa"],
        )

        # HOJE - Tarde
        add_event(
            "Bloqueio Almoço",
            dt_at(0, 12),
            dt_at(0, 13, 30),
            False,
            None,
            None,
            None,
            palette["amarelo"],
        )

        add_event(
            "Fernanda Lima",
            dt_at(0, 14),
            dt_at(0, 15),
            False,
            d_list[0],
            None,
            (
                "1ª Consulta - Anamnese completa\n"
                "Queixa: Sensibilidade ao frio\n"
                "Tel: (11) 97654-3210\n"
                "Indicação: Dr. Roberto (ortopedista)"
            ),
            palette["laranja"],
        )

        add_event(
            "Roberto Alves",
            dt_at(0, 15, 30),
            dt_at(0, 17, 30),
            False,
            d_list[2],
            paciente2,
            (
                "Endodontia D26 (2ª sessão)\n"
                "Tratamento de canal - Dente 26 (2 canais)\n"
                "Curativo CTZ\n"
                "RX periapical tirado"
            ),
            palette["indigo"],
        )

        add_event(
            "Reunião Equipe",
            dt_at(0, 18),
            dt_at(0, 19),
            False,
            None,
            None,
            (
                "Discussão de casos complexos\n"
                "Revisar protocolos de biossegurança"
            ),
            palette["cinza"],
        )

        # ========================================
        # ONTEM - Histórico
        # ========================================
        add_event(
            "Patricia Souza",
            dt_at(-1, 9),
            dt_at(-1, 9, 30),
            False,
            d_list[1],
            paciente,
            (
                "Retorno - Remoção de pontos\n"
                "D18 (extração há 7 dias)\n"
                "Cicatrização normal\n"
                "Alta do procedimento"
            ),
            palette["verde"],
        )

        add_event(
            "Ricardo Nunes",
            dt_at(-1, 10),
            dt_at(-1, 11, 30),
            False,
            d_list[2],
            None,
            (
                "Consulta para Implante D36\n"
                "Avaliação inicial\n"
                "Tomografia solicitada\n"
                "Orçamento: R$ 3.200,00\n"
                "Tel: (11) 96543-2109"
            ),
            palette["ciano"],
        )

        add_event(
            "Juliana Ferreira",
            dt_at(-1, 14),
            dt_at(-1, 15),
            False,
            d_list[0],
            paciente2,
            (
                "Clareamento Caseiro\n"
                "Moldagem realizada\n"
                "Peróxido de carbamida 16%\n"
                "Entrega de moldeiras: +7 dias"
            ),
            palette["azul"],
        )

        # ========================================
        # AMANHÃ - Planejamento
        # ========================================
        add_event(
            "Bruno Campos",
            dt_at(1, 8, 30),
            dt_at(1, 9, 30),
            False,
            d_list[2],
            None,
            (
                "Avaliação Cirúrgica\n"
                "Extração D38 incluso\n"
                "RX panorâmica disponível\n"
                "Jejum de 8h\n"
                "Tel: (11) 95432-1098"
            ),
            palette["vermelho"],
        )

        add_event(
            "Camila Rocha",
            dt_at(1, 10),
            dt_at(1, 11),
            False,
            d_list[0],
            paciente,
            (
                "Manutenção Preventiva\n"
                "Limpeza semestral\n"
                "Aplicação selante (molares)\n"
                "Orientação higiene bucal"
            ),
            palette["verde"],
        )

        add_event(
            "Diego Martins",
            dt_at(1, 14),
            dt_at(1, 15, 30),
            False,
            d_list[1],
            paciente2,
            (
                "Prótese - Prova de PPR superior\n"
                "Ajustes de retenção\n"
                "Laboratório: Dental Plus\n"
                "Previsão entrega final: +10 dias"
            ),
            palette["roxo"],
        )

        add_event(
            "🚨 Horário Reserva",
            dt_at(1, 16),
            dt_at(1, 17),
            False,
            d_list[2],
            None,
            "Encaixe para emergências eventuais",
            palette["vermelho"],
        )

        # ========================================
        # EVENTOS ALL-DAY
        # ========================================
        add_event(
            "📅 Aniversário Clínica",
            today_midnight,
            None,
            True,
            None,
            None,
            "12 anos de atendimento odontológico de excelência!",
            palette["rosa"],
        )

        # Feriado semana que vem
        add_event(
            "🏖️ Feriado - Proclamação da República",
            dt_at(8, 0),
            None,
            True,
            None,
            None,
            "Clínica fechada",
            palette["amarelo"],
        )

        # ========================================
        # EVENTOS MULTI-DIA
        # ========================================
        # Congresso daqui 2 dias (3 dias de duração)
        congress_start = today_midnight + timedelta(days=2)
        congress_end = congress_start + timedelta(days=3)
        add_event(
            "🎓 Congresso APCD - São Paulo",
            congress_start,
            congress_end,
            True,
            d_list[1],
            None,
            (
                "32º Congresso Internacional de Odontologia\n"
                "Local: Expo Center Norte\n"
                "Temas: Implantodontia e Estética\n"
                "Dr. Dev Dentista participando"
            ),
            palette["indigo"],
        )

        # Retiro clínico semana que vem (2 dias)
        retiro_start = today_midnight + timedelta(days=5)
        retiro_end = retiro_start + timedelta(days=2)
        add_event(
            "🏕️ Retiro de Planejamento",
            retiro_start,
            retiro_end,
            True,
            None,
            None,
            (
                "Planejamento estratégico 2026\n"
                "Equipe completa\n"
                "Local: Hotel Fazenda Vale Verde"
            ),
            palette["verde"],
        )

        # ========================================
        # CROSS-MIDNIGHT (Procedimento noturno)
        # ========================================
        cross_start = dt_at(3, 21)
        cross_end = dt_at(4, 1, 30)
        add_event(
            "Larissa Gomes",
            cross_start,
            cross_end,
            False,
            d_list[0],
            None,
            (
                "Sedação Consciente\n"
                "Extração múltipla com sedação\n"
                "Dentes: 18, 28, 38, 48 (sisos)\n"
                "Anestesista: Dr. Paulo Mendes\n"
                "Tel emergência: (11) 94321-0987\n"
                "Pós-op: Amoxicilina 500mg + Ibuprofeno"
            ),
            palette["roxo"],
        )

        # ========================================
        # SEMANA PASSADA - Histórico
        # ========================================
        add_event(
            "Eduardo Silva",
            dt_at(-3, 10),
            dt_at(-3, 10, 30),
            False,
            d_list[1],
            paciente,
            (
                "Controle Pós-Operatório\n"
                "Controle após implante D46 (instalado há 15 dias)\n"
                "Sem sinais de infecção\n"
                "Próximo retorno: +3 meses"
            ),
            palette["verde"],
        )

        add_event(
            "Beatriz Andrade",
            dt_at(-5, 14),
            dt_at(-5, 15, 30),
            False,
            d_list[1],
            None,
            (
                "Documentação Ortodôntica\n"
                "Documentação ortodôntica completa\n"
                "Telerradiografia\n"
                "Fotos intra/extra orais\n"
                "Moldagem para estudo\n"
                "Tel: (11) 93210-9876"
            ),
            palette["rosa"],
        )

        # Evento sem dentista e sem notas (administrativo)
        add_event(
            "Manutenção Ar Condicionado",
            dt_at(-2, 13),
            dt_at(-2, 14),
            False,
            None,
            None,
            None,
            palette["cinza"],
        )

        # ========================================
        # PRÓXIMA SEMANA - Diversos horários
        # ========================================
        add_event(
            "Gabriel Torres",
            dt_at(7, 9),
            dt_at(7, 10),
            False,
            d_list[0],
            paciente2,
            (
                "1ª Sessão Clareamento\n"
                "Clareamento em consultório\n"
                "Peróxido hidrogênio 35%\n"
                "3 sessões programadas\n"
                "Orientar sensibilidade pós"
            ),
            palette["azul"],
        )

        add_event(
            "Amanda Reis",
            dt_at(9, 8),
            dt_at(9, 10, 30),
            False,
            d_list[2],
            None,
            (
                "Cirurgia Gengival\n"
                "Gengivoplastia região anterior superior\n"
                "Laser de diodo\n"
                "Pós-op: Dexametasona + Dipirona\n"
                "Tel: (11) 92109-8765"
            ),
            palette["roxo"],
        )

        # Evento curto (15 min) - consulta express
        add_event(
            "Lucas Pereira",
            dt_at(4, 11, 30),
            dt_at(4, 11, 45),
            False,
            d_list[1],
            paciente,
            (
                "Receita Rápida\n"
                "Renovar receita Periostat\n"
                "Doença periodontal controlada"
            ),
            palette["verde"],
        )

        # Consulta sem cor (teste UI default)
        add_event(
            "Mariana Oliveira",
            dt_at(6, 15),
            dt_at(6, 16),
            False,
            d_list[0],
            None,
            (
                "Orçamento\n"
                "Apresentar plano de tratamento completo\n"
                "Prótese + Implantes\n"
                "Valor total: R$ 18.500,00\n"
                "Tel: (11) 91098-7654"
            ),
            None,  # Sem cor
        )

        # Mês passado
        last_month_first = (
            today_midnight.replace(day=1) - timedelta(days=1)
        ).replace(day=1)
        last_month_event_day = last_month_first + timedelta(days=10)
        add_event(
            "Caso Revisão (Histórico)",
            last_month_event_day.replace(hour=15, minute=0),
            last_month_event_day.replace(hour=16, minute=30),
            False,
            d_list[2],
            paciente,
            "Registro para testar histórico.",
            "#0ea5e9",
        )
        # All-day mês passado
        last_month_allday = last_month_first + timedelta(days=15)
        add_event(
            "Feriado Local (All-Day)",
            last_month_allday,
            None,
            True,
            None,
            None,
            "Feriado municipal.",
            "#fbbf24",
        )

        # Próximo mês
        next_month_first = (
            today_midnight.replace(day=1) + timedelta(days=32)
        ).replace(day=1)
        next_month_event_day = next_month_first + timedelta(days=3)
        add_event(
            "Planejamento Orto",
            next_month_event_day.replace(hour=10),
            next_month_event_day.replace(hour=11),
            False,
            d_list[2],
            paciente,
            "Início da fase 2.",
            "#a21caf",
        )
        three_weeks_future = today_midnight + timedelta(weeks=3, hours=8)
        add_event(
            "Sessão Clareamento",
            three_weeks_future,
            three_weeks_future + timedelta(hours=1),
            False,
            d_list[0],
            paciente,
            "Etapa 1 do clareamento.",
            "#f472b6",
        )
        # Futuro distante (6 meses) sem dentista definido ainda
        distant_future = today_midnight + timedelta(days=180, hours=9)
        add_event(
            "Campanha Preventiva",
            distant_future,
            distant_future + timedelta(hours=2),
            False,
            None,
            None,
            "Planejar ações de prevenção e marketing.",
            "#3b82f6",
        )
        # Passado distante (90 dias atrás)
        distant_past = today_midnight - timedelta(days=90, hours=14)
        add_event(
            "Auditoria Interna",
            distant_past,
            distant_past + timedelta(hours=3),
            False,
            d_list[2],
            None,
            "Revisão de protocolos clínicos.",
            "#6b7280",
        )

        # Commit dedicado aos eventos (atomicidade §7.5)
        try:
            db.session.commit()
            print(
                "INFO: [seed_tenant_default] "
                "CalendarEvent dinamicos criados."
            )
        except Exception as ce_err:
            db.session.rollback()
            print(
                "ERRO: [seed_tenant_default] "
                f"Falha ao criar CalendarEvent: {ce_err}"
            )
            raise

        # -----------------------------------------------
        # Catálogo de Procedimentos (Tratamentos) (§2 / §4)
        # -----------------------------------------------
        # Regras:
        #  - Apenas cria se não houver procedimentos ainda
        #    (idempotência simples)
        #  - Usa CategoriaEnum para garantir integridade
        #  - Valores ilustrativos (DEV) — podem ser ajustados em produção
        #  - Soft-delete padrão (is_active=True) aplicado automaticamente
        #  - Auditoria automática via events.py (não desativamos aqui)
        existing_proc = db.session.query(Procedimento).count()
        if existing_proc == 0:
            print(
                "INFO: [seed_tenant_default] Criando catálogo de "
                "procedimentos..."
            )
            procedimentos_catalogo = [
                # Clínica Geral
                (
                    "Profilaxia (Limpeza)",
                    CategoriaEnum.CLINICA_GERAL,
                    180.00,
                    "Profilaxia + remoção de biofilme e polimento.",
                ),
                (
                    "Raspagem Supra-Gengival",
                    CategoriaEnum.CLINICA_GERAL,
                    150.00,
                    "Remoção de cálculo e placa supra-gengival.",
                ),
                (
                    "Aplicação de Flúor",
                    CategoriaEnum.CLINICA_GERAL,
                    80.00,
                    "Aplicação tópica de flúor gel ou verniz.",
                ),
                (
                    "Selante de Fissuras (por dente)",
                    CategoriaEnum.CLINICA_GERAL,
                    90.00,
                    "Selamento preventivo de sulcos e fissuras.",
                ),
                (
                    "Restauração Resina (Unitária)",
                    CategoriaEnum.CLINICA_GERAL,
                    250.00,
                    "Restauração direta em resina composta.",
                ),
                (
                    "Restauração Provisória",
                    CategoriaEnum.CLINICA_GERAL,
                    120.00,
                    "Proteção temporária de cavidade.",
                ),
                (
                    "Remoção de Tártaro Ultrassônica",
                    CategoriaEnum.CLINICA_GERAL,
                    200.00,
                    "Profilaxia com ultrassom + jato de bicarbonato.",
                ),
                # Ortodontia
                (
                    "Avaliação Ortodôntica",
                    CategoriaEnum.ORTODONTIA,
                    250.00,
                    "Consulta + plano preliminar.",
                ),
                (
                    "Documentação Ortodôntica",
                    CategoriaEnum.ORTODONTIA,
                    950.00,
                    "Fotos, moldes, radiografias e análise.",
                ),
                (
                    "Instalação Aparelho Fixo (Arcada)",
                    CategoriaEnum.ORTODONTIA,
                    2800.00,
                    "Colagem de bráquetes metálicos arcada completa.",
                ),
                (
                    "Manutenção Ortodôntica Mensal",
                    CategoriaEnum.ORTODONTIA,
                    180.00,
                    "Ajustes, troca de ligaduras/elásticos.",
                ),
                (
                    "Instalação Aparelho Autoligado",
                    CategoriaEnum.ORTODONTIA,
                    4200.00,
                    "Bráquetes autoligados alta performance.",
                ),
                (
                    "Contenção Fixa",
                    CategoriaEnum.ORTODONTIA,
                    600.00,
                    "Instalação de contenção pós-tratamento.",
                ),
                (
                    "Ajuste Contenção",
                    CategoriaEnum.ORTODONTIA,
                    180.00,
                    "Pequenos reparos ou ajustes em contenção.",
                ),
                (
                    "Planejamento Alinhadores",
                    CategoriaEnum.ORTODONTIA,
                    1500.00,
                    "Setup digital e plano de fases.",
                ),
                (
                    "Alinhadores - Fase Mensal",
                    CategoriaEnum.ORTODONTIA,
                    900.00,
                    "Entrega e controle de fases de alinhadores.",
                ),
                # Endodontia
                (
                    "Tratamento de Canal Unirradicular",
                    CategoriaEnum.ENDODONTIA,
                    900.00,
                    "Endodontia em dente unirradicular.",
                ),
                (
                    "Tratamento de Canal Birradicular",
                    CategoriaEnum.ENDODONTIA,
                    1200.00,
                    "Endodontia em dente birradicular.",
                ),
                (
                    "Tratamento de Canal Molar",
                    CategoriaEnum.ENDODONTIA,
                    1600.00,
                    "Endodontia em molar multirradicular.",
                ),
                (
                    "Retratamento Canal Unirradicular",
                    CategoriaEnum.ENDODONTIA,
                    1100.00,
                    "Retratamento endodôntico.",
                ),
                (
                    "Curativo Intracanal",
                    CategoriaEnum.ENDODONTIA,
                    250.00,
                    "Aplicação de medicação intracanal.",
                ),
                # Periodontia
                (
                    "Raspagem/Ali. Radicular Quadrante",
                    CategoriaEnum.PERIODONTIA,
                    550.00,
                    "Raspagem e alisamento radicular por quadrante.",
                ),
                (
                    "Cirurgia Periodontal (Retalho)",
                    CategoriaEnum.PERIODONTIA,
                    1800.00,
                    "Cirurgia de acesso periodontal.",
                ),
                (
                    "Controle Periodontal (Manutenção)",
                    CategoriaEnum.PERIODONTIA,
                    220.00,
                    "Sessão de manutenção periodontal.",
                ),
                (
                    "Gengivoplastia Estética",
                    CategoriaEnum.PERIODONTIA,
                    900.00,
                    "Remodelação de contorno gengival.",
                ),
                (
                    "Aplicação Antimicrobiano Local",
                    CategoriaEnum.PERIODONTIA,
                    300.00,
                    "Inserção local (ex: gel clorexidina).",
                ),
                # Prótese
                (
                    "Coroa Metalo-Cerâmica",
                    CategoriaEnum.PROTESE,
                    1800.00,
                    "Coroa metalocerâmica unitária.",
                ),
                (
                    "Coroa Cerâmica Pura",
                    CategoriaEnum.PROTESE,
                    2400.00,
                    "Coroa em cerâmica pura (Ex: E.max).",
                ),
                (
                    "PPR Acrílica (Parcial Removível)",
                    CategoriaEnum.PROTESE,
                    2800.00,
                    "Prótese parcial removível acrílica.",
                ),
                (
                    "Prótese Total (Arcada)",
                    CategoriaEnum.PROTESE,
                    3500.00,
                    "Prótese total convencional de uma arcada.",
                ),
                (
                    "Planejamento Prótese sobre Implante",
                    CategoriaEnum.PROTESE,
                    700.00,
                    "Planejamento e estudo para prótese \
implanto-suportada.",
                ),
                (
                    "Reembasamento PPR",
                    CategoriaEnum.PROTESE,
                    650.00,
                    "Reembasamento e ajuste de PPR.",
                ),
                (
                    "Reparação Prótese Total",
                    CategoriaEnum.PROTESE,
                    400.00,
                    "Pequenos reparos em prótese total.",
                ),
                # Implantodontia
                (
                    "Implante Unitário (Colocação)",
                    CategoriaEnum.IMPLANTODONTIA,
                    2600.00,
                    "Instalação de implante unitário.",
                ),
                (
                    "Implante Adicional (por dente)",
                    CategoriaEnum.IMPLANTODONTIA,
                    2400.00,
                    "Implante extra em mesma sessão.",
                ),
                (
                    "Levantamento de Seio Maxilar",
                    CategoriaEnum.IMPLANTODONTIA,
                    4200.00,
                    "Cirurgia de elevação de seio.",
                ),
                (
                    "Enxerto Ósseo Localizado",
                    CategoriaEnum.IMPLANTODONTIA,
                    1900.00,
                    "Enxerto em área limitada.",
                ),
                (
                    "Instalação de Pilar",
                    CategoriaEnum.IMPLANTODONTIA,
                    750.00,
                    "Colocação de componente protético (pilar).",
                ),
                (
                    "Protocolo Implantes (Planejamento)",
                    CategoriaEnum.IMPLANTODONTIA,
                    2500.00,
                    "Planejamento de prótese protocolo.",
                ),
                (
                    "Manutenção Prótese sobre Implante",
                    CategoriaEnum.IMPLANTODONTIA,
                    450.00,
                    "Ajustes e limpeza especializada.",
                ),
                # Odontopediatria
                (
                    "Profilaxia Infantil",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    130.00,
                    "Limpeza e controle de placa infantil.",
                ),
                (
                    "Aplicação de Flúor Infantil",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    70.00,
                    "Aplicação tópica preventiva infantil.",
                ),
                (
                    "Selante Infantil (por dente)",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    80.00,
                    "Selamento preventivo em dente decíduo.",
                ),
                (
                    "Restauração Resina Infantil",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    200.00,
                    "Restauração em dente decíduo.",
                ),
                (
                    "Pulpotomia Dente Decíduo",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    450.00,
                    "Terapia pulpar coronária em decíduo.",
                ),
                (
                    "Exodontia Dente Decíduo",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    180.00,
                    "Extração simples de dente decíduo.",
                ),
                (
                    "Consulta Controle de Hábitos",
                    CategoriaEnum.ODONTOPEDIATRIA,
                    160.00,
                    "Acompanhamento de hábitos (sucção digital, bruxismo).",
                ),
                # Cirurgia Bucomaxilofacial
                (
                    "Exodontia Simples",
                    CategoriaEnum.CIRURGIA,
                    300.00,
                    "Extração sem complicações.",
                ),
                (
                    "Exodontia Dente Incluso (Siso)",
                    CategoriaEnum.CIRURGIA,
                    950.00,
                    "Remoção de terceiro molar incluso.",
                ),
                (
                    "Frenectomia Lingual/Labial",
                    CategoriaEnum.CIRURGIA,
                    850.00,
                    "Remoção de freio labial ou lingual.",
                ),
                (
                    "Biópsia de Lesão",
                    CategoriaEnum.CIRURGIA,
                    650.00,
                    "Remoção e envio de tecido para análise.",
                ),
                (
                    "Apicectomia",
                    CategoriaEnum.CIRURGIA,
                    1800.00,
                    "Cirurgia de remoção de ápice radicular.",
                ),
                (
                    "Remoção de Cisto Simples",
                    CategoriaEnum.CIRURGIA,
                    2200.00,
                    "Exérese de cisto pequeno.",
                ),
                (
                    "Drenagem de Abscesso",
                    CategoriaEnum.CIRURGIA,
                    500.00,
                    "Procedimento de drenagem e irrigação.",
                ),
                # Estética/Cosmética
                (
                    "Clareamento Caseiro (Kit)",
                    CategoriaEnum.ESTETICA,
                    950.00,
                    "Moldes + kit peróxido (tratamento domiciliar).",
                ),
                (
                    "Clareamento Consultório (Sessão)",
                    CategoriaEnum.ESTETICA,
                    750.00,
                    "Sessão com peróxido alta concentração.",
                ),
                (
                    "Faceta Resina Direta (Unitária)",
                    CategoriaEnum.ESTETICA,
                    600.00,
                    "Faceta direta em resina composta.",
                ),
                (
                    "Faceta Cerâmica (Unitária)",
                    CategoriaEnum.ESTETICA,
                    2200.00,
                    "Faceta cerâmica laboratorizada.",
                ),
                (
                    "Lente de Contato Dental",
                    CategoriaEnum.ESTETICA,
                    2500.00,
                    "Lâmina cerâmica ultrafina.",
                ),
                (
                    "Microabrasão de Esmalte",
                    CategoriaEnum.ESTETICA,
                    400.00,
                    "Remoção de manchas superficiais.",
                ),
                (
                    "Escultura Gengival Estética",
                    CategoriaEnum.ESTETICA,
                    950.00,
                    "Remodelação a laser ou bisturi.",
                ),
                # Outros
                (
                    "Radiografia Periapical",
                    CategoriaEnum.OUTROS,
                    45.00,
                    "Imagem periapical diagnóstica.",
                ),
                (
                    "Tomografia Odontológica (Pedido)",
                    CategoriaEnum.OUTROS,
                    90.00,
                    "Pedido e avaliação de tomografia.",
                ),
                (
                    "Laserterapia (Sessão)",
                    CategoriaEnum.OUTROS,
                    150.00,
                    "Sessão de fotobiomodulação terapêutica.",
                ),
                (
                    "Consulta de Urgência",
                    CategoriaEnum.OUTROS,
                    260.00,
                    "Atendimento emergencial sem agendamento.",
                ),
                (
                    "Avaliação Inicial Completa",
                    CategoriaEnum.OUTROS,
                    300.00,
                    "Consulta clínica abrangente.",
                ),
                (
                    "Planejamento Digital do Sorriso",
                    CategoriaEnum.OUTROS,
                    1800.00,
                    "Mockup e fluxo digital de sorriso.",
                ),
            ]

            for nome, categoria, valor, desc in procedimentos_catalogo:
                proc = Procedimento()
                proc.nome = nome
                proc.categoria = categoria
                proc.valor_padrao = valor
                proc.descricao = desc
                db.session.add(proc)
            try:
                db.session.commit()
                total_procs = len(procedimentos_catalogo)
                print(
                    "INFO: [seed_tenant_default] Catálogo criado com "
                    f"{total_procs} procedimentos."
                )
            except Exception as proc_err:
                db.session.rollback()
                print(
                    "ERRO: [seed_tenant_default] Falha ao criar catálogo "
                    f"de procedimentos: {proc_err}"
                )
                raise
        else:
            print(
                "INFO: [seed_tenant_default] Já existem "
                f"{existing_proc} procedimentos. Catálogo não recriado."
            )

        # -----------------------------
        # Templates de documento padrão
        # -----------------------------
        # Criar somente se não existirem registros desse tipo
        existentes = db.session.query(TemplateDocumento).count()
        if existentes == 0:
            # v2.0: Templates com string.Template ($variavel) e blocos
            atestado = TemplateDocumento()
            atestado.nome = "Atestado Simples"
            atestado.tipo_doc = TipoDocumento.ATESTADO
            atestado.template_body = (
                "Atesto que $paciente_nome, portador do CPF "
                "$paciente_cpf, necessita de $dias_repouso dias de "
                "repouso.\n\n__BLOCO_CID__\n\n"
                "Emitido sob responsabilidade de Dr(a). $dentista_nome."
            )
            atestado.is_active = True

            receita = TemplateDocumento()
            receita.nome = "Receita Simples"
            receita.tipo_doc = TipoDocumento.RECEITA
            receita.template_body = (
                "Prescrição:\n"
                "1. $nome_remedio\n"
                "   $posologia_remedio\n\n"
                "Paciente: $paciente_nome\n"
                "CRM/CRO: $dentista_cro — Profissional: $dentista_nome"
            )
            receita.is_active = True
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


if __name__ == "__main__":
    # Permite rodar diretamente: python app/seeder.py
    # Ajuste do app context para que 'db' funcione fora do Flask CLI
    # Carregar variáveis de ambiente do .env (se existir)
    try:
        dotenv_mod = importlib.import_module("dotenv")
        load_dotenv = getattr(
            dotenv_mod, "load_dotenv", lambda *_a, **_k: False
        )
    except Exception:

        def load_dotenv(*_args, **_kwargs):  # type: ignore
            return False

    load_dotenv()

    cfg = os.environ.get("FLASK_CONFIG") or "default"
    app = create_app(cfg)
    with app.app_context():
        # Assegura search_path correto
        db.session.execute(
            text("SET SESSION search_path TO tenant_default, public")
        )
        # Executa seeds na ordem
        seed_public()
        seed_tenant_default()
        print("INFO: [__main__] Seeders executados com sucesso.")
