# EchoDent - Proposta de Melhorias UX/UI para Configurações e Novos Módulos

**Versão:** 2.0 (Revisada)
**Data:** Novembro 2025
**Autor:** Arquiteto de Agentes IA
**Status:** Proposta Refinada

---

## 📋 Sumário Executivo

Este documento apresenta melhorias de **UX**, **UI** e **novas funcionalidades** para o EchoDent, focando em:
1. Melhorias no módulo de **Configurações** (`/settings`)
2. **Novo módulo "Tratamentos"** (gestão do catálogo clínico)
3. **Centralização de APIs** (backend + UI)

### Princípios de Design:
- ✅ **Simplicidade acima de tudo** - Sem dependências desnecessárias
- ✅ **Offline-first** - Funciona em rede local sem internet
- ✅ **HTMX-first** - Sem frameworks JS pesados
- ✅ **CSS global** - Respeitar design tokens existentes
- ✅ **Validações simples** - Client + server, sem libs externas

---

## 🔍 1. Análise do Estado Atual

### 1.1. Estrutura Existente

#### Configurações (`/settings`):
- **`[Clínica]`** - Dados da clínica, endereço, horários, logos
- **`[Tema]`** - Cores primária/secundária (✅ **funcionando**)
- **`[Usuário]`** - Preferências pessoais, cor da agenda
- **`[Admin]`** - Usuários, dev logs, global settings, backups (placeholder)

#### Dark Mode:
- ✅ **JÁ IMPLEMENTADO** via `[data-theme-mode="dark"]` em `global.css`
- ✅ Toggle funcional na sidebar (`theme-toggle.js` + localStorage)
- ✅ Variáveis CSS completas para light/dark

#### Pontos Fortes:
✅ Arquitetura limpa (blueprints → services → templates)
✅ Design system consistente (design tokens em `global.css`)
✅ HTMX para interatividade
✅ Soft-delete e logs de auditoria (backend)

#### Pontos de Melhoria:
⚠️ Validação de campos apenas server-side (sem feedback visual inline)
⚠️ CEP sem autocomplete (BrasilAPI mencionado em AGENTS.MD mas não usado em Settings)
⚠️ Logos sem preview antes do upload
⚠️ Ações destrutivas sem confirmação
⚠️ Falta gestão de **Procedimentos/Tratamentos** (tabela existe mas sem UI)
⚠️ Tokens de API espalhados (sem painel unificado)

---

## 🎨 2. Melhorias de UX (User Experience)

### 2.1. Validação em Tempo Real (Simples)

**Objetivo:** Feedback imediato sem bibliotecas externas.

#### 2.1.1. Validação Client-Side (Vanilla JS)
**Campos a validar:**
- **CNPJ:** Formato `00.000.000/0000-00` (apenas validação de formato, sem dígito verificador)
- **CEP:** Formato `00000-000`
- **Email:** Atributo `type="email"` do HTML5
- **Telefone:** Máscara dinâmica via JavaScript puro

**Implementação:**
```javascript
// global.js (adicionar)
document.querySelectorAll('[data-validate="cnpj"]').forEach(input => {
  input.addEventListener('blur', () => {
    const valid = /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/.test(input.value);
    input.classList.toggle('is-invalid', !valid);
    input.classList.toggle('is-valid', valid);
  });
});
```

**CSS (já existe em global.css):**
```css
.is-invalid { border-color: var(--color-danger-border); }
.is-valid { border-color: var(--color-success-border, #10b981); }
```

---

#### 2.1.2. Estados de Carregamento
**Objetivo:** Feedback visual durante operações assíncronas.

**Implementação (já parcialmente existente):**
- `pointer-events: none` durante `.htmx-request` (✅ já em `global.css`)
- **Adicionar:** Spinner SVG inline + texto "Salvando..."

**Template pattern:**
```html
<button class="btn btn-primary" hx-post="/settings/clinica/update">
  <span class="btn-text">Salvar</span>
  <span class="btn-spinner htmx-indicator">
    <svg class="spinner" width="16" height="16" viewBox="0 0 16 16">...</svg>
  </span>
</button>
```

---

#### 2.1.3. Confirmação de Ações Destrutivas
**Problema:** Desativar usuário, purgar logs ocorre sem confirmação.

**Solução:**
- Modal HTMX com confirmação dupla (checkbox + botão)
- Mensagem clara das consequências

**Implementação:**
```html
<!-- Fragmento HTMX retornado pelo servidor -->
<div class="modal-confirm" role="dialog" aria-labelledby="modal-title">
  <div class="modal-overlay" data-dismiss-modal></div>
  <div class="modal-content">
    <h3 id="modal-title">⚠️ Desativar Usuário?</h3>
    <p>Usuário <strong>dr_joao</strong> perderá acesso imediato. Dados históricos serão preservados (soft-delete).</p>
    <label>
      <input type="checkbox" required> Entendo que esta ação não pode ser desfeita
    </label>
    <div class="modal-actions">
      <button class="btn btn-secondary" data-dismiss-modal>Cancelar</button>
      <button class="btn btn-danger" hx-post="/settings/admin/users/5/deactivate">
        Confirmar Desativação
      </button>
    </div>
  </div>
</div>
```

---

#### 2.1.4. Undo/Rollback de Configurações
**Objetivo:** Permitir desfazer alterações recentes.

**Solução:**
- Salvar estado anterior em campo JSONB `previous_state` (ClinicaInfo, GlobalSetting)
- Toast com botão "Desfazer" (disponível por 30s após salvar)
- Log de auditoria registra rollback

**Workflow:**
1. Admin altera cor primária → Salvo
2. Toast: "✅ Tema atualizado. [Desfazer] (30s)"
3. Click em "Desfazer" → Rollback imediato
4. Se timeout → `previous_state` mantido para recuperação manual (Admin → Auditoria)

---

### 2.2. Feedback Visual Aprimorado

#### 2.2.1. Toast Notifications Consistentes
**Objetivo:** Feedback unificado para todas as ações.

**Tipos:**
- ✅ **Sucesso:** "Configurações salvas com sucesso"
- ℹ️ **Informação:** "Tema restaurado para padrão"
- ⚠️ **Atenção:** "Logo não pode exceder 2MB"
- ❌ **Erro:** "Falha ao salvar: CNPJ inválido"

**Implementação:**
```html
<!-- templates/components/_toast.html -->
<div class="toast toast-{{ tipo }}" role="alert" hx-swap-oob="afterbegin:#toast-container">
  <span class="toast-icon">{{ icon }}</span>
  <span class="toast-message">{{ mensagem }}</span>
  <button class="toast-close" aria-label="Fechar">×</button>
</div>
```

**JavaScript (global.js):**
```javascript
// Auto-dismiss em 5s
document.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target.id === 'toast-container') {
    setTimeout(() => {
      e.detail.target.querySelector('.toast')?.remove();
    }, 5000);
  }
});
```

---

#### 2.2.2. Preview de Logos Antes/Depois do Upload
**Problema:** Usuário não vê preview antes de submeter.

**Solução:**
- Thumbnail da logo atual (se existir)
- Preview live ao selecionar arquivo (FileReader API)
- Botão "Remover Logo" para limpar

**Implementação:**
```javascript
// global.js
document.querySelectorAll('[data-logo-preview]').forEach(input => {
  input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const preview = input.closest('.logo-upload-card').querySelector('[data-preview-img]');
      preview.src = ev.target.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  });
});
```

**Template:**
```html
<div class="logo-upload-card">
  <div class="logo-preview">
    <img data-preview-img src="{{ info.logo_cabecalho_path or '/static/img/placeholder-logo.svg' }}" alt="Preview">
  </div>
  <input type="file" name="logo_cabecalho" accept="image/*" data-logo-preview>
  <button type="button" class="btn btn-outline-danger btn-sm" hx-delete="/settings/clinica/logo/cabecalho">
    Remover Logo
  </button>
</div>
```

---

### 2.3. Modo de Edição Inline (Admin Panel)
**Objetivo:** Editar usuários sem sair da página.

**Solução:**
- Click no nome do usuário → Linha vira formulário inline
- Campos editáveis: Nome completo, email, CRO, cor
- HTMX retorna apenas HTML da linha atualizada (`hx-swap="outerHTML"`)

**Template:**
```html
<!-- Modo leitura -->
<tr id="user-row-5" hx-get="/settings/admin/users/5/edit" hx-swap="outerHTML">
  <td>dr_joao</td>
  <td>Dr. João Silva</td>
  <td><span class="badge badge-dentista">DENTISTA</span></td>
  <td><button class="btn btn-sm btn-danger">Desativar</button></td>
</tr>

<!-- Modo edição (retornado pelo servidor) -->
<tr id="user-row-5">
  <td>dr_joao</td>
  <td><input type="text" name="nome_completo" value="Dr. João Silva" class="form-control-sm"></td>
  <td><select name="role" class="form-select-sm">...</select></td>
  <td>
    <button class="btn btn-sm btn-success" hx-post="/settings/admin/users/5/update">✓</button>
    <button class="btn btn-sm btn-secondary" hx-get="/settings/admin/users/5">✗</button>
  </td>
</tr>
```

---

## 🎨 3. Melhorias de UI (User Interface)

### 3.1. Iconografia Padronizada

**Problema:** Sistema já usa ícones SVG (Tabler), mas alguns faltam.

**Solução:**
- **Manter Tabler Icons** (já usados na sidebar)
- Garantir consistência semântica:
  - Clínica: `building`
  - Tema: `palette`
  - Usuário: `user`
  - Admin: `shield`
  - Tratamentos: `stethoscope` ou `medical-cross`
  - Salvar: `check`
  - Cancelar: `x`
  - Upload: `upload`

**Implementação:**
- Helper Jinja reutilizável: `{% include 'utils/_icon.html' with icon='check' %}`

---

### 3.2. Componentes Visuais Novos

#### 3.2.1. Card de Status da Clínica
**Objetivo:** Guiar admin na configuração inicial.

**Localização:** Topo da aba `[Clínica]`

**Mockup:**
```
┌─────────────────────────────────────────────────────┐
│ 📊 Status da Configuração                           │
├─────────────────────────────────────────────────────┤
│ ✅ Dados empresariais completos                     │
│ ✅ Endereço cadastrado                              │
│ ⚠️  Logos faltando (Cabeçalho, Favicon)            │
│ ✅ Horário de funcionamento definido                │
│                                                     │
│ Completude: ████████░░ 80%                          │
└─────────────────────────────────────────────────────┘
```

**Implementação:**
- Service calcula completude (`clinica_service.get_config_completeness()`)
- Template renderiza dinamicamente com base nos campos preenchidos

---

#### 3.2.2. Timeline de Alterações (Admin)
**Objetivo:** Visibilidade de mudanças em configurações.

**Localização:** Nova sub-aba em `[Admin]` → "Auditoria de Configurações"

**Mockup:**
```
┌─────────────────────────────────────────────────────┐
│ 📜 Histórico de Alterações (Últimas 10)             │
├─────────────────────────────────────────────────────┤
│ 🕐 14:32 - admin - Alterou cor primária            │
│ 🕐 12:15 - admin - Upload de logo cabeçalho        │
│ 🕐 11:50 - dr_joao - Alterou cor da agenda         │
│                                        [Ver Todos]  │
└─────────────────────────────────────────────────────┘
```

**Implementação:**
- Query na tabela `LogAuditoria` filtrada por operações em Settings
- Link "Ver Todos" → Página completa com filtros (usuário, data, tabela)

---

## 🚀 4. Novas Funcionalidades

### 4.1. CEP Autocomplete (BrasilAPI)

**Contexto:** Mencionado em AGENTS.MD mas não implementado no formulário de Clínica.

**Funcionalidade:**
- Input de CEP dispara busca ao perder foco (`blur`)
- Preenche automaticamente: logradouro, bairro, cidade, estado
- Cache local para offline-first (salvar em `GlobalSetting`)

**Implementação:**
```javascript
// global.js
document.getElementById('cep')?.addEventListener('blur', async (e) => {
  const cep = e.target.value.replace(/\D/g, '');
  if (cep.length !== 8) return;

  try {
    // Tentar cache primeiro
    const cached = localStorage.getItem(`cep_${cep}`);
    const data = cached ? JSON.parse(cached) : await (await fetch(`https://brasilapi.com.br/api/cep/v2/${cep}`)).json();

    document.getElementById('logradouro').value = data.street || '';
    document.getElementById('bairro').value = data.neighborhood || '';
    document.getElementById('cidade').value = data.city || '';
    document.getElementById('estado').value = data.state || '';

    // Cachear resposta
    localStorage.setItem(`cep_${cep}`, JSON.stringify(data));

    showToast('✅ Endereço preenchido automaticamente', 'success');
  } catch (err) {
    showToast('⚠️ CEP não encontrado', 'warning');
  }
});
```

---

### 4.2. Centralização de APIs (Backend + UI)

**Problema:** Tokens de API espalhados (InverTexto para feriados, futuras integrações).

#### 4.2.1. Backend: `api_keys_service.py`

**Funcionalidade:**
- CRUD de chaves de API (sem criptografia, texto plano com sanitização)
- Teste de conexão para cada API

**Implementação:**
```python
# app/services/api_keys_service.py
from app.models import GlobalSetting, db
from app.utils.sanitization import sanitizar_input
from flask import current_app
import requests

def get_api_key(key_name: str) -> str | None:
    """Retorna chave de API (ex: 'BRASILAPI_TOKEN')."""
    setting = db.session.get(GlobalSetting, f"API_{key_name}")
    return setting.value if setting else None

def set_api_key(key_name: str, value: str) -> bool:
    """Define chave de API. Retorna True se sucesso."""
    try:
        sanitized = sanitizar_input(value.strip()) if value else None
        setting = db.session.get(GlobalSetting, f"API_{key_name}")
        if setting:
            setting.value = sanitized
        else:
            setting = GlobalSetting(key=f"API_{key_name}", value=sanitized)
            db.session.add(setting)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar API key: {e}")
        return False

def test_api_connection(api_name: str) -> dict:
    """Testa conexão com API. Retorna {'status': 'ok'|'error', 'message': '...'}"""
    if api_name == 'BRASILAPI_FERIADOS':
        token = get_api_key('INVERTEXTO_TOKEN')
        if not token:
            return {'status': 'error', 'message': 'Token não configurado'}
        try:
            resp = requests.get(
                'https://api.invertexto.com/v1/holidays/2025',
                headers={'Authorization': f'Bearer {token}'},
                timeout=5
            )
            return {'status': 'ok', 'message': f'Conexão OK (HTTP {resp.status_code})'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    return {'status': 'error', 'message': 'API não suportada'}
```

---

#### 4.2.2. UI: Nova Aba "Integrações" em Settings

**Localização:** `[Admin]` → Sub-navegação → "Integrações"

**Template:**
```html
<!-- templates/settings/integrations.html -->
{% extends "base.html" %}
{% block title %}Integrações{% endblock %}
{% block content %}
<div class="settings-container">
  {% set active_tab = 'admin' %}
  {% include "settings/_tabs.html" %}

  <div class="settings-content">
    <div class="settings-header">
      <h1>Integrações com APIs Externas</h1>
      <p class="text-muted">Configure chaves de API para serviços externos.</p>
    </div>

    <!-- BrasilAPI (Feriados) -->
    <form hx-post="{{ url_for('settings_bp.integrations_save') }}" hx-swap="outerHTML">
      <div class="card">
        <div class="card-header">
          <strong>📅 BrasilAPI (Feriados & CEP)</strong>
          <span class="badge badge-success">Ativa</span>
        </div>
        <div class="card-body">
          <input type="hidden" name="api_name" value="INVERTEXTO_TOKEN">
          <label for="invertexto_token" class="form-label">Token InverTexto (opcional - para feriados):</label>
          <input type="password" id="invertexto_token" name="api_value"
                 value="{{ api_keys.get('INVERTEXTO_TOKEN', '') }}"
                 class="form-control" placeholder="Token JWT...">
          <div class="form-text">CEP funciona sem token. Feriados exigem token gratuito do InverTexto.</div>

          <div class="mt-3">
            <button type="submit" class="btn btn-primary">Salvar</button>
            <button type="button" class="btn btn-outline-secondary"
                    hx-post="{{ url_for('settings_bp.integrations_test', api='BRASILAPI_FERIADOS') }}"
                    hx-target="#test-result">
              Testar Conexão
            </button>
          </div>
          <div id="test-result" class="mt-2"></div>
        </div>
      </div>
    </form>

    <!-- Gateway de Pagamento (Futuro) -->
    <div class="card mt-4">
      <div class="card-header">
        <strong>💳 Gateway de Pagamento</strong>
        <span class="badge badge-secondary">Inativa</span>
      </div>
      <div class="card-body">
        <p class="text-muted">Em desenvolvimento. Suporte futuro para Mercado Pago, PagSeguro, Stripe.</p>
      </div>
    </div>

  </div>
</div>
{% endblock %}
```

**Blueprint (`settings_bp.py`):**
```python
@settings_bp.route("/admin/integrations", methods=["GET"])
@login_required
@admin_required
def integrations():
    from app.services import api_keys_service
    api_keys = {
        'INVERTEXTO_TOKEN': api_keys_service.get_api_key('INVERTEXTO_TOKEN')
    }
    return render_template("settings/integrations.html", api_keys=api_keys)

@settings_bp.route("/admin/integrations/save", methods=["POST"])
@login_required
@admin_required
def integrations_save():
    from app.services import api_keys_service
    api_name = request.form.get('api_name')
    api_value = request.form.get('api_value')

    success = api_keys_service.set_api_key(api_name, api_value)
    if success:
        flash("✅ Chave de API salva com sucesso", "success")
    else:
        flash("❌ Erro ao salvar chave de API", "error")

    return redirect(url_for('settings_bp.integrations'))

@settings_bp.route("/admin/integrations/test/<api>", methods=["POST"])
@login_required
@admin_required
def integrations_test(api: str):
    from app.services import api_keys_service
    result = api_keys_service.test_api_connection(api)

    # Retorna fragmento HTML para HTMX
    return render_template("settings/_integration_test_result.html", result=result)
```

**Template de resultado (`_integration_test_result.html`):**
```html
<div class="alert alert-{{ 'success' if result.status == 'ok' else 'danger' }}">
  {{ result.message }}
</div>
```

---

### 4.3. Página "Tratamentos" (NOVA ENTRADA NA SIDEBAR)

**Objetivo:** Gestão do catálogo clínico (`ProcedimentoMestre`) com CRUD completo.

#### 4.3.1. Arquitetura

**Localização:** Nova entrada na sidebar (entre "Financeiro" e "Configurações")

**Permissões:**
- **ADMIN:** CRUD completo, ajuste de preços em massa
- **DENTISTA:** Read-only (consulta para orçamentos)
- **SECRETARIA:** Read-only (consulta para atendimento)

**Categorias Fixas (Especialidades Odontológicas):**
1. Clínica Geral
2. Ortodontia
3. Endodontia
4. Periodontia
5. Prótese
6. Implantodontia
7. Odontopediatria
8. Cirurgia Bucomaxilofacial
9. Estética/Cosmética
10. Outros

**OBS:** Categorias são **FIXAS** (Enum no backend). Admin não pode criar novas.

---

#### 4.3.2. Funcionalidades

##### A) CRUD de Tratamentos

**Campos:**
- Nome do tratamento (ex: "Limpeza Completa")
- Código (ex: "LIMP001" - opcional, para TUSS/CBHPM)
- Categoria (select com 10 especialidades)
- Preço padrão (decimal)
- Descrição (text, opcional)
- Ativo (boolean - soft-delete)

**UI:**
- Tabela com filtros (categoria, nome, ativo/inativo)
- Edição inline (similar ao Admin de usuários)
- Botão "Novo Tratamento" (modal ou inline)

---

##### B) Ajuste de Preços em Massa

**Funcionalidade:**
- Admin pode aplicar **ajuste percentual** a todos os preços (ex: +5% para inflação)
- **Filtros opcionais:** Por categoria, por faixa de preço
- **Preview:** Mostrar preços atuais vs. novos antes de confirmar
- **Confirmação dupla:** Checkbox + modal
- **Log de auditoria:** Registrar ajuste (`LogAuditoria`)

**Mockup:**
```
┌─────────────────────────────────────────────────────┐
│ 📊 Ajuste de Preços em Massa                        │
├─────────────────────────────────────────────────────┤
│ Ajuste: [+5%] [Aplicar a:] [Todas categorias ▼]   │
│                                                     │
│ Preview (10 primeiros):                             │
│ Limpeza Completa: R$ 150,00 → R$ 157,50           │
│ Clareamento:      R$ 800,00 → R$ 840,00           │
│ ...                                                 │
│                                                     │
│ ⚠️ Este ajuste afetará 47 tratamentos              │
│ [ ] Confirmo que revisei os novos valores          │
│                                                     │
│ [Cancelar] [Aplicar Ajuste]                        │
└─────────────────────────────────────────────────────┘
```

---

#### 4.3.3. Implementação

**Model (já existe em `models.py`):**
```python
class ProcedimentoMestre(db.Model):
    __tablename__ = "procedimento_mestre"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    codigo = db.Column(db.String(50), nullable=True)
    categoria = db.Column(db.String(100), nullable=False)  # Enum no service
    preco_padrao = db.Column(db.Numeric(10, 2), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())
```

**Service (`procedimentos_service.py`):**
```python
# app/services/procedimentos_service.py
from app.models import ProcedimentoMestre, LogAuditoria, db
from app.utils.sanitization import sanitizar_input
from decimal import Decimal
from flask import current_app

CATEGORIAS_FIXAS = [
    "Clínica Geral",
    "Ortodontia",
    "Endodontia",
    "Periodontia",
    "Prótese",
    "Implantodontia",
    "Odontopediatria",
    "Cirurgia Bucomaxilofacial",
    "Estética/Cosmética",
    "Outros"
]

def list_tratamentos(categoria: str = None, ativo: bool = True):
    """Lista tratamentos com filtros opcionais."""
    q = db.session.query(ProcedimentoMestre)
    if categoria:
        q = q.filter(ProcedimentoMestre.categoria == categoria)
    if ativo is not None:
        q = q.filter(ProcedimentoMestre.is_active == ativo)
    return q.order_by(ProcedimentoMestre.categoria, ProcedimentoMestre.nome).all()

def create_tratamento(data: dict, user_id: int) -> ProcedimentoMestre | None:
    """Cria novo tratamento."""
    try:
        proc = ProcedimentoMestre(
            nome=sanitizar_input(data['nome']),
            codigo=sanitizar_input(data.get('codigo', '')),
            categoria=data['categoria'],  # Validar contra CATEGORIAS_FIXAS
            preco_padrao=Decimal(data['preco_padrao']),
            descricao=sanitizar_input(data.get('descricao', ''))
        )
        db.session.add(proc)
        db.session.commit()

        # Log de auditoria
        log = LogAuditoria(
            user_id=user_id,
            tabela='procedimento_mestre',
            operacao='CREATE',
            registro_id=proc.id,
            changes_json={'novo': data}
        )
        db.session.add(log)
        db.session.commit()

        return proc
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar tratamento: {e}")
        return None

def ajustar_precos_em_massa(percentual: float, categoria: str = None, user_id: int = None) -> dict:
    """
    Ajusta preços de tratamentos em massa.

    Args:
        percentual: Percentual de ajuste (ex: 5.0 para +5%, -3.0 para -3%)
        categoria: Filtro opcional por categoria
        user_id: ID do usuário que executou (para auditoria)

    Returns:
        {'sucesso': True, 'afetados': 10, 'preview': [...]}
    """
    try:
        q = db.session.query(ProcedimentoMestre).filter(ProcedimentoMestre.is_active == True)
        if categoria:
            q = q.filter(ProcedimentoMestre.categoria == categoria)

        tratamentos = q.all()
        afetados = 0
        preview = []

        for proc in tratamentos:
            preco_antigo = proc.preco_padrao
            preco_novo = preco_antigo * (1 + Decimal(percentual) / 100)
            preco_novo = preco_novo.quantize(Decimal('0.01'))  # Arredondar para 2 casas

            proc.preco_padrao = preco_novo
            afetados += 1

            if len(preview) < 10:  # Preview dos 10 primeiros
                preview.append({
                    'nome': proc.nome,
                    'preco_antigo': float(preco_antigo),
                    'preco_novo': float(preco_novo)
                })

        db.session.commit()

        # Log de auditoria
        log = LogAuditoria(
            user_id=user_id,
            tabela='procedimento_mestre',
            operacao='UPDATE_MASSA',
            registro_id=None,
            changes_json={
                'percentual': percentual,
                'categoria': categoria,
                'afetados': afetados
            }
        )
        db.session.add(log)
        db.session.commit()

        return {'sucesso': True, 'afetados': afetados, 'preview': preview}
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao ajustar preços: {e}")
        return {'sucesso': False, 'erro': str(e)}
```

**Blueprint (`tratamentos_bp.py`):**
```python
# app/blueprints/tratamentos_bp.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.services import procedimentos_service
from app.utils.decorators import admin_required

tratamentos_bp = Blueprint("tratamentos_bp", __name__, url_prefix="/tratamentos")

@tratamentos_bp.route("/", methods=["GET"])
@login_required
def index():
    """Página principal de tratamentos (todos os roles podem ver)."""
    categoria = request.args.get('categoria')
    ativo = request.args.get('ativo', 'true') == 'true'

    tratamentos = procedimentos_service.list_tratamentos(categoria, ativo)
    categorias = procedimentos_service.CATEGORIAS_FIXAS

    return render_template(
        "tratamentos/index.html",
        tratamentos=tratamentos,
        categorias=categorias,
        is_admin=current_user.is_admin
    )

@tratamentos_bp.route("/create", methods=["POST"])
@login_required
@admin_required
def create():
    """Criar novo tratamento (apenas admin)."""
    data = {
        'nome': request.form.get('nome'),
        'codigo': request.form.get('codigo'),
        'categoria': request.form.get('categoria'),
        'preco_padrao': request.form.get('preco_padrao'),
        'descricao': request.form.get('descricao')
    }

    proc = procedimentos_service.create_tratamento(data, current_user.id)
    if proc:
        flash("✅ Tratamento criado com sucesso", "success")
    else:
        flash("❌ Erro ao criar tratamento", "error")

    return redirect(url_for('tratamentos_bp.index'))

@tratamentos_bp.route("/ajustar-precos", methods=["GET", "POST"])
@login_required
@admin_required
def ajustar_precos():
    """Ajuste de preços em massa (apenas admin)."""
    if request.method == "GET":
        # Renderiza modal de preview
        categorias = procedimentos_service.CATEGORIAS_FIXAS
        return render_template("tratamentos/ajustar_precos.html", categorias=categorias)

    # POST: Aplicar ajuste
    percentual = float(request.form.get('percentual', 0))
    categoria = request.form.get('categoria')
    confirmado = request.form.get('confirmado') == 'on'

    if not confirmado:
        flash("⚠️ Você precisa confirmar o ajuste", "warning")
        return redirect(url_for('tratamentos_bp.ajustar_precos'))

    resultado = procedimentos_service.ajustar_precos_em_massa(
        percentual, categoria, current_user.id
    )

    if resultado['sucesso']:
        flash(f"✅ {resultado['afetados']} tratamentos atualizados", "success")
    else:
        flash(f"❌ Erro: {resultado['erro']}", "error")

    return redirect(url_for('tratamentos_bp.index'))

@tratamentos_bp.route("/preview-ajuste", methods=["POST"])
@login_required
@admin_required
def preview_ajuste():
    """Retorna preview do ajuste (HTMX)."""
    percentual = float(request.form.get('percentual', 0))
    categoria = request.form.get('categoria')

    # Mock do preview (usar service real aqui)
    preview = procedimentos_service.get_preview_ajuste(percentual, categoria)

    return render_template("tratamentos/_preview_ajuste.html", preview=preview)
```

**Template Principal (`tratamentos/index.html`):**
```html
{% extends "base.html" %}
{% block title %}Tratamentos{% endblock %}
{% block content %}
<div class="tratamentos-container">
  <div class="page-header">
    <h1>Catálogo de Tratamentos</h1>
    {% if is_admin %}
    <div class="page-actions">
      <button class="btn btn-primary" hx-get="{{ url_for('tratamentos_bp.create') }}" hx-target="#modal-container">
        Novo Tratamento
      </button>
      <button class="btn btn-warning" hx-get="{{ url_for('tratamentos_bp.ajustar_precos') }}" hx-target="#modal-container">
        Ajustar Preços em Massa
      </button>
    </div>
    {% endif %}
  </div>

  <!-- Filtros -->
  <div class="filters">
    <select name="categoria" hx-get="{{ url_for('tratamentos_bp.index') }}" hx-trigger="change" hx-target=".tratamentos-table">
      <option value="">Todas as Categorias</option>
      {% for cat in categorias %}
      <option value="{{ cat }}">{{ cat }}</option>
      {% endfor %}
    </select>
  </div>

  <!-- Tabela de Tratamentos -->
  <div class="tratamentos-table">
    <table class="table">
      <thead>
        <tr>
          <th>Código</th>
          <th>Nome</th>
          <th>Categoria</th>
          <th>Preço</th>
          {% if is_admin %}<th>Ações</th>{% endif %}
        </tr>
      </thead>
      <tbody>
        {% for trat in tratamentos %}
        <tr>
          <td>{{ trat.codigo or '-' }}</td>
          <td>{{ trat.nome }}</td>
          <td><span class="badge badge-categoria">{{ trat.categoria }}</span></td>
          <td>R$ {{ "%.2f"|format(trat.preco_padrao) }}</td>
          {% if is_admin %}
          <td>
            <button class="btn btn-sm btn-secondary" hx-get="{{ url_for('tratamentos_bp.edit', id=trat.id) }}">Editar</button>
            <button class="btn btn-sm btn-danger" hx-delete="{{ url_for('tratamentos_bp.delete', id=trat.id) }}">Desativar</button>
          </td>
          {% endif %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<div id="modal-container"></div>
{% endblock %}
```

**Template de Ajuste (`tratamentos/ajustar_precos.html`):**
```html
<div class="modal" role="dialog">
  <div class="modal-overlay" data-dismiss-modal></div>
  <div class="modal-content">
    <h3>📊 Ajuste de Preços em Massa</h3>

    <form hx-post="{{ url_for('tratamentos_bp.ajustar_precos') }}">
      <div class="form-group">
        <label>Percentual de Ajuste:</label>
        <input type="number" name="percentual" step="0.1" value="5.0" class="form-control"
               hx-post="{{ url_for('tratamentos_bp.preview_ajuste') }}"
               hx-trigger="change"
               hx-target="#preview-container">
        <div class="form-text">Use valor positivo para aumento (5.0 = +5%) ou negativo para desconto (-3.0 = -3%)</div>
      </div>

      <div class="form-group">
        <label>Aplicar a:</label>
        <select name="categoria" class="form-select">
          <option value="">Todas as categorias</option>
          {% for cat in categorias %}
          <option value="{{ cat }}">{{ cat }}</option>
          {% endfor %}
        </select>
      </div>

      <div id="preview-container" class="mt-3">
        <!-- Preview será carregado aqui via HTMX -->
      </div>

      <div class="form-check mt-3">
        <input type="checkbox" name="confirmado" id="confirm-checkbox" required>
        <label for="confirm-checkbox">Confirmo que revisei os novos valores</label>
      </div>

      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" data-dismiss-modal>Cancelar</button>
        <button type="submit" class="btn btn-warning">Aplicar Ajuste</button>
      </div>
    </form>
  </div>
</div>
```

---

### 4.4. Logs de Auditoria Visíveis (Admin)

**Funcionalidade:**
- Listagem paginada de `LogAuditoria`
- Filtros: Usuário, data, tabela, operação
- Detalhamento: Modal com diff JSON (antes/depois)

**Localização:** `[Admin]` → Sub-navegação → "Auditoria"

**Implementação:**
- Rota: `/settings/admin/audit-logs`
- Query com paginação (Flask-SQLAlchemy `.paginate()`)
- Template com tabela sortável (HTMX)

---

## 📊 5. Roadmap de Implementação (Revisado)

### Fase 1: Fundação UX (PRIORIDADE ALTA - 2 semanas)

1. **Validação simples de campos** (CNPJ, CEP, email)
   - JavaScript puro, sem libs
   - Estimativa: 2 dias

2. **Loading states e spinners**
   - Aproveitando `.htmx-request` existente
   - Estimativa: 1 dia

3. **Sistema de toasts unificado**
   - Template `_toast.html` + auto-dismiss
   - Estimativa: 2 dias

4. **Confirmação de ações destrutivas**
   - Modal HTMX + checkbox duplo
   - Estimativa: 2 dias

5. **CEP Autocomplete (BrasilAPI)**
   - JavaScript + cache localStorage
   - Estimativa: 2 dias

6. **Preview de logos**
   - FileReader API
   - Estimativa: 2 dias

**Total:** 11 dias (~2 semanas)

---

### Fase 2: Página Tratamentos (PRIORIDADE ALTA - 2 semanas)

1. **CRUD de tratamentos**
   - Model, service, blueprint, templates
   - Estimativa: 4 dias

2. **Ajuste de preços em massa**
   - Modal de preview + confirmação + log
   - Estimativa: 3 dias

3. **Filtros e busca**
   - Por categoria, nome, ativo/inativo
   - Estimativa: 2 dias

4. **Edição inline**
   - Similar ao Admin de usuários
   - Estimativa: 2 dias

**Total:** 11 dias (~2 semanas)

---

### Fase 3: Centralização de APIs (PRIORIDADE MÉDIA - 1 semana)

1. **Backend: `api_keys_service.py`**
   - CRUD de chaves, teste de conexão
   - Estimativa: 2 dias

2. **UI: Aba "Integrações"**
   - Template + formulários
   - Estimativa: 2 dias

3. **Integração com BrasilAPI (feriados)**
   - Migrar token para novo sistema
   - Estimativa: 1 dia

**Total:** 5 dias (~1 semana)

---

### Fase 4: Polimento e Auditoria (PRIORIDADE MÉDIA - 1 semana)

1. **Logs de auditoria visíveis**
   - Listagem paginada + filtros + diff viewer
   - Estimativa: 3 dias

2. **Undo/Rollback de configs**
   - `previous_state` JSONB + toast com botão
   - Estimativa: 2 dias

3. **Card de status da clínica**
   - Cálculo de completude + UI
   - Estimativa: 1 dia

4. **Timeline de alterações**
   - Query em LogAuditoria + template
   - Estimativa: 1 dia

**Total:** 7 dias (~1 semana)

---

## 🎯 6. Matriz de Priorização (Revisada)

| Feature                           | Impacto | Esforço | Prioridade |
|-----------------------------------|---------|---------|------------|
| Validação em tempo real           | 🔥🔥🔥    | ⚡       | **ALTA**   |
| CEP Autocomplete (BrasilAPI)      | 🔥🔥🔥    | ⚡       | **ALTA**   |
| Confirmação de ações destrutivas  | 🔥🔥🔥    | ⚡       | **ALTA**   |
| Sistema de toasts                 | 🔥🔥      | ⚡       | **ALTA**   |
| Preview de logos                  | 🔥       | ⚡       | **ALTA**   |
| **Página Tratamentos (CRUD)**     | 🔥🔥🔥    | ⚡⚡      | **ALTA**   |
| **Ajuste de preços em massa**     | 🔥🔥🔥    | ⚡⚡      | **ALTA**   |
| Centralização de APIs (Backend)   | 🔥🔥      | ⚡       | **MÉDIA**  |
| Centralização de APIs (UI)        | 🔥       | ⚡       | **MÉDIA**  |
| Logs de auditoria visíveis        | 🔥🔥      | ⚡⚡      | **MÉDIA**  |
| Undo/Rollback de configs          | 🔥🔥      | ⚡⚡      | **MÉDIA**  |
| Edição inline (Admin)             | 🔥       | ⚡       | **BAIXA**  |
| Card de status da clínica         | 🔥       | ⚡       | **BAIXA**  |
| Timeline de alterações            | 🔥       | ⚡       | **BAIXA**  |

**Legenda:**
- **Impacto:** 🔥 (baixo), 🔥🔥 (médio), 🔥🔥🔥 (alto)
- **Esforço:** ⚡ (baixo - 1-2 dias), ⚡⚡ (médio - 3-4 dias), ⚡⚡⚡ (alto - 5+ dias)

---

## 📝 7. Considerações de Implementação

### 7.1. Alinhamento com AGENTS.MD

✅ **Offline-first:** BrasilAPI com cache localStorage, ícones locais
✅ **Robustez:** Validações client + server, transações atômicas, soft-delete
✅ **HTMX-first:** Zero SPA, toda interatividade via `hx-*`
✅ **CSS global:** Design tokens em `:root`, temas light/dark já funcionando
✅ **Simplicidade:** Validações em vanilla JS, sem libs pesadas
✅ **Atomicidade:** Todo service com `try/commit/rollback`
✅ **Log de auditoria:** Registrar mudanças críticas (ajuste preços, configs)

---

### 7.2. Segurança de Dados

**Tokens de API (sem criptografia):**
- ✅ Justificativa: Schema-per-tenant isolado, rede local, controle de acesso via `is_admin`
- ✅ Sanitização: Todo input passa por `sanitizar_input()`
- ✅ Auditoria: Mudanças em tokens registradas em `LogAuditoria`

**Validação:**
- ✅ Client-side: Feedback UX imediato
- ✅ Server-side: Camada obrigatória de segurança (nunca confiar no cliente)

---

### 7.3. Testes e Validação

Para cada feature:
1. **Testes manuais via MCP Browser** (verificar UI/UX)
2. **Testes de integração** (garantir HTMX retorna HTML correto)
3. **Testes de robustez** (validar atomicidade, soft-delete, sanitização)

---

## 🎬 8. Próximos Passos

1. ✅ **Revisar este documento** com o Líder de Tecnologia
2. **Priorizar Fase 1** (Fundação UX) para início imediato
3. **Criar tasks** no GitHub ou gerenciador de tarefas
4. **Iterar em sprints de 1 semana** com entregas incrementais

---

## 📚 9. Referências

- **AGENTS.MD** - Diretrizes de arquitetura do EchoDent
- **BrasilAPI** - https://brasilapi.com.br/docs
- **HTMX** - https://htmx.org/docs/
- **WCAG 2.1** - https://www.w3.org/WAI/WCAG21/quickref/
- **Tabler Icons** - https://tabler-icons.io/ (já em uso no projeto)

---

**Fim do Documento**

*Documento revisado removendo features descartadas (navegação teclado, mobile, backups auto, email, i18n) e adicionando Página Tratamentos + Centralização de APIs.*
