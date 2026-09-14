/* Visual prototype. All metrics below are fixtures, never operational data. */
(() => {
  'use strict';
  const fixtures = {
    'UZ-QR':[2,64,0,0,0], 'UZ-XO':[2,52,0,0,0], 'UZ-NW':[1,35,0,0,0],
    'UZ-BU':[2,71,0,1,0], 'UZ-SA':[2,81,0,0,0], 'UZ-QA':[2,68,0,2,1],
    'UZ-SU':[1,43,0,0,0], 'UZ-JI':[1,32,0,0,0], 'UZ-SI':[1,24,0,0,0],
    'UZ-TO':[2,82,0,0,0], 'UZ-TK':[3,120,4,0,1], 'UZ-NG':[null,null,null,null,null],
    'UZ-AN':[1,38,0,0,0], 'UZ-FA':[2,65,0,0,0]
  };
  const labels = {
    'UZ-QR':[147,128,'Qoraqalpog‘iston|Respublikasi'], 'UZ-XO':[227,284,'Xorazm'],
    'UZ-NW':[390,217,'Navoiy'], 'UZ-BU':[323,363,'Buxoro'], 'UZ-SA':[466,371,'Samarqand'],
    'UZ-QA':[457,452,'Qashqadaryo'], 'UZ-SU':[535,496,'Surxondaryo'], 'UZ-JI':[529,302,'Jizzax'],
    'UZ-SI':[598,381,'Sirdaryo'], 'UZ-TO':[640,220,'Toshkent vil.'],
    'UZ-TK':[568,175,'Toshkent sh.'], 'UZ-NG':[745,248,'Namangan'],
    'UZ-AN':[825,302,'Andijon'], 'UZ-FA':[746,382,'Farg‘ona']
  };
  const names = {'UZ-QR':'Qoraqalpog‘iston Respublikasi','UZ-FA':'Farg‘ona viloyati'};
  const short = {'UZ-QR':'Qoraqalpog‘iston','UZ-FA':'Farg‘ona'};
  const data = Object.entries(fixtures).map(([code,values]) => {
    const geo = MAP_GEOMETRY.regions[code];
    const [sites,stock,critical,warning,offline] = values;
    return {code,geo,sites,stock,critical,warning,offline,name:names[code]||geo.name,short:short[code]||geo.short,
      state:sites===null?'unknown':critical?'critical':warning||offline?'warning':'stable'};
  });
  const svg = document.getElementById('country-map');
  const NS = 'http://www.w3.org/2000/svg';
  function node(type,attrs,parent,text){const n=document.createElementNS(NS,type);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;parent.appendChild(n);return n;}
  const defs=node('defs',{},svg);
  const gradient=node('linearGradient',{id:'region-fill',x1:0,y1:0,x2:0,y2:1},defs);
  node('stop',{offset:'0%','stop-color':'var(--map-top)'},gradient);
  node('stop',{offset:'100%','stop-color':'var(--map-bottom)'},gradient);
  const pattern=node('pattern',{id:'no-data',width:8,height:8,patternUnits:'userSpaceOnUse',patternTransform:'rotate(35)'},defs);
  node('rect',{width:8,height:8,fill:'var(--map-bottom)'},pattern);
  node('path',{d:'M0 0 V8',stroke:'var(--unknown)','stroke-width':2},pattern);
  node('path',{d:data.map(r=>r.geo.d).join(' '),class:'country-shadow',transform:'translate(0 8)','fill-rule':'evenodd','aria-hidden':'true'},svg);
  const faces=node('g',{},svg), leaders=node('g',{'aria-hidden':'true'},svg), labelLayer=node('g',{},svg),markers=node('g',{'aria-hidden':'true','pointer-events':'none'},svg);
  const statusText={stable:'Barqaror',critical:'Jiddiy signal mavjud',warning:'Ogohlantirish mavjud',unknown:'Ma’lumot yo‘q'};
  data.forEach(r=>{
    const path=node('path',{d:r.geo.d,class:`map-face ${r.state}`,'data-region':r.code,'fill-rule':'evenodd',tabindex:0,role:'button','aria-label':`${r.name}: ${statusText[r.state]}`,'aria-pressed':'false'},faces);
    node('title',{},path,`${r.name} · ${statusText[r.state]}`);
    const [x,y,text]=labels[r.code];
    if(['UZ-SI','UZ-TO','UZ-TK','UZ-NG','UZ-AN','UZ-FA','UZ-XO'].includes(r.code))node('path',{d:`M${r.geo.cx} ${r.geo.cy} L${x} ${y+6}`,class:'leader'},leaders);
    const g=node('g',{class:'label-group','data-region':r.code,role:'button',tabindex:0,'aria-label':`${r.name} tafsilotlari`,'aria-pressed':'false'},labelLayer);
    text.split('|').forEach((line,i)=>node('text',{x,y:y+i*20},g,line));
    if(r.critical||r.warning||r.state==='unknown'){
      const marker=node('g',{class:`signal-marker ${r.state}`,transform:`translate(${r.geo.cx},${r.geo.cy})`},markers);
      node('circle',{r:12},marker);node('text',{x:0,y:0},marker,r.state==='unknown'?'—':String(r.critical+r.warning));
    }
  });
  const picker=document.getElementById('region-picker');
  const allOption=document.createElement('option');allOption.value='all';allOption.textContent='Respublika bo‘yicha';picker.appendChild(allOption);
  const regionButtons=document.getElementById('region-buttons');
  data.forEach(r=>{
    const option=document.createElement('option');option.value=r.code;option.textContent=r.name;picker.appendChild(option);
    const button=document.createElement('button');button.type='button';button.className='region-button';button.dataset.region=r.code;button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',`${r.name}: ${statusText[r.state]}`);button.append(document.createTextNode(r.short));const dot=document.createElement('i');dot.className=`status-dot ${r.state}`;dot.setAttribute('aria-hidden','true');button.appendChild(dot);regionButtons.appendChild(button);
  });
  const sum=field=>data.reduce((total,r)=>total+(r[field]||0),0);
  const totals={sites:sum('sites'),stock:sum('stock'),critical:sum('critical'),warning:sum('warning'),offline:sum('offline')};
  const put=(id,value)=>{document.getElementById(id).textContent=value===null?'—':value;};
  put('total-sites',totals.sites);put('total-stock',totals.stock);put('total-critical',totals.critical);put('site-note',`${totals.sites-totals.offline} onlayn · ${totals.offline} oflayn`);
  function alertRow(level,title,body,count){return `<article class="alert-row"><div class="alert-meta"><span class="${level}">${level==='critical'?'JIDDIY SIGNAL':'OGOHLANTIRISH'}</span><span>${count} ta</span></div><strong>${title}</strong><p>${body}</p></article>`;}
  function select(code){
    const r=code==='all'?{...totals,code:'all',name:'O‘zbekiston Respublikasi',state:'critical'}:data.find(row=>row.code===code);
    if(!r)return;
    document.querySelectorAll('[data-region]').forEach(el=>{const active=el.dataset.region===code;el.classList.toggle('selected',active);el.setAttribute('aria-pressed',String(active));});
    picker.value=code;put('detail-category',code==='all'?'RESPUBLIKA BO‘YICHA':'TANLANGAN HUDUD');put('detail-code',code==='all'?'14 HUDUD':r.code.replace('UZ-',''));
    put('detail-name',r.name);const badge=document.getElementById('detail-status');badge.className=`detail-status ${r.state}`;badge.textContent=`● ${statusText[r.state]}`;
    put('detail-sites',r.sites);put('detail-stock',r.stock);put('detail-offline',r.offline);put('detail-count',r.sites===null?'—':r.critical+r.warning);
    let content='';
    if(r.critical)content+=alertRow('critical',`${r.critical} ta jiddiy signal`,code==='all'?'Toshkent shahri bo‘yicha namunaviy holat.':'Tasdiqlashni kutayotgan namunaviy signallar.',r.critical);
    if(r.warning)content+=alertRow('warning',`${r.warning} ta ogohlantirish`,code==='all'?'Buxoro va Qashqadaryo bo‘yicha namunaviy holat.':'Ko‘rib chiqishni kutayotgan namunaviy holatlar.',r.warning);
    if(r.offline)content+=alertRow('warning','Aloqa holatini tekshirish',`${r.offline} ta qurolxona oflayn ko‘rsatilgan.`,r.offline);
    if(!content)content=`<p class="empty">${r.sites===null?'Bu hudud bo‘yicha ma’lumot kelmagan. Holat barqaror deb belgilanmaydi.':'Bu hududda namunaviy ma’lumotlar bo‘yicha faol signal yoki aloqa uzilishi yo‘q.'}</p>`;
    document.getElementById('detail-alerts').innerHTML=content;
  }
  document.addEventListener('click',event=>{const target=event.target.closest('[data-region]');if(target)select(target.dataset.region);});
  svg.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){const target=event.target.closest('[data-region]');if(target){event.preventDefault();select(target.dataset.region);}}});
  picker.addEventListener('change',()=>select(picker.value));
  const filter=document.getElementById('focus-alerts');
  function focusAlerts(on){filter.setAttribute('aria-pressed',String(on));document.querySelectorAll('.map-face.stable').forEach(el=>el.classList.toggle('muted',on));}
  filter.addEventListener('click',()=>focusAlerts(filter.getAttribute('aria-pressed')!=='true'));
  document.getElementById('reset').addEventListener('click',()=>{focusAlerts(false);select('all');});
  const themeButton=document.getElementById('theme');
  themeButton.addEventListener('click',()=>{const light=document.documentElement.dataset.theme!=='light';document.documentElement.dataset.theme=light?'light':'dark';themeButton.innerHTML=light?'☾ <span>Tungi rejim</span>':'☀ <span>Kunduzgi rejim</span>';themeButton.setAttribute('aria-label',light?'Tungi rejimga o‘tish':'Kunduzgi rejimga o‘tish');});
  select('UZ-TK');
})();
