'use strict';
(function () {
  let undoTimeoutId = null;
  let countdownIntervalId = null;

  function clearTimers() {
    if (undoTimeoutId) clearTimeout(undoTimeoutId);
    if (countdownIntervalId) clearInterval(countdownIntervalId);
    undoTimeoutId = null;
    countdownIntervalId = null;
  }

  function hideUndoToast() {
    const toast = document.getElementById('undoToast');
    if (!toast) return;
    toast.classList.add('hiding');
    setTimeout(() => {
      toast.classList.add('hidden');
      toast.classList.remove('hiding');
    }, 300);
    clearTimers();
  }

  function startCountdown(durationSeconds) {
    const timerSpan = document.getElementById('undoTimer');
    const progressBar = document.getElementById('undoProgressBar');
    let timeLeft = durationSeconds;
    if (timerSpan) timerSpan.textContent = String(timeLeft);

    countdownIntervalId = setInterval(() => {
      timeLeft -= 1;
      if (timerSpan) timerSpan.textContent = String(timeLeft);
      if (progressBar) {
        const pct = Math.max(0, Math.min(100, (timeLeft / durationSeconds) * 100));
        progressBar.style.width = pct + '%';
      }
      if (timeLeft <= 0) {
        clearTimers();
        hideUndoToast();
      }
    }, 1000);

    undoTimeoutId = setTimeout(() => {
      hideUndoToast();
    }, durationSeconds * 1000);
  }

  function initUndoToastBehavior() {
    const toast = document.getElementById('undoToast');
    if (!toast) return;

    const dismissButton = document.getElementById('dismissToast');
    if (dismissButton) {
      dismissButton.addEventListener('click', hideUndoToast, { once: true });
    }

    const progressBar = document.getElementById('undoProgressBar');
    if (progressBar) {
      // reset and animate from 100% -> 0%
      progressBar.style.transition = 'none';
      progressBar.style.width = '100%';
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          progressBar.style.transition = 'width 30s linear';
          progressBar.style.width = '0%';
        });
      });
    }

    // Begin countdown at 30s by default
    startCountdown(30);
  }

  // Public API to show toast with server-provided data
  window.showUndoToast = function (data) {
    // data can include message/previous_state/record_id depending on usage
    const toast = document.getElementById('undoToast');
    if (!toast) return;
    toast.classList.remove('hidden');

    // If the undo button should POST back via HTMX (response variant), we don't override it here.
    // For variants that expect fetch rollback, you can extend this module as needed.

    clearTimers();
    initUndoToastBehavior();
  };

  // Bootstrap: read data-undo from hidden div if present
  document.addEventListener('DOMContentLoaded', () => {
    const bootstrap = document.getElementById('undoToastBootstrap');
    if (bootstrap) {
      const raw = bootstrap.getAttribute('data-undo');
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (parsed) {
            window.showUndoToast(parsed);
          }
        } catch (e) {
          console.error('Invalid undo data:', e);
        }
      }
    }
  });

  // When HTMX swaps in the toast response, initialize behavior
  document.body.addEventListener('htmx:afterSwap', (evt) => {
    // If the swapped content includes #undoToast, init behavior
    const target = evt.target;
    if (!target) return;
    const toast = target.querySelector ? target.querySelector('#undoToast') : null;
    if (toast) {
      // Ensure visible
      toast.classList.remove('hidden');
      clearTimers();
      initUndoToastBehavior();
    }
  });
})();
