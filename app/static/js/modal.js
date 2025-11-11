'use strict';
(function () {
  function closeModal(el) {
    const modal = el.closest('.modal-overlay');
    if (modal) modal.remove();
  }

  function onDocKeyDown(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
    }
  }

  function enableConfirmIfChecked(container) {
    const checkbox = container.querySelector('#confirma-ajuste');
    const btn = container.querySelector('#btn-confirmar-ajuste');
    if (checkbox && btn) {
      btn.disabled = !checkbox.checked;
      checkbox.addEventListener('change', () => {
        btn.disabled = !checkbox.checked;
      });
    }
  }

  function autofocusPercentual(container) {
    const inputPercentual = container.querySelector('#percentual');
    if (inputPercentual) {
      setTimeout(() => inputPercentual.focus(), 100);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', (e) => {
      const t = e.target;
      if (t && t.matches('[data-close-modal]')) {
        e.preventDefault();
        closeModal(t);
      }
    });

    document.addEventListener('keydown', onDocKeyDown);
  });

  // Initialize modal behaviors when content is swapped in
  document.body.addEventListener('htmx:afterSwap', (evt) => {
    const target = evt.target;
    if (!target) return;
    target.querySelectorAll('.modal-overlay').forEach(container => {
      enableConfirmIfChecked(container);
      autofocusPercentual(container);
    });
  });
})();
