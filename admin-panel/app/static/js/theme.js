/* Runs before styles load so the saved theme is present on the first paint. */
(() => {
  'use strict';
  const key = 'aq-theme';
  const root = document.documentElement;
  const normalize = value => value === 'dark' ? 'dark' : 'light';

  function apply(value) {
    const theme = normalize(value);
    root.dataset.theme = theme;
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      const label = theme === 'dark' ? button.dataset.lightLabel : button.dataset.darkLabel;
      button.setAttribute('aria-label', label);
      button.title = label;
    });
  }

  let initial = 'light';
  try { initial = normalize(localStorage.getItem(key)); } catch (_) { /* Storage may be disabled. */ }
  apply(initial);

  document.addEventListener('DOMContentLoaded', () => apply(root.dataset.theme), { once: true });
  document.addEventListener('click', event => {
    if (!(event.target instanceof Element) || !event.target.closest('[data-theme-toggle]')) return;
    const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    apply(theme);
    try { localStorage.setItem(key, theme); } catch (_) { /* Switching still works for this page. */ }
  });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) apply(event.newValue);
  });
})();
