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
