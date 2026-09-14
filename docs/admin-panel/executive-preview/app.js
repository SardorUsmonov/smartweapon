'use strict';
const byId = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const number = value => Number(value).toLocaleString('ru-RU');
const state = {data:null, selected:null, filter:'all', query:'', sort:'priority', direction:-1};
const set = (id, text) => { byId(id).textContent = text; };
const attention = row => row.active_alarms > 0 || row.offline > 0;
const priority = row => row.serious_alarms * 100 + row.offline * 10 + row.warnings;
const statusClass = row => row.serious_alarms ? 'critical' : row.offline ? 'offline' : row.warnings ? 'warning' : 'neutral';
const localDate = value => {
  if (!value) return 'Qayd etilmagan';
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  return match ? `${match[3]}.${match[2]}.${match[1]} · ${match[4]}:${match[5]}` : value;
};
function description(row) {
  const parts = [];
  if (row.serious_alarms) parts.push(`${row.serious_alarms} ta jiddiy signal`);
  if (row.warnings) parts.push(`${row.warnings} ta ogohlantirish`);
  if (row.offline) parts.push(`${row.offline} ta qurolxonada aloqa uzilgan`);
  return parts.length ? parts.join(' · ') : 'Faol signal va aloqa uzilishi qayd etilmagan';
}
function renderMetrics() {
  const d = state.data, s = d.summary;
  const formatted = localDate(d.captured_at).split(' · ');
  set('snapshot-date', formatted[0]); byId('snapshot-date').dateTime=d.captured_at;
  set('snapshot-time', `${formatted[1]} · Holat nusxasi`);
  set('summary-headline', `${s.attention_regions} ta hududda signal yoki aloqa uzilishi qayd etilgan.`);
  set('summary-detail', `${s.offline} ta qurolxonada aloqa uzilgan. ${s.overdue} ta qurolning qaytarish muddati o‘tgan.`);
  const values = {'metric-regions':s.regions,'metric-armories':s.armories,'metric-online':s.online,'metric-signals':s.active_alarms,'metric-overdue':s.overdue,'metric-issued':s.issued,'attention-count':s.attention_regions,'priority-total':s.attention_regions,'ack-count':s.pending_ack,'all-count':s.regions,'filter-attention-count':s.attention_regions};
  Object.entries(values).forEach(([id, value])=>set(id,number(value)));
  set('metric-online-denom', `/ ${s.armories}`);
  set('metric-offline', `${s.offline} ta aloqa uzilgan`);
  set('metric-sync', `Sinxron: ${localDate(d.armory_sync.newest).split(' · ')[0]}`);
  set('metric-serious', `${s.serious_alarms} ta jiddiy`);
  set('metric-warning', `${s.warnings} ta ogohlantirish`);
  set('source-captured', localDate(d.captured_at));
  set('source-event', localDate(d.source_latest_event));
  set('source-sync', localDate(d.armory_sync.newest));
  byId('source-notes').innerHTML = d.notes.map(note=>`<li>${escapeHTML(note)}</li>`).join('');
  byId('priority-list').innerHTML = d.regions.filter(attention).sort((a,b)=>priority(b)-priority(a)).map((row,index)=>`<button class="priority-row" type="button" data-region="${row.id}" aria-label="${escapeHTML(row.name)} hududini tanlash"><span class="priority-number">${String(index+1).padStart(2,'0')}</span><span class="priority-copy"><strong>${escapeHTML(row.name)}</strong><small class="${row.serious_alarms?'has-critical':row.offline?'has-offline':''}">${escapeHTML(description(row))}</small></span><span class="priority-arrow" aria-hidden="true">→</span></button>`).join('');
}
function renderTable() {
  let rows = state.data.regions.filter(row => (state.filter==='all'||attention(row)) && row.name.toLocaleLowerCase().includes(state.query));
  rows = [...rows].sort((a,b)=> {
    if (state.sort==='priority') return priority(b)-priority(a) || b.cabinets-a.cabinets;
    const result = state.sort==='name' ? a.name.localeCompare(b.name,'uz') : a[state.sort]-b[state.sort];
    return result*state.direction;
  });
  byId('region-rows').innerHTML = rows.length ? rows.map((row,index)=>`<tr class="${state.selected===row.id?'selected':''}"><td class="region-col"><span class="region-number">${String(index+1).padStart(2,'0')}</span><button type="button" class="region-button" data-region="${row.id}" aria-label="${escapeHTML(row.name)} hududini xaritada tanlash">${escapeHTML(row.name)}</button></td><td>${number(row.armories)}</td><td>${number(row.cabinets)}</td><td>${number(row.issued)}</td><td class="${row.overdue?'warning-number':''}">${number(row.overdue)}</td><td class="${row.serious_alarms?'signal-number':row.active_alarms?'warning-number':''}">${row.active_alarms || '—'}${row.serious_alarms?`<small>/${row.serious_alarms} jiddiy</small>`:''}</td><td>${row.offline?`<span class="offline-label">${row.offline} ta aloqa uzilgan</span>`:`<span class="online-label">${row.online}/${row.armories} aloqada</span>`}</td><td><a href="http://127.0.0.1:8080/hudud/${row.id}" target="_blank" rel="noopener" aria-label="${escapeHTML(row.name)} hudud kartasini ochish">↗</a></td></tr>`).join('') : '<tr><td class="empty-cell" colspan="8">Qidiruvga mos hudud topilmadi. Nomni yoki filtrni o‘zgartiring.</td></tr>';
  set('row-count', `${rows.length} / ${state.data.summary.regions} hudud ko‘rsatilmoqda`);
  document.querySelectorAll('[data-sort]').forEach(button=>{
    const active=button.dataset.sort===state.sort;
    const th=button.closest('th');
    if(active) th.setAttribute('aria-sort',state.direction===1?'ascending':'descending'); else th.removeAttribute('aria-sort');
    button.querySelector('span').textContent=active?(state.direction===1?'↑':'↓'):'↕';
  });
}
function selectRegion(id, reveal = false) {
  state.selected=id;
  const row=state.data.regions.find(row=>row.id===id);
  byId('clear-selection').hidden=!row;
  set('selected-name',row?row.name:'Respublika bo‘yicha');
  set('selected-description',row?`${row.armories} qurolxona · ${row.cabinets} yacheyka · ${row.issued} ta berilgan qurol`:`${state.data.summary.armories} qurolxona · ${state.data.summary.cabinets} yacheyka · ${state.data.summary.weapons} ta qurol hisobda`);
  byId('selected-link').href=row?`http://127.0.0.1:8080/hudud/${row.id}`:'http://127.0.0.1:8080/hududlar';
  document.querySelectorAll('[data-region]').forEach(element=>{
    const active=Number(element.dataset.region)===id;
    element.classList.toggle('selected',active);
    if(element.tagName.toLowerCase()==='a' && element.closest('#map')) element.setAttribute('aria-pressed',String(active));
  });
  renderTable();
  if (reveal) {
    const detail = byId('region-detail');
    detail.focus({preventScroll:true});
    detail.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});
  }
}
function renderMap(geo) {
  const rows=new Map(state.data.regions.map(row=>[row.code,row]));
  let svg=`<svg viewBox="0 0 ${geo.w} ${geo.h}" role="group" aria-label="O‘zbekistonning 14 hududi. Hudud nomini tanlab tafsilotlarni ko‘ring.">`;
  for (const [code,shape] of Object.entries(geo.regions)) {
    const row=rows.get(code); if(!row) continue;
    svg+=`<a href="#region-detail" role="button" tabindex="0" class="st-${statusClass(row)}" data-region="${row.id}" aria-pressed="false" aria-label="${escapeHTML(row.name)}: ${escapeHTML(description(row))}"><path d="${shape.d}"><title>${escapeHTML(row.name)} — ${escapeHTML(description(row))}</title></path></a>`;
  }
  for (const [code,shape] of Object.entries(geo.regions)) {
    if(code==='UZ-TK') {
      svg+=`<path class="callout" d="M${shape.cx},${shape.cy} l35,-45 h60"/><circle class="capital-dot" cx="${shape.cx}" cy="${shape.cy}" r="4"/><text x="${shape.cx+38}" y="${shape.cy-51}" font-size="15">Toshkent sh.</text>`;
    } else if (['UZ-QR','UZ-NW','UZ-BU','UZ-QA','UZ-SU','UZ-XO'].includes(code)) {
      svg+=`<text x="${shape.cx}" y="${shape.cy+5}" font-size="19" text-anchor="middle">${escapeHTML(shape.short)}</text>`;
    }
  }
  byId('map').innerHTML=svg+'</svg>';
}
function renderActivity() {
  const days=state.data.daily_ops;
  const max=Math.max(1,...days.map(day=>day.value));
  byId('activity-chart').innerHTML=days.map(day=>`<div class="chart-day ${day.today?'today':''}" title="${escapeHTML(day.date)}: ${number(day.value)} ta qayd"><span class="chart-value">${number(day.value)}</span><span class="chart-bar" style="height:${Math.max(1,day.value/max*105)}px"></span><span class="chart-label">${escapeHTML(day.date.slice(8))}.${escapeHTML(day.date.slice(5,7))}</span></div>`).join('');
  byId('activity-chart').setAttribute('aria-label',days.map(day=>`${day.date}: ${day.value} ta qayd`).join('; '));
  set('ops-total', number(days.reduce((sum,day)=>sum+day.value,0)));
}
document.addEventListener('click', event=>{
  const region=event.target.closest('[data-region]');
  if(region&&state.data){event.preventDefault();selectRegion(Number(region.dataset.region),region.matches('.priority-row,.region-button'));return;}
  const filter=event.target.closest('[data-filter]');
  if(filter&&state.data){state.filter=filter.dataset.filter;document.querySelectorAll('[data-filter]').forEach(button=>{const active=button===filter;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});renderTable();}
  const sort=event.target.closest('[data-sort]');
  if(sort&&state.data){state.direction=state.sort===sort.dataset.sort?-state.direction:(sort.dataset.sort==='name'?1:-1);state.sort=sort.dataset.sort;renderTable();}
  const nav=event.target.closest('.nav-link');
  if(nav){document.querySelectorAll('.nav-link').forEach(link=>{link.classList.toggle('active',link===nav);link.removeAttribute('aria-current');});nav.setAttribute('aria-current','location');}
});
byId('map').addEventListener('keydown',event=>{if(event.key===' '&&event.target.closest('[data-region]')){event.preventDefault();selectRegion(Number(event.target.closest('[data-region]').dataset.region));}});
byId('clear-selection').addEventListener('click',()=>{if(state.data)selectRegion(null,true);});
byId('region-search').addEventListener('input',event=>{state.query=event.target.value.trim().toLocaleLowerCase();if(state.data)renderTable();});
byId('print-report').addEventListener('click',()=>window.print());
Promise.all(['data.json','map.json'].map(url=>fetch(url).then(response=>{if(!response.ok)throw new Error(`Yuklash xatosi: ${url}`);return response.json();}))).then(([data,geo])=>{state.data=data;renderMetrics();renderMap(geo);renderActivity();selectRegion(null);}).catch(error=>{console.error(error);byId('load-error').hidden=false;byId('print-report').disabled=true;set('map','Xarita ma’lumoti yuklanmadi.');set('summary-headline','Ma’lumotlar yuklanmadi.');set('summary-detail','Saqlangan nusxani o‘qib bo‘lmadi.');});
