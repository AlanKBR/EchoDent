# EchoDent - Diretrizes de Arquitetura (v4 - Híbrida)

Este projeto, **EchoDental**, é um sucessor espiritual do OdontoClin. Suas ações de codificação DEVEM aderir estritamente a estas regras de arquitetura, workflow e robustez.

## 1. Stack e Filosofia
* **Backend:** Flask
* **Frontend:** HTMX (Arquitetura de Hipermídia). O backend renderiza HTML.
* **PDFs:** HTML + @media print (client-side).
* **3D:** Three.js (para o Odontograma Master).
* **Filosofia:** Offline-first (rede local), robustez, simplicidade, workflow clínico-primeiro.

## 2. Arquitetura de UI (As 5 Telas do Paciente)
A interação com o paciente é centralizada em 5 abas/telas:
1.  **`[Ficha + Anamnese]`:** Dados cadastrais (com `BrasilAPI` para CEP) e Anamnese (com alertas de pendência/revalidação).
2.  **`[Odontograma Master]` (3D):** O hub *clínico* (Three.js) para diagnóstico. Salva dados na tabela `AchadoClinico`. Possui um "Catálogo de Serviços" (pesquisa) para adicionar itens avulsos (ex: Limpeza).
3.  **`[Planejamento Financeiro]` (Orçamentos):** A lista de `PlanoTratamento`. Mostra um **Diagrama 2D-SVG** (dinâmico) para cada plano.
4.  **`[Financeiro (Extrato)]`:** O extrato global do paciente, o "Carnê Cosmético" (`ParcelaPrevista`), e os botões de Admin (`Ajustar Saldo`, `Estorno`).
5.  **`[Histórico]`:** A timeline *legível* (vinda da tabela `TimelineEvento`).

## 3. Workflow Clínico (Odontograma)
* **Master (3D) vs. Snapshot (2D):** A Tela 2 (3D) é a ferramenta de trabalho "viva". A Tela 3 (Plano) DEVE exibir um "snapshot" 2D-SVG dinâmico, *apenas* com os itens daquele plano.
* **Estado (Inicial vs. Atual):**
    * **"Atual" (Vivo):** A tabela `AchadoClinico` (minimalista: `paciente_id`, `dente`, `faces`, `diagnostico_cod`) é a fonte da verdade do Odontograma Master.
    * **"Inicial" (Imutável):** O campo `Paciente.odontograma_inicial_json` armazena um snapshot JSON do primeiro diagnóstico, que SÓ PODE ser sobrescrito por um Admin.
* **Lançamento Avulso (Catálogo):** O `service` DEVE suportar a criação de `ItemPlano` com `dente=NULL` e `achado_clinico_id=NULL` (vindos do "Catálogo de Serviços" na Tela 2).

## 4. Workflow Financeiro (O "Plano Perfeito")
* **Fonte da Verdade (A "Soma Burra"):** O `Saldo Devedor` DEVE ser sempre um cálculo dinâmico: `Plano.valor_total - SUM(Lancamentos.valor_pago)`.
* **Crédito (Saldo Negativo):** O `service` DEVE permitir um Saldo Devedor negativo (ex: -R$ 50,00). A UI DEVE renderizar isso como "Crédito Disponível".
* **Fase 1: `PROPOSTO` (Flexível):** O `service` DEVE permitir a edição (via UI/HTMX) dos campos `ItemPlano.procedimento_nome_historico` e `ItemPlano.valor_cobrado`.
* **Fase 2: `APROVADO` (Selado):** O `service` DEVE *bloquear* a edição desses campos.
* **Preços (Congelados):** O `service` DEVE "congelar" (denormalizar) o preço e o nome no `ItemPlano` no momento da criação. O `PlanoTratamento` *não* será afetado por reajustes futuros (Regra "Orto").
* **Parcelas (Carnê Cosmético):** O modelo `ParcelaPrevista` é *apenas* um lembrete visual (sem status). A UI (Jinja) DEVE renderizar o status (`Paga/Parcial/Pendente`) dinamicamente, comparando `SUM(Lancamentos.valor_pago)` contra a lista de `ParcelaPrevista`.
* **Ajustes (Desconto/Juros/Quitação):** *NÃO* se edita um plano `APROVADO`. Ajustes DEVEM ser feitos criando um `LancamentoFinanceiro` com `tipo_lancamento="AJUSET"` e `notas_motivo` (obrigatório).
* **Upsell (Mudança de Plano):** *NÃO* usar `parent_plan`. Criar um `PlanoTratamento` (Orçamento) *novo* e independente, que pode conter itens de estorno (valor negativo).
* **Inadimplência:** *NÃO* usar status `CANCELADO`. A dívida é permanente. O `Plano` fica `APROVADO` (a menos que quitado via `AJUSET`).

## 5. Arquitetura de Código (Layers)
* **`app/models.py`:** Um arquivo *único* para *todos* os modelos SQLAlchemy.
* **`app/services/`:** Pacote para *toda* lógica de negócio (ex: `financeiro_service.py`).
* **`app/blueprints/`:** Pacote para rotas "burras" (thin controllers) que chamam os *services* e renderizam templates.

## 6. Banco de Dados (Workflow Híbrido - PostgreSQL)
* **Arquitetura:** Um único banco de dados PostgreSQL.
* **Modelo Multi-Tenant:** Arquitetura "Schema-per-Tenant".
* **Schemas:**
    * **`public`:** Contém tabelas de governança global (ex: `Tenant`, `GlobalSetting`) e tabelas de infraestrutura (ex: `DeveloperLog`). Modelos DEVEM ser marcados com `__table_args__ = {"schema": "public"}`.
    * **`tenant_xxx` (ex: `tenant_default`):** Contém todos os dados de negócios isolados da clínica (ex: `Paciente`, `Usuario`, `PlanoTratamento`, `LogAuditoria`). Modelos DEVEM ser agnósticos de schema (não possuem `__table_args__`).
* **Resolução de Schema:** A aplicação (em `app/__init__.py`) DEVE interceptar todas as requisições (`@app.before_request`) e definir o `search_path` da sessão do banco de dados (ex: `SET LOCAL search_path TO tenant_default, public`).
* **Foreign Keys (Importante):** `db.ForeignKey` são **mandatórias** para garantir a integridade referencial *dentro* de cada schema (ex: `Agendamento.dentista_id` -> `Usuario.id`).
* **Concorrência (Mandatório):** O sistema depende do controle de concorrência (MVCC) nativo do PostgreSQL.
* **Workflow de Schema (Híbrido - DEV):** O desenvolvimento é otimizado para velocidade.
    * **Trabalho Diário (Rápido):** `flask dev-sync-db`. Este comando é a fonte da verdade para DEV. Ele DEVE apontar para o `DATABASE_URL` principal (ex: `echodent_dev`).
    * **Execução do `dev-sync-db`:**
        1.  `DROP/CREATE SCHEMAS` (`public`, `tenant_default`).
        2.  `db.create_all()`: Constrói o schema *instantaneamente* a partir dos `app/models.py`. (Não usa `flask_migrate.upgrade()`).
        3.  `seeder.py`: Popula os dados de teste.
* **Migrações (Alembic - PROD):** A geração de migrações é uma ação de "consolidação" feita antes do deploy, não diariamente.
    * **Geração (`migrate`):** O comando `flask db migrate` DEVE ser configurado (via `alembic.ini` ou `env.py`) para apontar para um "Banco Sombra" (ex: `SHADOW_DATABASE_URL=.../echodent_shadow`). Este banco sombra *nunca* é tocado pelo `dev-sync-db`, permitindo que o Alembic calcule o *diff* correto entre os `models.py` e o estado de migração anterior.
    * **Aplicação (`upgrade`):** O comando `flask db upgrade` DEVE usar a lógica "two-pass" (Public -> Tenants) para aplicar os scripts gerados no ambiente de produção.

## 7. Requisitos de Robustez (Humano/Legal)
* **Offboarding:** *Sempre* usar Soft-Delete (`is_active=False`) para `Usuario` e `ProcedimentoMestre`. Nunca excluir, para preservar o histórico.
* **Log de Auditoria (Legal):** Logs criados automaticamente (via eventos SQLAlchemy) capturando `user_id` e `changes_json`, armazenados no schema `tenant`.
* **Log de Histórico (UX):** *NÃO* usar `SQL UNION`. Criar uma tabela `TimelineEvento` (dedicada) e populá-la (via escrita dupla) na camada de `services/` para uma timeline legível e performática.
* **Anamnese (Segurança):** A UI DEVE exibir um "Alerta Amarelo" intrusivo se `Anamnese.status == "PENDENTE"` ou `Anamnese.data_atualizacao > 6 meses`.
* **Atomicidade (Mandatório):** *Toda* função no `services/` que escreve no DB DEVE usar `try/commit/rollback` para garantir transações atômicas.
* **Sanitização:** O `services/` DEVE usar uma função `utils.sanitizar_input()` em todos os campos de texto livre (`Text`, `String`) antes de salvar no DB.
* **Trava de Caixa:** O `service` de Estorno DEVE ser bloqueado se `FechamentoCaixa.status == "Fechado"`, forçando o Admin a usar um `AJUSET` no dia atual.

## 8. Robustez de UI (Mandatório)
* **Clique Duplo:** *Todo* botão/link de ação (`hx-post`, `hx-put`, etc.) DEVE ser desabilitado via CSS (`.htmx-request { pointer-events: none; }`) durante a requisição.
* **Saída Suja:** O `global.js` DEVE implementar a flag `window.isFormDirty` (acionada por `<form>` *e* pelo `three.js`) e usar `htmx:beforeRequest` para disparar um `window.confirm()` e prevenir perda de dados.

## 9. Regras Técnicas (PDF, Datas, Mídia)
* **Timezone (Mandatório):** Todos os `DateTime` no DB DEVEM ser `timezone=True` (UTC).
* **PDFs:** (Removido WeasyPrint) A geração de PDF/Impressão segue client-side via window.print conforme regra abaixo.
* **Mídia (RX):** Salvar arquivos em `instance/media_storage/` com caminhos relativos. *Não* usar blobs. *Não* comprimir imagens de diagnóstico.
* **PDFs e Impressão (window.print):** A geração de PDF é delegada 100% ao cliente (navegador). O servidor renderizará HTML puro (com um CSS `@media print` dedicado) em uma rota de impressão (ex: `/imprimir/log/<id>`). O `service` NÃO salva o PDF; a persistência é feita no `LogEmissao` (dados-chave JSON).

## 10. Regras de Frontend (CSS/JS)
* **Proibido:** *NÃO* usar CSS/JS inline (atributos `style="..."` ou `<script>...</script>`).
* **`global.css`:** Usar para Design Tokens (Variáveis CSS) e componentes (ex: `.card`).
* **CSS Escopado:** Estilos de páginas específicas DEVEM ser escopados ao seu contêiner raiz (ex: `.ficha-paciente-container .tabela-especifica { ... }`).

## 11. Dev Shortcuts (DEV ONLY)
* As rotas `/__dev/login_as/...` e scripts de purga (como `purge_dev_users.py`) são permitidos, mas DEVEM ser bloqueados se `app.debug == False`.
* Ignorar `pytest` para mudanças visuais (CSS/JS) é aceitável; focar em testes visuais.
