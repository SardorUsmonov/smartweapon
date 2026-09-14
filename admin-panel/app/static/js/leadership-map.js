/* Read-only leadership overview. All metrics come from the authenticated server snapshot. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const viewBox = '-28 -36 944 600';
  const positions = {
    'UZ-QR':[147,128], 'UZ-XO':[227,284], 'UZ-NW':[390,217], 'UZ-BU':[323,363],
    'UZ-SA':[466,371], 'UZ-QA':[457,452], 'UZ-SU':[535,496], 'UZ-JI':[529,302],
    'UZ-SI':[598,381], 'UZ-TO':[640,220], 'UZ-TK':[568,175], 'UZ-NG':[745,248],
    'UZ-AN':[825,302], 'UZ-FA':[746,382]
  };
  const leaderCodes = new Set(['UZ-SI','UZ-TO','UZ-TK','UZ-NG','UZ-AN','UZ-FA','UZ-XO']);
  const state = {selected:'all', zoomed:false, filtered:false, scroll:null, focus:null};
  let geometryPromise;
  function geometry() {
    if (!geometryPromise) geometryPromise = fetch('/static/data/uz_regions.json', {credentials:'same-origin'})
      .then(response => { if (!response.ok) throw new Error('Map geometry unavailable'); return response.json(); })
      .catch(error => { geometryPromise = null; throw error; });
    return geometryPromise;
  }
  function element(tag, attrs, parent, text) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    parent.appendChild(node);
    return node;
  }
  function isOverview(event) {
    return event.detail?.target?.id === 'executive-overview' || event.detail?.elt?.id === 'executive-overview';
  }
  function rememberPosition(root) {
    const scroller = root.closest('.main');
    state.scroll = scroller ? scroller.scrollTop : null;
    const focused = document.activeElement;
    state.focus = root.contains(focused) ? {
      id:focused.id || null,
      region:focused.dataset?.lmRegion || null,
      type:focused.classList?.contains('lm-face') ? 'path' : focused.classList?.contains('lm-label') ? 'g' : focused.tagName?.toLowerCase(),
      control:focused.hasAttribute?.('data-lm-zoom') ? 'data-lm-zoom' : focused.hasAttribute?.('data-lm-filter') ? 'data-lm-filter' : focused.hasAttribute?.('data-lm-reset') ? 'data-lm-reset' : null
    } : null;
  }
  async function mount(root) {
    if (root.dataset.lmMounted) return;
    root.dataset.lmMounted = 'loading';
    let data, strings, geo;
    try {
      data = JSON.parse(root.querySelector('[data-lm-data]').textContent);
      strings = JSON.parse(root.querySelector('[data-lm-strings]').textContent);
      geo = await geometry();
    } catch (_) {
      if (root.isConnected && strings) root.querySelector('[data-lm-map-fallback]').textContent = strings.mapUnavailable;
      root.dataset.lmMounted = 'failed';
      return;
    }
    if (!root.isConnected) return;
    const rows = data.regions.filter(row => geo.regions[row.code] && positions[row.code]);
    const byCode = new Map(rows.map(row => [row.code, row]));
    if (!byCode.has(state.selected)) { state.selected = 'all'; state.zoomed = false; }
    const svg = root.querySelector('[data-lm-map]');
    const picker = root.querySelector('#lm-region-picker');
    const zoom = root.querySelector('[data-lm-zoom]');
    const filter = root.querySelector('[data-lm-filter]');
    const number = value => value == null ? '—' : new Intl.NumberFormat('en-US').format(value).replaceAll(',', ' ');
    const stamp = value => {
      if (!value || !Number.isFinite(Date.parse(value))) return strings.noData;
      return new Intl.DateTimeFormat('en-GB', {timeZone:'Asia/Tashkent',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})
        .format(new Date(value)).replaceAll('/', '.').replace(',', ' ·');
    };
    const delta = (current, before) => current == null || before == null ? strings.noComparison : current === before ? strings.noChange : `${current > before ? '+' : '−'}${number(Math.abs(current - before))}`;
    const put = (key, value) => { const target = root.querySelector(`[data-lm="${key}"]`); if (target) target.textContent = value == null ? '—' : value; };
    const snapshot = root.querySelector('[data-lm-snapshot]');
    snapshot.textContent = `${stamp(data.asOf)} (UTC+5)`;
    root.querySelector('[data-lm-critical-change]').textContent = `${delta(data.totals.critical, data.previousTotals.critical)} · ${strings.previousDay}`;
    const staleCount = data.regions.filter(row => row.stale).length;
    const missingCount = data.regions.filter(row => row.updatedAt === null).length;
    const national = {...data.totals, code:'all', name:strings.national, previous:data.previousTotals,
      state:data.totals.critical ? 'critical' : data.totals.warning || data.totals.knownOffline ? 'warning' : missingCount || !data.totals.sites ? 'unknown' : 'stable'};
    // Controls only activate after geometry is ready; normal links remain a usable fallback.
    svg.hidden = false;
    svg.removeAttribute('hidden');
    root.querySelector('[data-lm-map-fallback]').hidden = true;
    root.querySelectorAll('[data-lm-js]').forEach(node => { node.hidden = false; });
    const defs = element('defs', {}, svg);
    const pattern = element('pattern', {id:'lm-no-data',width:8,height:8,patternUnits:'userSpaceOnUse',patternTransform:'rotate(35)'}, defs);
    element('rect', {width:8,height:8,fill:'var(--lm-map-unknown)'}, pattern);
    element('path', {d:'M0 0 V8',stroke:'var(--lm-unknown)','stroke-width':2}, pattern);
    const fullCountry = Object.values(geo.regions).map(region => region.d).join(' ');
    element('path', {d:fullCountry,class:'lm-country-shadow',transform:'translate(0 7)','fill-rule':'evenodd','aria-hidden':'true'}, svg);
    element('path', {d:fullCountry,class:'lm-country-context','fill-rule':'evenodd','aria-hidden':'true'}, svg);
    const faces = element('g', {}, svg), leaders = element('g', {'aria-hidden':'true'}, svg);
    const labelLayer = element('g', {}, svg), markers = element('g', {'aria-hidden':'true','pointer-events':'none'}, svg);
    const shapes = new Map(), labels = new Map();
    rows.forEach(row => {
      const shape = geo.regions[row.code], [x,y] = positions[row.code];
      const status = `${strings[row.state] || strings.unknown}${row.stale ? ` · ${strings.stale}` : ''}`;
      const path = element('path', {d:shape.d,class:`lm-face ${row.state}`,'data-lm-region':row.code,
        'fill-rule':'evenodd',tabindex:0,role:'button','aria-label':`${row.name}: ${status}`,'aria-pressed':'false'}, faces);
      element('title', {}, path, `${row.name} · ${status}`);
      shapes.set(row.code, path);
      if (leaderCodes.has(row.code)) element('path', {d:`M${shape.cx} ${shape.cy} L${x} ${y+6}`,class:'lm-leader','data-for':row.code}, leaders);
      const group = element('g', {class:'lm-label','data-lm-region':row.code,role:'button',tabindex:0,
        'aria-label':`${row.name} ${strings.details}`,'aria-pressed':'false'}, labelLayer);
      element('text', {x,y}, group, row.short);
      const bounds = group.getBBox();
      const hit = element('rect', {x:bounds.x-10,y:bounds.y-10,width:bounds.width+20,height:Math.max(40,bounds.height+20),class:'lm-label-hit',rx:4}, group);
      group.insertBefore(hit, group.firstChild);
      labels.set(row.code, group);
      if (row.critical || row.warning || row.offline || row.state === 'unknown') {
        const marker = element('g', {class:`lm-marker ${row.state}`,'data-for':row.code,transform:`translate(${shape.cx},${shape.cy})`}, markers);
        element('circle', {r:13}, marker);
        element('text', {x:0,y:0}, marker, row.state === 'unknown' ? '?' : (row.critical || 0)+(row.warning || 0) || '!');
      }
    });
    function fitZoom() {
      svg.classList.toggle('is-zoomed', state.zoomed);
      labels.forEach((group,code) => {
        group.style.display = '';
        const [x,y] = positions[code];
        group.setAttribute('transform', state.zoomed ? `translate(${x} ${y}) scale(.55) translate(${-x} ${-y})` : '');
      });
      if (!state.zoomed || state.selected === 'all') svg.setAttribute('viewBox', viewBox);
      else {
        const shape = shapes.get(state.selected).getBBox(), raw = labels.get(state.selected).getBBox();
        const [x,y] = positions[state.selected], scale = .55;
        const label = {x:x+(raw.x-x)*scale,y:y+(raw.y-y)*scale,width:raw.width*scale,height:raw.height*scale};
        const left = Math.min(shape.x,label.x)-28, top = Math.min(shape.y,label.y)-28;
        const width = Math.max(230,Math.max(shape.x+shape.width,label.x+label.width)-left+28);
        const height = Math.max(180,Math.max(shape.y+shape.height,label.y+label.height)-top+28);
        svg.setAttribute('viewBox', `${left} ${top} ${width} ${height}`);
      }
      labels.forEach((group,code) => { group.style.display = state.zoomed && code !== state.selected ? 'none' : ''; });
      svg.querySelectorAll('[data-for]').forEach(node => {
        node.style.display = state.zoomed && (node.dataset.for !== state.selected || node.classList.contains('lm-marker')) ? 'none' : '';
      });
      zoom.disabled = state.selected === 'all';
      zoom.setAttribute('aria-pressed', String(state.zoomed));
      zoom.setAttribute('aria-label', state.zoomed ? strings.zoomBackLabel : strings.zoomLabel);
      put('zoom-label', state.zoomed ? strings.zoomBack : strings.zoom);
    }
    function focusAlerts() {
      filter.setAttribute('aria-pressed', String(state.filtered));
      rows.forEach(row => shapes.get(row.code).classList.toggle('is-muted', state.filtered && row.state === 'stable' && !row.stale));
    }
    function revealDetails() {
      const panel = root.querySelector('.lm-details'), scroller = root.closest('.main');
      const rect = panel.getBoundingClientRect(), viewport = scroller ? scroller.getBoundingClientRect() : {top:0,bottom:window.innerHeight};
      if (rect.top < viewport.top || rect.top + 100 > viewport.bottom) {
        if (scroller) scroller.scrollTop += rect.top - viewport.top - 14;
        else panel.scrollIntoView({block:'start',behavior:'instant'});
        panel.focus({preventScroll:true});
      }
    }
    function updateLinks(row) {
      const base = row.code === 'all' ? {} : {hudud:String(row.id)};
      const href = (path,extra={}) => { const query = new URLSearchParams({...base,...extra}).toString(); return path+(query ? '?'+query : ''); };
      const links = {critical:href('/signallar'),warning:href('/signallar',{daraja:'WARNING'}),
        online:href('/qurolxonalar',{holat:'onlayn'}),offline:href('/qurolxonalar',{holat:'oflayn'}),
        sites:href('/qurolxonalar'),stock:href('/inventar'),detail:row.code === 'all' ? '/hududlar' : row.href};
      Object.entries(links).forEach(([key,url]) => { root.querySelector(`[data-lm-link="${key}"]`).href = url; });
    }
    function select(code, reveal=false, announce=false) {
      const row = code === 'all' ? national : byCode.get(code);
      if (!row) return;
      state.selected = code;
      if (code === 'all') state.zoomed = false;
      root.querySelectorAll('[data-lm-region]').forEach(node => {
        const selected = node.dataset.lmRegion === code;
        node.classList.toggle('is-selected', selected);
        if (node.getAttribute('role') === 'button') node.setAttribute('aria-pressed', String(selected));
        else if (selected) node.setAttribute('aria-current', 'true'); else node.removeAttribute('aria-current');
      });
      if (code !== 'all') faces.appendChild(shapes.get(code));
      picker.value = code;
      put('category', code === 'all' ? strings.nationalCategory : strings.selectedCategory);
      put('name', row.name); put('status', strings[row.state] || strings.unknown);
      const timeNode = root.querySelector('[data-lm="time"]');
      timeNode.classList.toggle('lm-warning-text', code === 'all' ? staleCount > 0 : row.stale);
      if (code === 'all') put('time', `${staleCount} ${strings.staleRegions} · ${missingCount} ${strings.missingRegions}`);
      else if (!row.sites) put('time', strings.noSites);
      else if (!row.updatedAt) put('time', strings.noMessage);
      else put('time', `${strings.oldestMessage}: ${stamp(row.updatedAt)}${row.stale ? ` · ${strings.stale}` : ''}`);
      put('signal-total', row.critical == null || row.warning == null ? null : number(row.critical+row.warning));
      ['critical','warning','offline','online','sites','stock'].forEach(key => put(key,number(row[key])));
      put('signal-change', `${strings.criticalLabel}: ${delta(row.critical,row.previous?.critical)} · ${strings.warningLabel}: ${delta(row.warning,row.previous?.warning)}`);
      put('connection-note', row.offline != null ? strings.connectionNote : !row.sites ? strings.noSites : `${number(row.knownOffline)} ${strings.knownOffline} · ${number(row.missingTelemetrySites)} ${strings.missingSites}`);
      put('inventory-note', code !== 'all' && row.stale ? strings.staleNote : strings.registeredNote);
      put('comparison', `${strings.previousDay}. ${strings.noOfflineHistory}. ${strings.staleLimit}: ${data.staleMinutes} ${strings.minutes}.`);
      root.querySelector('[data-lm="comparison"]').title = `${strings.comparisonPeriod}: ${stamp(data.previousAsOf)} → ${stamp(data.asOf)} (UTC+5). ${data.comparisonNote || ''} ${strings.oldestNote}`;
      put('selection', code === 'all' ? strings.nationalView : `${strings.selection}: ${row.short}`);
      put('detail-link-label', code === 'all' ? strings.openRegions : strings.openRegion);
      updateLinks(row); fitZoom(); focusAlerts();
      if (announce) root.querySelector('[data-lm-announcement]').textContent = `${row.name}. ${strings[row.state] || strings.unknown}. ${number(row.critical)} ${strings.criticalLabel}, ${number(row.warning)} ${strings.warningLabel}.`;
      if (reveal) revealDetails();
    }
    root.addEventListener('click', event => {
      const region = event.target.closest('[data-lm-region]');
      if (!region || !root.contains(region) || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      if (!byCode.has(region.dataset.lmRegion)) return;
      event.preventDefault(); select(region.dataset.lmRegion,true,true);
    });
    svg.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const region = event.target.closest('[data-lm-region]');
      if (region) { event.preventDefault(); select(region.dataset.lmRegion,true,true); }
    });
    picker.addEventListener('change', () => select(picker.value,false,true));
    filter.addEventListener('click', () => { state.filtered = !state.filtered; focusAlerts(); });
    zoom.addEventListener('click', () => { if (state.selected !== 'all') { state.zoomed = !state.zoomed; fitZoom(); } });
    root.querySelector('[data-lm-reset]').addEventListener('click', () => { state.filtered = false; select('all',false,true); });
    root.dataset.lmMounted = 'ready';
    select(state.selected);
    if (state.scroll !== null) { const scroller = root.closest('.main'); if (scroller) scroller.scrollTop = state.scroll; state.scroll = null; }
    if (state.focus) {
      const saved = state.focus;
      let target = saved.id ? document.getElementById(saved.id) : saved.control ? root.querySelector(`[${saved.control}]`) : null;
      if (!target && saved.region) target = [...root.querySelectorAll('[data-lm-region]')].find(node => node.dataset.lmRegion === saved.region && node.tagName.toLowerCase() === saved.type);
      if (target && root.contains(target)) target.focus({preventScroll:true});
      state.focus = null;
    }
  }
  function init() { document.querySelectorAll('[data-leadership]').forEach(root => { if (!root.dataset.lmMounted) mount(root); }); }
  document.addEventListener('htmx:beforeSwap', event => { if (isOverview(event)) { const root = document.querySelector('[data-leadership]'); if (root) rememberPosition(root); } });
  document.addEventListener('htmx:afterSwap', init);
  ['htmx:responseError','htmx:sendError','htmx:timeout'].forEach(name => document.addEventListener(name,event => {
    if (isOverview(event)) { const message = document.querySelector('[data-lm-refresh-error]'); if (message) message.hidden = false; }
  }));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
