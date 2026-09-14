/* The Constructor map stays mounted while HTMX updates the executive figures. */
(() => {
  'use strict';
  let selectedRegion = '';
  const frame = document.getElementById('yandex-country-frame');
  if (frame) {
    const wide = frame.getAttribute('src');
    const compact = frame.dataset.compactSrc || wide;
    // Both URLs come from Constructor. Their saved views fit the two widths.
    new ResizeObserver(() => {
      const source = frame.clientWidth < 480 ? compact : wide;
      if (frame.getAttribute('src') !== source) frame.src = source;
    }).observe(frame);
  }
  document.addEventListener('click', event => {
    if (event.target.closest('[data-yandex-reset]') && frame) {
      frame.src = frame.getAttribute('src');
    }
  });
  document.addEventListener('change', event => {
    if (event.target.id === 'yandex-region-choice') selectedRegion = event.target.value;
  });
  document.addEventListener('htmx:oobAfterSwap', () => {
    const select = document.getElementById('yandex-region-choice');
    if (select && [...select.options].some(option => option.value === selectedRegion)) select.value = selectedRegion;
  });
  document.addEventListener('submit', event => {
    if (!event.target.matches('[data-region-navigation]')) return;
    const href = event.target.querySelector('select').value;
    if (!/^\/hudud\/\d+$/.test(href)) return;
    event.preventDefault();
    location.assign(href);
  });
})();
