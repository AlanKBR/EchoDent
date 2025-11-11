'use strict';
(function () {
  function showSection(id) {
    document.querySelectorAll('.admin-section').forEach(section => {
      section.style.display = 'none';
    });
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
  }

  function wireNav() {
    document.querySelectorAll('.admin-subnav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.admin-subnav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const sectionId = link.getAttribute('data-section');
        if (sectionId) showSection(sectionId);
      });
    });
  }

  function wireConfirm() {
    document.querySelectorAll('form[data-confirm-message], form[onsubmit]').forEach(form => {
      const message = form.getAttribute('data-confirm-message') || form.getAttribute('onsubmit');
      if (!message) return;
      form.addEventListener('submit', (e) => {
        // If onsubmit contains confirm('...'), attempt to extract message
        let msg = message;
        const m = /confirm\(['\"](.+?)['\"]\)/.exec(message);
        if (m && m[1]) msg = m[1];
        if (!window.confirm(msg)) {
          e.preventDefault();
        }
      });
      // Clean inline handler to avoid double prompts
      form.removeAttribute('onsubmit');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    wireNav();
    wireConfirm();
  });
})();
