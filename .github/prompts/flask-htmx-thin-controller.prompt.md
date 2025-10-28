---
mode: 'agent'
description: 'Gerar/Refatorar controladores Flask (Blueprints) finos para HTMX, delegando a services, retornando parciais Jinja e respeitando as regras EchoDent.'
tools: ['edit', 'search', 'runTasks', 'think', 'changes', 'todos']
---
# Flask + HTMX Thin Controller (EchoDent)

Gere ou refatore rotas (Blueprints) seguindo a arquitetura EchoDent:
- Controllers "burros" (fina orquestração)
- Toda lógica/DB no `services/` com transação atômica (try/commit/rollback)
- Renderização Jinja; HTMX recebe parciais, navegação normal recebe páginas completas
- Sem CSS/JS inline; usar componentes/partials e `static/`

## Entradas que você deve pedir/assumir
- Blueprint alvo (arquivo em `app/blueprints/*.py` e nome do `Blueprint`)
- Rota: método(s), URL, nome da função
- Service alvo: caminho e assinatura (ex: `financeiro_service.create_ajuste(paciente_id, valor, notas_motivo, user_id)`)
- Templates: parcial (ex: `components/flash.html` ou lista/table-row) e página completa (fallback)
- URL canônica para redirect após sucesso quando não-HTMX

## Regras Obrigatórias (EchoDent)
- NUNCA abrir/fechar transação no controller; apenas chamar a função do `service` (atomicidade está no service)
- Sanitização de campos de texto via `utils.sanitizar_input()` acontece NO SERVICE, não no controller
- Detectar HTMX via `request.headers.get('HX-Request') == 'true'`
- Para sucesso:
  - HTMX: retornar parcial atualizado (ou fragmento DOM) + opcionalmente `HX-Trigger` com mensagem
  - Não-HTMX: `redirect(url_for(...))`
- Para erro (exceção do service):
  - Registrar erro e retornar parcial de erro/flash (HTMX) OU `flash(..)` + redirect (não-HTMX)
- NUNCA usar CSS/JS inline; respeitar `.htmx-request { pointer-events: none; }` e o fluxo `window.isFormDirty`
- Componentes Jinja devem ser escopados por container raiz da página

## Padrões de Código (esqueleto)
- Importar apenas o necessário (`Blueprint`, `request`, `render_template`, `redirect`, `url_for`, `flash`)
- Padrão de detecção HTMX:
  - `is_hx = request.headers.get('HX-Request') == 'true'`
- Receber dados tanto de `request.form` quanto `request.get_json(silent=True)`
- Chamar o `service` e capturar exceções específicas (ex.: `ValueError`, `IntegrityError`) e genéricas

## Contrato de Saída
- Trecho de código da rota adicionada/atualizada no arquivo de blueprint correto
- Criação de parciais necessários em `templates/components/...` (se ausentes)
- Comentários mínimos no código explicando decisões (1-2 linhas)

## Exemplo de Fluxo (ilustrativo)
1. POST `/financeiro/ajuste`
2. Controller extrai `paciente_id`, `valor`, `notas_motivo` e `user_id`
3. Chama `financeiro_service.create_ajuste(...)`
4. Se HTMX: renderiza `components/flash.html` e/ou um row atualizado
5. Se não-HTMX: `redirect(url_for('financeiro.extrato', paciente_id=paciente_id))`

## Checklist Antes de Finalizar
- [ ] Controller não contém lógica de negócios/SQL
- [ ] Retornos adequados para HTMX vs. não-HTMX
- [ ] Parciais criados/atualizados sem inline CSS/JS
- [ ] Mensagens de erro/sucesso via flash ou `HX-Trigger`
- [ ] Nome da rota e URL estão consistentes com a navegação existente

## Dicas
- Para listas/tables: retorne apenas a `<tr>` ou `<tbody>` parcial para HTMX
- Use `url_for` para manter rotas desacopladas
- Componentize mensagens em `templates/components/flash.html`
