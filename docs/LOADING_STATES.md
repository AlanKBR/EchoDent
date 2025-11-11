# Sistema de Loading States - EchoDent

**Versão:** 1.0
**Data:** Novembro 2025
**Princípios:** Simplicidade, Modularidade, Zero Dependências

---

## 📋 Visão Geral

Sistema global de feedback visual para operações assíncronas (HTMX, fetch, forms). Totalmente baseado em CSS + atributos HTML nativos.

### Características:
- ✅ **Zero JavaScript customizado** - Usa apenas hooks HTMX nativos
- ✅ **CSS puro** - Animações via `@keyframes`
- ✅ **Modular** - Funciona em botões, cards, containers
- ✅ **Acessível** - `aria-busy`, `aria-live` para screen readers
- ✅ **Performance** - CSS animations com `will-change`

---

## 🎨 Componentes

### 1. Spinner SVG (Ícone Global)

**Localização:** `app/templates/utils/_spinner.html`

```html
<!-- Spinner inline (16x16px por padrão) -->
<svg class="spinner" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
  <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2"
          fill="none" stroke-linecap="round" stroke-dasharray="30 10"/>
</svg>
```

**Uso:**
- `currentColor` herda a cor do contexto (branco em botões primários, azul em secondary)
- Tamanhos: Classe `.spinner-sm` (12px), `.spinner-lg` (24px)

---

### 2. Loading em Botões

#### Pattern HTML:
```html
<button class="btn btn-primary"
        hx-post="/api/salvar"
        hx-indicator=".htmx-indicator">
  <span class="btn-text">Salvar</span>
  <span class="htmx-indicator">
    {% include 'utils/_spinner.html' %}
  </span>
</button>
```

#### CSS Automático:
```css
/* global.css - já implementado */
.htmx-indicator {
  display: none;
}

.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator {
  display: inline-block;
}

.htmx-request .btn-text {
  display: none;
}
```

#### Resultado:
- **Idle:** "Salvar" visível, spinner oculto
- **Loading:** Spinner visível, "Salvar" oculto
- **Auto-troca:** HTMX adiciona `.htmx-request` automaticamente

---

### 3. Loading em Cards/Containers

#### Pattern HTML:
```html
<div class="card"
     hx-get="/api/dados"
     hx-trigger="load"
     hx-indicator="this"
     aria-busy="false">
  <div class="card-body">
    <div class="loading-overlay">
      {% include 'utils/_spinner.html' with spinner_size='lg' %}
      <p class="loading-text">Carregando dados...</p>
    </div>
    <div class="card-content">
      <!-- Conteúdo aqui -->
    </div>
  </div>
</div>
```

#### CSS:
```css
/* settings.css */
.loading-overlay {
  display: none;
  position: absolute;
  inset: 0;
  background: var(--color-surface-card);
  z-index: 10;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: var(--space-2);
}

.htmx-request .loading-overlay {
  display: flex;
}

.htmx-request .card-content {
  opacity: 0.3;
  pointer-events: none;
}
```

#### Resultado:
- **Loading:** Overlay com spinner + texto cobre o card
- **Concluído:** Overlay desaparece, conteúdo opaco volta ao normal

---

### 4. Loading em Formulários

#### Pattern HTML:
```html
<form hx-post="/settings/clinica/update"
      hx-indicator="#form-loader"
      aria-busy="false">
  <input type="text" name="nome_fantasia" class="form-control">

  <div class="form-actions">
    <button type="submit" class="btn btn-primary">
      <span class="btn-text">Salvar Alterações</span>
      <span class="htmx-indicator">{% include 'utils/_spinner.html' %}</span>
    </button>

    <div id="form-loader" class="form-loading-banner htmx-indicator">
      {% include 'utils/_spinner.html' %}
      <span>Salvando configurações...</span>
    </div>
  </div>
</form>
```

#### CSS:
```css
.form-loading-banner {
  display: none;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-info-bg);
  border: 1px solid var(--color-info-border);
  border-radius: var(--border-radius-medium);
  color: var(--color-info-text);
  margin-top: var(--space-3);
}

.htmx-request .form-loading-banner {
  display: flex;
}
```

---

## 🔧 Customização

### Tamanhos de Spinner:
```html
<!-- Pequeno (12px) - para badges, textos inline -->
{% include 'utils/_spinner.html' with spinner_size='sm' %}

<!-- Médio (16px) - padrão para botões -->
{% include 'utils/_spinner.html' %}

<!-- Grande (24px) - para overlays, cards -->
{% include 'utils/_spinner.html' with spinner_size='lg' %}
```

### Cores:
```html
<!-- Herda cor do contexto (padrão) -->
<button class="btn btn-primary">
  <span class="htmx-indicator">{% include 'utils/_spinner.html' %}</span>
</button>

<!-- Cor customizada via CSS -->
<span class="htmx-indicator" style="color: var(--color-success);">
  {% include 'utils/_spinner.html' %}
</span>
```

### Texto de Loading:
```html
<!-- Com texto -->
<span class="htmx-indicator">
  {% include 'utils/_spinner.html' %}
  <span class="loading-text">Processando...</span>
</span>

<!-- Sem texto (apenas ícone) -->
<span class="htmx-indicator">
  {% include 'utils/_spinner.html' %}
</span>
```

---

## 📐 CSS Completo (Referência)

### Global (`global.css`):
```css
/* Spinner animation */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinner {
  animation: spin 0.8s linear infinite;
  will-change: transform;
}

.spinner-sm { width: 12px; height: 12px; }
.spinner-lg { width: 24px; height: 24px; }

/* HTMX indicators */
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { display: inline-flex; }

/* Desabilitar interação durante request */
.htmx-request { pointer-events: none; }
.htmx-request .btn-text { display: none; }
```

### Settings (`settings.css`):
```css
/* Loading overlay para cards */
.loading-overlay {
  display: none;
  position: absolute;
  inset: 0;
  background: rgba(var(--color-surface-card-rgb), 0.95);
  z-index: 10;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: var(--space-2);
}

.htmx-request .loading-overlay { display: flex; }
.htmx-request .card-content {
  opacity: 0.3;
  pointer-events: none;
}

/* Loading banner para formulários */
.form-loading-banner {
  display: none;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-info-bg);
  border: 1px solid var(--color-info-border);
  border-radius: var(--border-radius-medium);
  color: var(--color-info-text);
  margin-top: var(--space-3);
}

.htmx-request .form-loading-banner { display: flex; }
```

---

## 🎯 Exemplos de Uso no EchoDent

### 1. Botão de Salvar (Settings):
```html
<button class="btn btn-primary" hx-post="{{ url_for('settings_bp.clinica_update') }}">
  <span class="btn-text">Salvar Configurações</span>
  <span class="htmx-indicator">{% include 'utils/_spinner.html' %}</span>
</button>
```

### 2. Teste de API (Integrações):
```html
<button class="btn btn-outline-secondary"
        hx-post="{{ url_for('settings_bp.integrations_test', api='BRASILAPI') }}"
        hx-target="#test-result">
  <span class="btn-text">Testar Conexão</span>
  <span class="htmx-indicator">{% include 'utils/_spinner.html' %}</span>
</button>
```

### 3. Carregamento de Tabela (Tratamentos):
```html
<div class="card" hx-get="{{ url_for('tratamentos_bp.list') }}"
     hx-trigger="load" hx-indicator="this">
  <div class="loading-overlay">
    {% include 'utils/_spinner.html' with spinner_size='lg' %}
    <p class="loading-text">Carregando catálogo...</p>
  </div>
  <div class="card-content">
    <table class="table">...</table>
  </div>
</div>
```

### 4. Upload de Logo (com preview):
```html
<form hx-post="{{ url_for('settings_bp.upload_logo') }}"
      hx-encoding="multipart/form-data"
      hx-indicator="#upload-loader">
  <input type="file" name="logo" accept="image/*">

  <button type="submit" class="btn btn-primary">
    <span class="btn-text">Upload</span>
    <span class="htmx-indicator">{% include 'utils/_spinner.html' %}</span>
  </button>

  <div id="upload-loader" class="htmx-indicator loading-text">
    Enviando arquivo...
  </div>
</form>
```

---

## ✅ Checklist de Implementação

- [x] Criar `app/templates/utils/_spinner.html`
- [x] Adicionar CSS de spinner em `global.css`
- [x] Adicionar CSS de overlay/banner em `settings.css`
- [ ] Aplicar pattern em botões de Settings (Clínica, Tema, Admin)
- [ ] Aplicar pattern em botões de Tratamentos (Salvar, Ajustar Preços)
- [ ] Aplicar pattern em botões de Integrações (Salvar, Testar)
- [ ] Testar acessibilidade com screen reader (NVDA)

---

## 🔍 Troubleshooting

### Spinner não aparece:
1. Verificar se HTMX está carregado (`htmx.org` script tag)
2. Verificar se `.htmx-indicator` está dentro do elemento com `hx-*`
3. Verificar console do navegador (erros de HTMX)

### Spinner não desaparece:
1. Verificar se o servidor está retornando resposta (200/204)
2. Verificar se `hx-swap` está configurado corretamente
3. Checar se há erros JavaScript bloqueando HTMX

### Overlay cobre conteúdo permanentemente:
1. Verificar se `.loading-overlay` tem `position: absolute`
2. Verificar se container pai tem `position: relative`
3. Checar se HTMX removeu `.htmx-request` após resposta

---

## 📚 Referências

- **HTMX Indicators:** https://htmx.org/attributes/hx-indicator/
- **CSS Animations:** https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations
- **ARIA Busy:** https://www.w3.org/TR/wai-aria-1.1/#aria-busy

---

**Fim da Documentação**

*Sistema implementado seguindo princípios de simplicidade do AGENTS.MD.*
