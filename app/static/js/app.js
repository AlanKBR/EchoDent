// EchoDent App JS — shared behaviors (no inline JS)
(function () {
  const doc = document;

  function qs(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function qsa(sel, ctx) { return (ctx || doc).querySelectorAll(sel); }

  const overlay = qs('#error-modal');
  const messageEl = qs('#error-modal-message');
  const textEl = qs('#error-modal-text');
  const copyBtnSelector = '#copy-error-btn';
  let autoDismissTimer = null;

  function showErrorModal(message) {
    if (!overlay) return;
    if (messageEl) messageEl.textContent = String(message || 'Ocorreu um erro inesperado.');
    overlay.classList.add('is-visible');

    // Auto-dismiss after 7s
    if (autoDismissTimer) clearTimeout(autoDismissTimer);
    autoDismissTimer = setTimeout(() => {
      hideErrorModal();
    }, 7000);
  }

  function hideErrorModal() {
    if (!overlay) return;
    overlay.classList.remove('is-visible');
  }

  // Expose globally for optional manual calls
  window.EchoDent = window.EchoDent || {};
  window.EchoDent.showErrorModal = showErrorModal;
  window.EchoDent.hideErrorModal = hideErrorModal;

  // --- Global Search: prevenir autofoco/auto-complete em F5 ---
  function blurAndClearGlobalSearch() {
    try {
      const input = qs('.global-search-input');
      const results = qs('#global-search-results');
      if (!input) return;
      if (doc.activeElement === input) input.blur();
      // Limpa valor e dropdown para evitar requisições automáticas
      input.value = '';
      if (results) results.innerHTML = '';
      // Bloqueia autofill de credenciais até interação explícita
      input.setAttribute('readonly', 'readonly');
    } catch (_) {}
  }

  // Em reload (F5) alguns navegadores restauram foco/valor
  doc.addEventListener('DOMContentLoaded', () => {
    try {
      const nav = performance.getEntriesByType && performance.getEntriesByType('navigation');
      const isReload = Array.isArray(nav) && nav[0] && nav[0].type === 'reload';
      if (isReload) blurAndClearGlobalSearch();
      // Fallback: segundo tick para casos de restauração tardia
      setTimeout(() => {
        const input = qs('.global-search-input');
        if (input && doc.activeElement === input) blurAndClearGlobalSearch();
      }, 100);
    } catch (_) {}
  });

  // pageshow cobre bfcache (voltar/avançar) que pode restaurar foco
  window.addEventListener('pageshow', () => {
    try {
      const input = qs('.global-search-input');
      if (input && doc.activeElement === input) blurAndClearGlobalSearch();
    } catch (_) {}
  });

  // Ativar edição somente após interação explícita (pointer/focus)
  doc.addEventListener('pointerdown', (e) => {
    const input = e.target.closest('.global-search-input');
    if (input) input.removeAttribute('readonly');
  });
  doc.addEventListener('focusin', (e) => {
    const input = e.target.closest('.global-search-input');
    if (input) input.removeAttribute('readonly');
  });

  // Close on overlay click or [data-close-modal]
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      const isBackdrop = e.target === overlay;
      const isCloseBtn = e.target.closest('[data-close-modal]');
      if (isBackdrop || isCloseBtn) hideErrorModal();
    });
  }

  // htmx error hook (event listener works regardless of load order)
  doc.body.addEventListener('htmx:responseError', (evt) => {
    try {
      const xhr = evt && evt.detail && evt.detail.xhr;
      let msg = 'Falha na requisição.';
      if (xhr) {
        msg += ` Código ${xhr.status}`;
        const raw = xhr.responseText || '';
        // Inject raw server log/text into modal <pre>
        if (textEl) textEl.textContent = raw;
        // Also extract a concise title if present for the header message
        if (raw) {
          const m = raw.match(/<title[^>]*>(.*?)<\/title>/i);
          msg += ': ' + (m ? m[1] : String(raw).substring(0, 140));
        }
      }
      showErrorModal(msg);
    } catch (_) {
      showErrorModal('Erro desconhecido ao processar resposta.');
    }
  });

  // --- Início: Lógica de Prevenção de Saída Suja (Regra 8) ---
  // B1: Flag Global
  window.isFormDirty = false;

  // B2: Acionadores (Set Flag)
  doc.body.addEventListener('input', function (event) {
    if (event.target && event.target.closest && event.target.closest('form')) {
      window.isFormDirty = true;
    }
  });

  // B3: Reset da Flag (Após salvar com sucesso)
  doc.body.addEventListener('htmx:afterRequest', function (event) {
    const detail = event && event.detail;
    const req = detail && detail.requestConfig;
    const verb = req && req.verb ? String(req.verb).toUpperCase() : '';
    const isWrite = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(verb);
    if (isWrite) {
      if (!detail || !detail.failed) {
        window.isFormDirty = false;
      }
    }
  });

  // B4: A Trava (O Guarda) — antes de requisições HTMX
  doc.body.addEventListener('htmx:beforeRequest', function (event) {
    try {
      if (!window.isFormDirty) return;
      const elt = event && event.detail && event.detail.elt;
      if (!elt) return;

      // Permite submissões de formulário (o usuário está tentando salvar)
      if (elt.closest && elt.closest('form')) return;

      const confirmExit = window.confirm(
        'Você possui alterações não salvas. Deseja realmente sair e descartar as alterações?'
      );
      if (!confirmExit) {
        event.preventDefault();
        return;
      }
      // Usuário confirmou saída: reset flag para permitir a navegação
      window.isFormDirty = false;
    } catch (_) {
      // Em caso de erro na checagem, não bloquear a navegação
    }
  });
  // --- Fim: Lógica de Prevenção de Saída Suja ---

  // --- Início: Validações e Máscaras de Formulários (Fase 1.1) ---

  /**
   * Aplica máscara de CNPJ: 00.000.000/0000-00
   */
  function maskCNPJ(value) {
    return value
      .replace(/\D/g, '') // Remove não-dígitos
      .replace(/^(\d{2})(\d)/, '$1.$2') // 00.
      .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3') // 00.000.
      .replace(/\.(\d{3})(\d)/, '.$1/$2') // 00.000.000/
      .replace(/(\d{4})(\d)/, '$1-$2') // 00.000.000/0000-00
      .slice(0, 18); // Limita ao tamanho máximo
  }

  /**
   * Valida formato de CNPJ (apenas formato, sem dígito verificador)
   */
  function validateCNPJ(cnpj) {
    const cleaned = cnpj.replace(/\D/g, '');
    return cleaned.length === 14 && /^\d{14}$/.test(cleaned);
  }

  /**
   * Aplica máscara de CEP: 00000-000
   */
  function maskCEP(value) {
    return value
      .replace(/\D/g, '')
      .replace(/^(\d{5})(\d)/, '$1-$2')
      .slice(0, 9);
  }

  /**
   * Valida formato de CEP
   */
  function validateCEP(cep) {
    const cleaned = cep.replace(/\D/g, '');
    return cleaned.length === 8 && /^\d{8}$/.test(cleaned);
  }

  /**
   * Valida email usando pattern HTML5
   */
  function validateEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
  }

  /**
   * Aplica validação visual (adiciona classes .is-valid ou .is-invalid)
   */
  function applyValidationState(input, isValid) {
    input.classList.remove('is-valid', 'is-invalid');
    if (input.value.trim() === '') return; // Não validar campos vazios
    input.classList.add(isValid ? 'is-valid' : 'is-invalid');
  }

  // Event listener para campos CNPJ
  doc.addEventListener('DOMContentLoaded', () => {
    qsa('[data-validate="cnpj"]').forEach(input => {
      // Aplicar máscara durante digitação
      input.addEventListener('input', (e) => {
        e.target.value = maskCNPJ(e.target.value);
      });

      // Validar ao perder foco
      input.addEventListener('blur', (e) => {
        const isValid = validateCNPJ(e.target.value);
        applyValidationState(e.target, isValid);
      });
    });

    // Event listener para campos CEP
    qsa('[data-validate="cep"]').forEach(input => {
      // Aplicar máscara durante digitação
      input.addEventListener('input', (e) => {
        e.target.value = maskCEP(e.target.value);
      });

      // Validar ao perder foco
      input.addEventListener('blur', (e) => {
        const isValid = validateCEP(e.target.value);
        applyValidationState(e.target, isValid);
      });
    });

    // Event listener para campos Email
    qsa('[data-validate="email"]').forEach(input => {
      input.addEventListener('blur', (e) => {
        const isValid = validateEmail(e.target.value);
        applyValidationState(e.target, isValid);
      });
    });
  });

  // --- Fim: Validações e Máscaras de Formulários ---

  // --- Início: Sistema de Toasts (Fase 1.2) ---

  /**
   * Auto-dismiss de toasts após 5 segundos
   * Escuta HTMX afterSwap para toasts OOB
   */
  doc.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target && e.detail.target.id === 'toast-container') {
      const toasts = e.detail.target.querySelectorAll('[data-toast]');
      toasts.forEach((toast) => {
        if (!toast.dataset.toastInitialized) {
          toast.dataset.toastInitialized = 'true';
          setTimeout(() => {
            toast.style.animation = 'toast-slide-out 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
          }, 5000);
        }
      });
    }
  });

  // Animação de saída
  const style = doc.createElement('style');
  style.textContent = `
    @keyframes toast-slide-out {
      from { opacity: 1; transform: translateX(0); }
      to { opacity: 0; transform: translateX(100%); }
    }
  `;
  doc.head.appendChild(style);

  // Delegated click para fechar toast manualmente
  doc.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('[data-toast-close]');
    if (closeBtn) {
      const toast = closeBtn.closest('[data-toast]');
      if (toast) {
        toast.style.animation = 'toast-slide-out 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
      }
    }
  });

  /**
   * Função global para criar toasts via JavaScript (opcional)
   * window.EchoDent.showToast('Mensagem', 'success')
   */
  if (!window.EchoDent) window.EchoDent = {};
  window.EchoDent.showToast = function(mensagem, tipo = 'info') {
    const container = qs('#toast-container');
    if (!container) {
      console.warn('Toast container não encontrado. Adicione <div id="toast-container"></div> ao base.html');
      return;
    }

    const iconMap = {
      success: '✅',
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌'
    };

    const toast = doc.createElement('div');
    toast.className = `toast toast-${tipo}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    toast.setAttribute('data-toast', '');
    toast.innerHTML = `
      <span class="toast-icon" aria-hidden="true">${iconMap[tipo] || 'ℹ️'}</span>
      <span class="toast-message">${mensagem}</span>
      <button type="button" class="toast-close" aria-label="Fechar" data-toast-close>×</button>
    `;

    container.insertBefore(toast, container.firstChild);

    // Auto-dismiss
    setTimeout(() => {
      toast.style.animation = 'toast-slide-out 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  };

  // --- Fim: Sistema de Toasts ---

  // --- Início: CEP Autocomplete via BrasilAPI (Fase 1.3) ---

  /**
   * Busca CEP na BrasilAPI e preenche campos de endereço
   * Usa localStorage para cache offline-first
   */
  async function autocompleteCEP(cepInput) {
    const cep = cepInput.value.replace(/\D/g, '');

    if (cep.length !== 8) return;

    // Tentar cache primeiro (offline-first)
    const cacheKey = `cep_${cep}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
      try {
        const data = JSON.parse(cached);
        fillAddressFields(data);
        if (window.EchoDent && window.EchoDent.showToast) {
          window.EchoDent.showToast('📍 Endereço preenchido (cache)', 'success');
        }
        return;
      } catch (_) {
        localStorage.removeItem(cacheKey);
      }
    }

    // Buscar na API
    try {
      const response = await fetch(`https://brasilapi.com.br/api/cep/v2/${cep}`);

      if (!response.ok) {
        if (window.EchoDent && window.EchoDent.showToast) {
          window.EchoDent.showToast('⚠️ CEP não encontrado', 'warning');
        }
        return;
      }

      const data = await response.json();

      // Normalizar estrutura da BrasilAPI
      const normalized = {
        street: data.street || '',
        neighborhood: data.neighborhood || '',
        city: data.city || '',
        state: data.state || ''
      };

      // Preencher campos
      fillAddressFields(normalized);

      // Cachear resposta
      localStorage.setItem(cacheKey, JSON.stringify(normalized));

      if (window.EchoDent && window.EchoDent.showToast) {
        window.EchoDent.showToast('✅ Endereço preenchido automaticamente', 'success');
      }

    } catch (err) {
      console.error('Erro ao buscar CEP:', err);
      if (window.EchoDent && window.EchoDent.showToast) {
        window.EchoDent.showToast('❌ Erro ao buscar CEP. Verifique sua conexão.', 'error');
      }
    }
  }

  /**
   * Preenche campos de endereço com dados do CEP
   */
  function fillAddressFields(data) {
    const fields = {
      logradouro: data.street,
      bairro: data.neighborhood,
      cidade: data.city,
      estado: data.state
    };

    Object.keys(fields).forEach(fieldName => {
      const field = qs(`#${fieldName}`);
      if (field && fields[fieldName]) {
        field.value = fields[fieldName];
        // Trigger input event para marcar formulário como dirty
        field.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  }

  // Event listener para campos CEP com autocomplete
  doc.addEventListener('DOMContentLoaded', () => {
    qsa('[data-cep-autocomplete]').forEach(input => {
      input.addEventListener('blur', (e) => {
        autocompleteCEP(e.target);
      });
    });
  });

  // --- Fim: CEP Autocomplete ---

  // --- Início: Preview de Logos via FileReader (Fase 1.4) ---

  /**
   * Event listener para preview de logos antes do upload
   */
  doc.addEventListener('DOMContentLoaded', () => {
    qsa('[data-logo-preview]').forEach(input => {
      input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Validar tamanho (máx 2MB conforme spec)
        if (file.size > 2 * 1024 * 1024) {
          if (window.EchoDent && window.EchoDent.showToast) {
            window.EchoDent.showToast('⚠️ Logo não pode exceder 2MB', 'warning');
          }
          e.target.value = ''; // Limpar input
          return;
        }

        // Validar tipo
        if (!file.type.startsWith('image/')) {
          if (window.EchoDent && window.EchoDent.showToast) {
            window.EchoDent.showToast('⚠️ Arquivo deve ser uma imagem', 'warning');
          }
          e.target.value = '';
          return;
        }

        // Gerar preview
        const reader = new FileReader();
        const logoType = e.target.getAttribute('data-logo-preview');

        reader.onload = (ev) => {
          const previewImg = qs(`[data-preview-img="${logoType}"]`);
          if (previewImg) {
            previewImg.src = ev.target.result;
            previewImg.classList.remove('hidden');
          }
        };

        reader.onerror = () => {
          if (window.EchoDent && window.EchoDent.showToast) {
            window.EchoDent.showToast('❌ Erro ao carregar imagem', 'error');
          }
        };

        reader.readAsDataURL(file);
      });
    });
  });

  // --- Fim: Preview de Logos ---

  // --- Início: Modal de Confirmação Destrutiva (Fase 1.5) ---

  /**
   * Event listeners para modais de confirmação
   */
  doc.addEventListener('DOMContentLoaded', () => {
    // Delegated: Habilitar botão de confirmação apenas quando checkbox marcado
    doc.addEventListener('change', (e) => {
      if (e.target.matches('[data-confirm-checkbox]')) {
        const modal = e.target.closest('[data-modal-confirm]');
        if (modal) {
          const confirmBtn = modal.querySelector('[data-confirm-btn]');
          if (confirmBtn) {
            confirmBtn.disabled = !e.target.checked;
          }
        }
      }
    });

    // Delegated: Fechar modal ao clicar no backdrop ou botão cancelar
    doc.addEventListener('click', (e) => {
      const dismissTrigger = e.target.closest('[data-modal-dismiss]');
      if (dismissTrigger) {
        const modal = dismissTrigger.closest('[data-modal-confirm]');
        if (modal) {
          modal.remove();
        }
      }
    });
  });

  // Escutar evento HTMX afterSwap para detectar modais OOB
  doc.body.addEventListener('htmx:afterSwap', (e) => {
    const modal = qs('[data-modal-confirm]');
    if (modal && !modal.dataset.initialized) {
      modal.dataset.initialized = 'true';
      // Focus no checkbox para acessibilidade
      const checkbox = modal.querySelector('[data-confirm-checkbox]');
      if (checkbox) {
        setTimeout(() => checkbox.focus(), 100);
      }
    }
  });

  // --- Fim: Modal de Confirmação Destrutiva ---

  // --- Início: Fechamento de Modal HTMX (Passo 2 - Feature A) ---

  /**
   * Escutar evento customizado "closeModal" emitido via HX-Trigger
   * para fechar modais no #modal-container
   */
  doc.body.addEventListener('closeModal', () => {
    const container = qs('#modal-container');
    if (container) {
      container.innerHTML = '';
    }
  });

  /**
   * Auto-aplicar classe .is-visible quando modal for injetado
   * no #modal-container via HTMX
   */
  doc.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target && e.detail.target.id === 'modal-container') {
      const modalOverlay = e.detail.target.querySelector('.modal-overlay');
      if (modalOverlay) {
        // Usar requestAnimationFrame para garantir que o DOM foi atualizado
        requestAnimationFrame(() => {
          modalOverlay.classList.add('is-visible');
        });
      }
    }
  });

  /**
   * Delegated: Fechar modal ao clicar em [data-close-modal] dentro de modais
   * dinâmicos carregados no #modal-container
   */
  doc.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('[data-close-modal]');
    if (closeBtn) {
      const modalContainer = qs('#modal-container');
      const modalOverlay = e.target.closest('.modal-overlay');
      // Se clicou no botão dentro de um modal overlay, fechar
      if (modalOverlay && modalContainer && modalContainer.contains(modalOverlay)) {
        modalContainer.innerHTML = '';
      }
    }
  });

  // --- Fim: Fechamento de Modal HTMX ---

  // --- Início: Busca Global - Fechar ao clicar fora ---

  /**
   * Fechar dropdown de busca global quando clicar fora dele
   */
  doc.addEventListener('click', (e) => {
    const searchWrapper = qs('.global-search-wrapper');
    const searchResults = qs('#global-search-results');

    if (!searchWrapper || !searchResults) return;

    // Se clicou fora do wrapper da busca E há resultados visíveis
    if (!searchWrapper.contains(e.target) && searchResults.innerHTML.trim() !== '') {
      searchResults.innerHTML = '';
      // Limpar o input também quando fechar ao clicar fora
      const searchInput = qs('.global-search-input');
      if (searchInput) {
        searchInput.value = '';
        searchInput.setAttribute('readonly', 'readonly');
      }
    }
  });

  /**
   * Limpar busca global ao pressionar Escape
   */
  doc.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const searchResults = qs('#global-search-results');
      const searchInput = qs('.global-search-input');

      if (searchResults && searchResults.innerHTML.trim() !== '') {
        searchResults.innerHTML = '';
        if (searchInput) {
          searchInput.value = '';
          searchInput.blur();
          searchInput.setAttribute('readonly', 'readonly');
        }
      }
    }
  });

  // --- Fim: Busca Global ---

  async function copyErrorToClipboard() {
    try {
      if (!textEl) return;
      const text = textEl.innerText || '';
      await navigator.clipboard.writeText(text);
      const btn = qs(copyBtnSelector);
      if (btn) {
        const original = btn.textContent;
        btn.textContent = 'Copiado!';
        setTimeout(() => { btn.textContent = original || 'Copiar Erro'; }, 2000);
      }
    } catch (_) {
      // best-effort: ignore copy failures silently
    }
  }

  // Delegated click for copy button
  doc.addEventListener('click', (e) => {
    const copyBtn = e.target.closest(copyBtnSelector);
    if (copyBtn) {
      e.preventDefault();
      copyErrorToClipboard();
    }
  });

  // Removed legacy document modal handlers (v2.0) — now using dedicated /documentos panel

  // Autocomplete picker for patients: delegate clicks on results
  doc.addEventListener('click', (e) => {
    const pick = e.target.closest('[data-paciente-pick]');
    if (!pick) return;
    try {
      const id = pick.getAttribute('data-id');
      const name = pick.getAttribute('data-name');
      const hidden = qs('#paciente_id_hidden');
      const input = qs('#paciente_busca');
      const results = qs('#autocomplete-results');
      if (hidden) hidden.value = id || '';
      if (input) input.value = name || '';
      if (results) results.innerHTML = '';
    } catch (_) {}
  });

  // Delegated handler: remove closest .item-plano-row (replaces inline onclick)
  doc.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-remove-row]');
    if (btn) {
      const row = btn.closest('.item-plano-row');
      if (row) row.remove();
    }
  });

  // Sidebar + User menu toggles
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize sidebar state from localStorage
    try {
      const saved = localStorage.getItem('echodent_sidebar_expanded');
      if (saved === 'true') {
        document.body.classList.add('sidebar-expanded');
      }
    } catch (_) {}

    // Toggle Sidebar expand/collapse
    const sidebarToggle = qs('#sidebar-toggle-btn');
    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', () => {
        document.body.classList.toggle('sidebar-expanded');
        // Persist state
        try {
          localStorage.setItem('echodent_sidebar_expanded', String(document.body.classList.contains('sidebar-expanded')));
        } catch (_) {}
      });
    }
  });
})();
