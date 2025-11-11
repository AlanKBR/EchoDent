'use strict';
(function () {
  function scheduleAutoDismiss(el) {
    if (!el) return;
    const timeout = parseInt(el.getAttribute('data-timeout') || '30000', 10);
    setTimeout(() => {
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    }, timeout);
  }

  function wireDismiss(el) {
    if (!el) return;
    el.querySelectorAll('.js-dismiss-on-click').forEach(btn => {
      btn.addEventListener('click', () => {
        const toast = btn.closest('.toast-with-undo');
        if (toast) toast.remove();
      });
    });
    el.querySelectorAll('.js-dismiss-toast').forEach(btn => {
      btn.addEventListener('click', () => {
        const toast = btn.closest('.toast-with-undo');
        if (toast) toast.remove();
      });
    });
  }

  function initExisting() {
    document.querySelectorAll('.toast-with-undo').forEach(toast => {
      wireDismiss(toast);
      scheduleAutoDismiss(toast);
    });
  }

  document.addEventListener('DOMContentLoaded', initExisting);

  document.body.addEventListener('htmx:afterSwap', (evt) => {
    const swapped = evt.target;
    if (!swapped) return;
    swapped.querySelectorAll('.toast-with-undo').forEach(toast => {
      wireDismiss(toast);
      scheduleAutoDismiss(toast);
    });
  });
})();
