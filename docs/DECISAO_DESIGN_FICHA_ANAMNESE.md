# DECISÃO DE DESIGN: [Ficha + Anamnese] - Conceito Selecionado

**Data:** 7 de Novembro de 2025
**Responsável:** Líder de Tecnologia
**Destinatário:** Arquiteto de Sistema

---

## 1. RESUMO EXECUTIVO

Após análise técnica e simulação visual (ASCII mockups), **seleciono o Conceito 1: "Split Vertical com Alerta-Âncora"** para implementação da Tela 1 ([Ficha + Anamnese]).

---

## 2. CONCEITO SELECIONADO

**Nome:** Split Vertical com Alerta-Âncora

**Características Principais:**
- **Layout:** Dois painéis lado a lado (50/50) - Ficha Cadastral (esquerda) e Anamnese (direita)
- **Navegação:** Tab Bar horizontal no topo (5 abas: Ficha+Anamnese, Odontograma, Planejamento, Financeiro, Histórico)
- **Alerta de Anamnese:** Banner amarelo fixo no topo da área de conteúdo, imediatamente abaixo da navegação
- **Formulário:** Único `<form>` envolvendo ambos os painéis, com botão "Salvar" centralizado no rodapé

---

## 3. JUSTIFICATIVA DA ESCOLHA

### 3.1 Conformidade Arquitetural (100%)

| Requisito Crítico | Status | Implementação |
|-------------------|--------|---------------|
| **§7.4 - Alerta Intrusivo** | ✅ **Total** | Banner amarelo ocupa largura total, impossível de ignorar, com CTA claro ("Atualizar Agora") |
| **§8.2 - Saída Suja** | ✅ **Total** | Formulário único simplifica `window.isFormDirty`. Compatível com `global.js` existente sem alterações |
| §1 - Stack HTMX | ✅ | Navegação por `hx-get`, backend renderiza HTML |
| §10.1 - Sem Inline CSS/JS | ✅ | Estilos externalizados (`global.css` + `ficha_paciente.css`) |
| §10.3 - CSS Escopado | ✅ | Prefixo `.ficha-paciente-container` |
| §2 - Navegação 5 Telas | ✅ | Tab Bar é o padrão de navegação global |

### 3.2 Vantagens Clínicas

1. **Visibilidade Máxima:** O alerta de anamnese pendente/desatualizada é **bloqueador visual**, alinhado com o requisito de compliance legal/regulatório.
2. **Contexto Dual:** Ficha e Anamnese visíveis simultaneamente (sem scroll horizontal) permite correlação rápida de dados demográficos e de saúde durante o atendimento.
3. **Fluxo de Trabalho Claro:** O banner intrusivo força o dentista a resolver a pendência de anamnese *antes* de iniciar o diagnóstico (Odontograma), reduzindo risco de atendimento sem dados de saúde atualizados.

### 3.3 Trade-off Aceitável

**Custo:** Consome ~12 linhas de espaço vertical (Tab Bar + Banner de alerta), exigindo scroll em laptops de 13" para visualizar formulários completos.

**Benefício:** Este custo é **aceitável e necessário** porque:
- O alerta §7.4 é um requisito de **conformidade legal**, não de UX.
- A natureza "intrusiva" é deliberada (não é um bug, é a especificação).
- Telas clínicas densas (formulários médicos) normalmente exigem scroll; este design apenas torna o alerta *prioritário* no viewport.

---

## 4. IMPACTO NA ARQUITETURA

### 4.1 Backend (Flask)
- **Rota:** `GET /paciente/<id>/ficha` renderiza `ficha_paciente.html` (fragmento HTMX ou página completa).
- **Lógica de Alerta:** Service calcula status de anamnese (`PENDENTE` ou `data_atualizacao > 6 meses`) e passa como contexto Jinja.
- **Integração BrasilAPI:** Endpoint HTMX para busca de CEP (`POST /api/buscar-cep`).

### 4.2 Frontend
- **Template:** `templates/paciente/ficha_paciente.html`
  - Contêiner raiz: `<div class="ficha-paciente-container">`
  - Banner condicional: `{% if mostrar_alerta_anamnese %} ... {% endif %}`
  - Split layout: Flexbox (`.split-panel-left`, `.split-panel-right`)
  - Formulário único: `<form id="form-ficha-anamnese" hx-post="/paciente/{{ paciente.id }}/atualizar">`

- **CSS:**
  - `static/css/global.css`: Design Tokens (`--warning-bg`, `--warning-border`, `.tab-bar`)
  - `static/css/ficha_paciente.css`: Estilos escopados (`.ficha-paciente-container .anamnese-alert`, `.split-panel-*`)
  - Media query: Empilhamento vertical (`flex-direction: column`) em telas < 768px

- **JS:**
  - `static/js/global.js`: Já possui `window.isFormDirty` e `htmx:beforeRequest`. Nenhuma alteração necessária.
  - Scroll suave para âncora (opcional): ~5 linhas para smooth scroll ao clicar em "Atualizar Agora".

### 4.3 Estimativa de Esforço
- **Tempo de Implementação:** ~4-6 horas (backend + frontend + testes visuais)
- **Risco Técnico:** Baixo (padrão HTMX + Flexbox, sem dependências externas)

---

## 5. PRÓXIMOS PASSOS (PROPOSTA)

1. **Aprovação do Arquiteto:** Confirmar que o Conceito 1 está alinhado com a visão de UX/compliance do sistema.
2. **Passo 1 - Implementação Backend:**
   - Criar/atualizar `paciente_service.py` com lógica de validação de anamnese.
   - Criar rota `GET /paciente/<id>/ficha` no `paciente_bp.py`.
3. **Passo 2 - Implementação Frontend:**
   - Criar `templates/paciente/ficha_paciente.html`.
   - Criar `static/css/ficha_paciente.css`.
   - Atualizar `global.css` com Design Tokens (se necessário).
4. **Passo 3 - Verificação:**
   - Teste visual com MCP (browser automation) para confirmar:
     - Alerta aparece quando `status == PENDENTE`.
     - Alerta desaparece quando anamnese está válida.
     - `window.isFormDirty` previne perda de dados ao clicar em outra aba.
     - Layout responsivo (desktop + mobile).

---

## 6. ANEXOS

- **Mockup Visual (ASCII):** `docs/FICHA_ANAMNESE_DESIGN_MOCKUPS.md` (Conceito 1, estados com/sem alerta)
- **Análise de Conceitos:** `docs/FICHA_ANAMNESE_DESIGN_MOCKUPS.md` (Seção "Relatório de Reconhecimento")

---

## 7. DECLARAÇÃO DE CONFORMIDADE

Confirmo que o **Conceito 1: Split Vertical com Alerta-Âncora** atende a **100% das restrições arquiteturais** especificadas no `AGENTS.MD`, incluindo:
- ✅ Requisito [CRÍTICO] §7.4 (Alerta Intrusivo de Anamnese)
- ✅ Requisito [CRÍTICO] §8.2 (Proteção contra Saída Suja)
- ✅ Stack HTMX pura (§1)
- ✅ Proibição de CSS/JS inline (§10.1)
- ✅ CSS Escopado (§10.3)
- ✅ Navegação consistente para as 5 Telas (§2)

Solicito autorização para prosseguir com a implementação (Passo 1).

---

**Assinatura Digital:**
Líder de Tecnologia - EchoDent
7 de Novembro de 2025
