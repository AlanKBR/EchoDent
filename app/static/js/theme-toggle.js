(function(){
  const STORAGE_KEY = 'theme-mode';
  const docEl = document.documentElement;

  function applyTheme(mode) {
    // accept only 'light' or 'dark'
    const m = (mode === 'dark') ? 'dark' : 'light';
    docEl.setAttribute('data-theme-mode', m);
    try { localStorage.setItem(STORAGE_KEY, m); } catch (_) {}
  }

  function readStoredTheme() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (_) { return null; }
  }

  // Initialize as early as possible
  const stored = readStoredTheme();
  if (stored) {
    applyTheme(stored);
  } else {
    // Default to light; optionally respect prefers-color-scheme in future
    applyTheme('light');
  }

  // Expose toggle function
  window.toggleThemeMode = function toggleThemeMode() {
    const current = docEl.getAttribute('data-theme-mode') === 'dark' ? 'dark' : 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  };

  // Bind buttons with [data-theme-toggle]
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-theme-toggle]')
      .forEach(function(btn){ btn.addEventListener('click', window.toggleThemeMode); });
  });
})();