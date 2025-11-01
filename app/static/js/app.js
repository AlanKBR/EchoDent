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

  // Delegated click: close the document modal when clicking [data-close-modal]
  doc.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('[data-close-modal]');
    if (!closeBtn) return;
    try {
      const modalDoc = qs('#modal-documento');
      if (modalDoc && modalDoc.contains(closeBtn)) {
        e.preventDefault();
        modalDoc.innerHTML = '';
        modalDoc.classList.remove('active');
      }
    } catch (_) {
      // fail silent
    }
  });

  // Close the document modal on Escape key
  doc.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    try {
      const modalDoc = qs('#modal-documento');
      if (modalDoc && modalDoc.innerHTML.trim() !== '') {
        e.preventDefault();
        modalDoc.innerHTML = '';
        modalDoc.classList.remove('active');
      }
    } catch (_) {}
  });

  // Optional backdrop-like close: clicking on the container (outside modal card)
  doc.addEventListener('click', (e) => {
    try {
      const modalDoc = qs('#modal-documento');
      if (!modalDoc || modalDoc.innerHTML.trim() === '') return;
      const clickedInsideModalDoc = e.target === modalDoc;
      if (clickedInsideModalDoc) {
        modalDoc.innerHTML = '';
        modalDoc.classList.remove('active');
      }
    } catch (_) {}
  });

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
