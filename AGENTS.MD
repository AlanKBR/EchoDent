# EchoDent - Diretrizes de Arquitetura

Este projeto segue uma arquitetura específica. Suas ações de codificação devem aderir estritamente a estas regras:

## 1. Stack e Filosofia
* **Backend:** Flask
* **Frontend:** HTMX (Arquitetura de Hipermídia). O backend renderiza HTML.
* **PDFs:** WeasyPrint (renderizando templates Jinja).
* **Filosofia:** Offline-first (rede local), robustez, simplicidade.

## 2. O "Fluxo de Ouro" (Lógica Financeira Central)
* **Fonte da Verdade:** O `PlanoTratamento` é a única fonte de débito.
* **Gatilho:** O `Saldo Devedor` só existe *após* um `PlanoTratamento` ter o status "Aprovado".
* **Integridade:** Todo `LancamentoFinanceiro` (pagamento) *deve* ter uma `ForeignKey` para um `PlanoTratamento`.
* **Recibo Avulso:** Para pagamentos "avulsos" (ex: venda de escova), o *service* deve primeiro criar um `PlanoTratamento` "fantasma" (ex: status="Concluído") e atrelar o pagamento a ele.

## 3. Arquitetura de Código (Layers)
* **`app/models.py`:** Um arquivo *único* para *todos* os modelos SQLAlchemy. (Evitar importação circular).
* **`app/services/`:** Pacote para *toda* lógica de negócio (ex: `financeiro_service.py`).
* **`app/blueprints/`:** Pacote para rotas "burras" (thin controllers) que chamam os *services* e renderizam templates.
* **Estilização (CSS):** Usar preferencialmente um arquivo `global.css` centralizado (ex: `app/static/css/global.css`).
* **Frontend (Boas Práticas):** É proibido CSS/JS inline nos `.html` — inclusive atributos `style="..."`. Todo CSS deve estar no `global.css` (ou arquivos .css linkados) e todo JS em arquivos `.js` separados (ex: `app/static/js/`).

## 4. Banco de Dados (Multi-Bind SQLite)
* **Arquitetura:** Múltiplos bancos SQLite (ex: `pacientes.db`, `users.db`, `history.db`).
* **Gerenciamento:** `SQLAlchemy Binds` no Flask.
* **Foreign Keys (Importante):** *Não* podemos usar `db.ForeignKey` entre bancos diferentes (binds). A integridade referencial (ex: checar se `dentista_id` existe no `users.db`) deve ser validada *manualmente* na camada de `services/`.
* **Concorrência (Mandatório):** Todos os bancos (`.db`) devem usar `PRAGMA journal_mode=WAL`. Isso deve ser configurado nos eventos do SQLAlchemy.
* **Migrações:** Usar `Flask-Migrate` (Alembic) configurado para suportar *multi-bind*.

## 5. Requisitos de Segurança e Legais
* **Offboarding (Mandatório):** *Sempre* usar Soft-Delete para o modelo `Usuario` (um campo `is_active = False`). Nunca excluir um usuário, para preservar o histórico.
* **Auditoria:** Um `history.db` dedicado. Os logs devem ser criados automaticamente (via eventos SQLAlchemy) capturando `user_id` e `changes_json`.
* **Mídia (RX):** Salvar arquivos em `instance/media_storage/`. Usar caminhos relativos no DB. *Não* usar blobs.

## 6. Datas, Horários e Timezone
* **UTC em tudo:** Todos os campos `DateTime` devem usar `timezone=True` e defaults com timezone-aware (ex.: `datetime.now(timezone.utc)`).
* **Proibido:** Evitar `datetime.utcnow()` (naive) e qualquer timestamp sem timezone.
* **Apresentação:** Converter para horário local apenas na camada de template (UI). O que vai ao DB fica em UTC.

## 7. HTMX e Templates (Padrões)
* **Hipermídia first:** Endpoints devem retornar HTML renderizado (parciais/fragmentos onde fizer sentido) — evitar JSON para a UI.
* **Parciais reutilizáveis:** Componentes dinâmicos (ex.: linhas de tabelas, widgets) devem ter parciais Jinja específicas para HTMX (`_*.html`).
* **DOM Targets:** IDs/anchors estáveis para `hx-target` e `hx-swap`. Evitar dependência de seletores frágeis.
* **Progressive enhancement:** A página base deve funcionar com full reload; HTMX melhora a UX, mas não deve ser obrigatório.
* **Sem JS inline:** Qualquer JS complementar vai em `app/static/js/`. CSS somente em `app/static/css/global.css`.
* **Design Tokens:** Toda UI deve ser construída sobre os Design Tokens (Variáveis CSS) definidos em `global.css`.
* **Componentização de Estilos:** Usar classes de componentes (ex.: `.card`, `.btn`, `.alert`) em vez de estilizar elementos brutos.
* **Estrutura de Páginas/Formulários:** Novos formulários/páginas devem usar a estrutura `.card` (com `.card-header` / `.card-body`) e botões `.btn-primary` / `.btn-secondary`.

## 8. PDFs e WeasyPrint (Windows)
* **Dependências nativas:** Em Windows, é necessário MSYS2 + Pango. Configure `WEASYPRINT_DLL_DIRECTORIES` apontando para `C:\msys64\mingw64\bin` quando presente.
* **Import lazy:** Os imports de WeasyPrint devem ocorrer dentro das rotas/serviços de impressão para não quebrar o app quando as DLLs não existirem.
* **Falhas elegantes:** Se faltar dependência nativa, a rota deve responder com erro amigável/log claro, sem derrubar a aplicação.
* **Offline-first:** Templates Jinja de PDF devem funcionar sem internet (fonts/assets locais).

## 9. SQLAlchemy 2.x — Conformidade
* **API 2.0:** Usar `Session.get(Model, id)` no lugar de `Query.get` (evitar Legacy API warnings).
* **Timezone nos modelos:** Declarar `DateTime(timezone=True)` e defaults aware (ver Seção 6).
* **WAL por bind:** Garantir `PRAGMA journal_mode=WAL` em todos os binds via listeners de engine.
* **Multi-bind:** Nunca usar `db.ForeignKey` entre bancos. Integridade entre binds é responsabilidade da camada `services/` (validações explícitas).

## 10. Segurança de Rotas e Papéis
* **Autenticação:** Rotas mutáveis exigem usuário autenticado.
* **Papéis (RBAC):** Restringir rotas administrativas (ex.: seeding, manutenção) a `ADMIN`. Evitar expor endpoints de debug em produção.
* **CSRF:** Formularios de escrita devem usar proteção CSRF (ex.: Flask-WTF), quando aplicável ao stack vigente.
* **Soft-Delete efetivo:** O fluxo de login deve checar `Usuario.is_active` para impedir acesso de desligados.

## 11. Mídia (RX) — Política Detalhada
* **Local de armazenamento:** `instance/media_storage/`, caminhos relativos gravados no DB.
* **Tipos e tamanho:** Restringir tipos permitidos (ex.: imagens/PDF) e limite de tamanho configurável; validar no service antes de salvar.
* **Sanitização:** Normalizar nomes de arquivos (sem espaços/caracteres proibidos) e evitar colisões (prefixo com UUID/data).
* **Privacidade:** URLs de mídia não devem vazar informações sensíveis; preferir controle de acesso por rota protegida quando necessário.

## 12. Fluxo de Ouro — Detalhes Operacionais
* **Aprovação como gatilho:** O `Saldo Devedor` só passa a existir após `PlanoTratamento.status == APROVADO`.
* **Pagamentos sempre com plano:** Todo `LancamentoFinanceiro` referencia um `PlanoTratamento` válido no mesmo bind.
* **Recibo Avulso:** Criar um plano "fantasma" (ex.: `CONCLUIDO`) antes de registrar o pagamento avulso e associá-lo a este plano.
* **Baixa do saldo:** Lançamentos reduzem o saldo do plano até zerar; status de quitação conforme regra de negócio.

## 13. Observabilidade e Auditoria
* **Eventos automáticos:** Logs em `history.db` via eventos SQLAlchemy, incluindo `user_id`, `timestamp UTC` e `changes_json`.
* **Erros previsíveis:** Mensagens de erro devem ser amigáveis ao usuário e detalhadas no log (stack/causa raiz) para o operador.

## 14. Checklist de Revisão (PR)
* Modelos: `DateTime(timezone=True)` e defaults em UTC (aware)? Sem `Query.get` legado?
* Services: validações entre binds estão presentes? Fluxo de Ouro respeitado (aprovado → saldo)?
* Rotas: sem lógica pesada (thin controllers)? Protegidas por auth/papéis?
* Templates/HTMX: sem CSS/JS inline? Parciais reutilizáveis? IDs estáveis para `hx-target`?
* PDFs: Import lazy e falha elegante se WeasyPrint ausente? Assets locais?
* Mídia: validação de tipos/tamanho e nomes sanitizados? Caminhos relativos?
* DB: PRAGMA WAL por bind ativo? Sem FKs cross-bind? Migrações cientes de multi-bind?