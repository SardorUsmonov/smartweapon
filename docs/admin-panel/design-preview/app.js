const themeButtons = document.querySelectorAll('.theme-controls button');
themeButtons.forEach(button => button.addEventListener('click', () => {
  document.documentElement.dataset.theme = button.dataset.theme;
  themeButtons.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
}));
let rows = [];
let selected = null;
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const search = document.querySelector('#region-search');
function renderRows() {
  const term = search.value.trim().toLocaleLowerCase();
  const visible = rows.filter(row => row.name.toLocaleLowerCase().includes(term));
  document.querySelector('#region-rows').innerHTML = visible.length ? visible.map(row => `<tr class="${row.id === selected ? 'selected' : ''}"><td><span class="region-number">${String(rows.indexOf(row)+1).padStart(2,'0')}</span><button class="region-name" data-select="${row.id}">${escapeHTML(row.name)}</button></td><td>${row.armories}</td><td>${row.cabinets}</td><td>${row.issued}</td><td class="${row.signals ? 'has-signal' : ''}">${row.signals || '—'}</td><td><span class="connection ${row.offline ? 'offline' : ''}"><i></i>${row.offline ? row.offline+' oflayn' : 'Onlayn'}</span></td><td><a href="http://127.0.0.1:8080/hudud/${row.id}" target="_blank" rel="noopener" aria-label="${escapeHTML(row.name)} tafsiloti">↗</a></td></tr>`).join('') : '<tr><td colspan="7">Bu nomdagi hudud topilmadi.</td></tr>';
  document.querySelector('#row-count').textContent = visible.length + ' hudud';
}
function selectRegion(id) {
  selected = id;
  const row = rows.find(row => row.id === id);
  document.querySelectorAll('#map a').forEach(link => {
    const active = Number(link.dataset.select) === id;
    link.classList.toggle('active', active);
    link.setAttribute('aria-pressed', String(active));
  });
  const selection = document.querySelector('#selection');
  selection.querySelector('.selection-label').textContent = row ? row.name : 'Barcha hududlar';
  selection.querySelector('strong').textContent = row ? `${row.armories} qurolxona · ${row.cabinets} yacheyka · ${row.issued} xodimlardagi qurol` : 'Respublika bo‘yicha umumiy ko‘rinish';
  const link = selection.querySelector('a');
  link.href = row ? `http://127.0.0.1:8080/hudud/${row.id}` : '#regions';
  link.innerHTML = row ? 'Hududni ochish <span>↗</span>' : 'Hududlar jadvali <span>↓</span>';
  if (row) {link.target = '_blank';link.rel = 'noopener';} else {link.removeAttribute('target');}
  document.querySelector('#clear-selection').hidden = !row;
  renderRows();
}
document.addEventListener('click', event => {
  const target = event.target.closest('[data-select]');
  if (!target) return;
  event.preventDefault();
  selectRegion(Number(target.dataset.select));
});
search.addEventListener('input', renderRows);
document.querySelector('#clear-selection').addEventListener('click', () => selectRegion(null));
Promise.all([fetch('regions.json').then(response => response.json()), fetch('map.json').then(response => response.json())]).then(([data, geo]) => {
  rows = data;
  const mapRows = new Map(rows.map(row => [row.code, row]));
  let svg = `<svg viewBox="0 0 ${geo.w} ${geo.h}" role="group" aria-label="O‘zbekiston hududlari">`;
  for (const [code, shape] of Object.entries(geo.regions)) {
    const row = mapRows.get(code);
    if (!row) continue;
    svg += `<a href="#selection" data-select="${row.id}" role="button" aria-pressed="false" aria-label="${escapeHTML(row.name)}"><path d="${shape.d}"><title>${escapeHTML(row.name)}</title></path>`;
    if ([10,13,9,7,2].includes(row.id)) svg += `<text x="${shape.cx}" y="${shape.cy+4}" font-size="17" text-anchor="middle">${escapeHTML(shape.short)}</text>`;
    svg += '</a>';
  }
  document.querySelector('#map').innerHTML = svg + '</svg>';
  renderRows();
}).catch(() => {document.querySelector('#map').textContent = 'Xarita ma’lumoti yuklanmadi.';document.querySelector('#region-rows').innerHTML='<tr><td colspan="7">Ma’lumot yuklanmadi. Sahifani lokal server orqali oching.</td></tr>';});
