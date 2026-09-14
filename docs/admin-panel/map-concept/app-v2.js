/* Isolated visual prototype: frozen sample snapshots, no operational API calls. */
(() => {
  'use strict';
  const asOf = '2026-09-14T10:00:00+05:00';
  const previousAsOf = '2026-09-13T10:00:00+05:00';
  const staleMinutes = 15;
  // sites, stock, critical signals, warning signals, offline sites
  const fixtures = {
    'UZ-QR':[2,64,0,0,0], 'UZ-XO':[2,52,0,0,0], 'UZ-NW':[1,35,0,0,0],
    'UZ-BU':[2,71,0,1,0], 'UZ-SA':[2,81,0,0,0], 'UZ-QA':[2,68,0,2,1],
    'UZ-SU':[1,43,0,0,0], 'UZ-JI':[1,32,0,0,0], 'UZ-SI':[1,24,0,0,0],
    'UZ-TO':[2,82,0,0,0], 'UZ-TK':[3,120,4,0,1], 'UZ-NG':[null,null,null,null,null],
    'UZ-AN':[1,38,0,0,0], 'UZ-FA':[2,65,0,0,0]
  };
  const previousOverrides = {'UZ-TK':[3,120,2,0,0], 'UZ-QA':[2,68,0,3,1]};
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
  const statusText = {stable:'Barqaror',critical:'Jiddiy signal mavjud',warning:'Ogohlantirish yoki aloqa uzilishi',unknown:'Ma’lumot yo‘q'};
  const fields = ['sites','stock','critical','warning','offline'];
  const record = values => Object.fromEntries(fields.map((key,i)=>[key,values[i]]));
  const data = Object.entries(fixtures).map(([code,values])=>{
    const geo=MAP_GEOMETRY.regions[code];
    const current=record(values);
    const updatedAt=current.sites===null?null:code==='UZ-BU'?'2026-09-14T09:30:00+05:00':code==='UZ-TK'?asOf:'2026-09-14T09:58:00+05:00';
    const age=updatedAt===null?null:Math.floor((Date.parse(asOf)-Date.parse(updatedAt))/60000);
    return {code,geo,...current,previous:record(previousOverrides[code]||values),updatedAt,age,stale:age!==null&&age>=staleMinutes,
      name:names[code]||geo.name,short:short[code]||geo.short,
      state:current.sites===null?'unknown':current.critical?'critical':current.warning||current.offline?'warning':'stable'};
  });
  const known=data.filter(r=>r.sites!==null);
  const missing=data.filter(r=>r.sites===null);
  const stale=data.filter(r=>r.stale);
  const comparable=known.filter(r=>r.previous.sites!==null);
  const sum=(rows,key)=>rows.reduce((total,r)=>total+r[key],0);
  const aggregate=rows=>Object.fromEntries(fields.map(key=>[key,sum(rows,key)]));
  const totals=aggregate(known);
  const previousTotals=aggregate(comparable.map(r=>r.previous));
  const all={...totals,previous:previousTotals,code:'all',name:'O‘zbekiston Respublikasi',state:totals.critical?'critical':totals.warning||totals.offline?'warning':'stable'};
  const put=(id,value)=>{document.getElementById(id).textContent=value===null?'—':value;};
  const time=value=>new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tashkent',hour:'2-digit',minute:'2-digit'}).format(new Date(value));
  const date=value=>new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tashkent',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date(value)).replaceAll('/','.');
  const delta=(now,before)=>now===null||before===null?'Taqqoslash uchun ma’lumot yo‘q':now===before?'O‘zgarish yo‘q':`${now>before?'+':'−'}${Math.abs(now-before)} ta`;
  const icons={...ICON_PATHS,
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
    moon:'<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14z"/>',
    north:'<path d="M12 21V3M7 8l5-5 5 5"/>'};
  const icon=name=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${icons[name]||icons.info}</svg>`;
  document.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});
  put('snapshot-time',`${date(asOf)} · ${time(asOf)} (UTC+5)`);
  document.getElementById('snapshot-time').dateTime=asOf;
  put('coverage-note',`${known.length-stale.length} hudud: yangi · ${stale.length}: eskirgan · ${missing.length}: ma’lumot yo‘q`);
  put('total-sites',totals.sites);put('total-stock',totals.stock);put('total-critical',totals.critical);
  put('total-coverage',`${known.length}/${data.length}`);
  put('site-note',`${totals.sites-totals.offline} onlayn · ${totals.offline} oflayn`);
  put('missing-note',`${missing.length} hududdan ma’lumot kelmagan`);
  put('critical-change',`${delta(totals.critical,previousTotals.critical)} · oldingi kunga nisbatan`);
  const priorityHost=document.getElementById('priority-items');
  function priority(code,title,note,tone){
    const button=document.createElement('button');button.className='priority-item';button.dataset.region=code;button.type='button';
    const span=document.createElement('span');const b=document.createElement('b');b.className=tone;b.textContent=title;
    const small=document.createElement('small');small.textContent=note;span.append(b,small);button.append(span);button.insertAdjacentHTML('beforeend',icon('chev'));priorityHost.append(button);
  }
  const criticalRegions=data.filter(r=>r.critical>0).sort((a,b)=>b.critical-a.critical);
  const offlineRegions=data.filter(r=>r.offline>0);
  if(criticalRegions.length)priority(criticalRegions[0].code,`${criticalRegions[0].short}: ${criticalRegions[0].critical} jiddiy signal`,`${criticalRegions.length} hudud rahbariyat e’tiborida`,'critical-text');
  priority('all',`${totals.offline} qurolxona oflayn`,offlineRegions.map(r=>r.short).join(' · '),'warning-text');
  priority(missing[0]?.code||'all',`${missing.length} hududdan ma’lumot yo‘q`,`${missing.map(r=>r.short).join(', ')}${stale.length?` · ${stale.length} hudud ma’lumoti eskirgan`:''}`,'');
  put('briefing-foot',`Ogohlantirishlar: ${data.filter(r=>r.warning>0).map(r=>`${r.short} — ${r.warning} ta${r.stale?' (eskirgan ma’lumot)':''}`).join(' · ')}.`);

  const svg=document.getElementById('country-map');
  const NS='http://www.w3.org/2000/svg';
  function node(type,attrs,parent,text){const n=document.createElementNS(NS,type);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;parent.appendChild(n);return n;}
  const defs=node('defs',{},svg);
  const pattern=node('pattern',{id:'no-data',width:8,height:8,patternUnits:'userSpaceOnUse',patternTransform:'rotate(35)'},defs);
  node('rect',{width:8,height:8,fill:'var(--map-unknown)'},pattern);node('path',{d:'M0 0 V8',stroke:'var(--unknown)','stroke-width':2},pattern);
  node('path',{d:data.map(r=>r.geo.d).join(' '),class:'country-shadow',transform:'translate(0 7)','fill-rule':'evenodd','aria-hidden':'true'},svg);
  const faces=node('g',{},svg),leaders=node('g',{'aria-hidden':'true'},svg),labelLayer=node('g',{},svg),markers=node('g',{'aria-hidden':'true','pointer-events':'none'},svg);
  const shapes=new Map(),labelGroups=new Map();
  data.forEach(r=>{
    const path=node('path',{d:r.geo.d,class:`map-face ${r.state}`,'data-region':r.code,'fill-rule':'evenodd',tabindex:0,role:'button','aria-label':`${r.name}: ${statusText[r.state]}${r.stale?', ma’lumot eskirgan':''}`,'aria-pressed':'false'},faces);
    node('title',{},path,`${r.name} · ${statusText[r.state]}${r.stale?' · Ma’lumot eskirgan':''}`);shapes.set(r.code,path);
    const [x,y,text]=labels[r.code];
    if(['UZ-SI','UZ-TO','UZ-TK','UZ-NG','UZ-AN','UZ-FA','UZ-XO'].includes(r.code))node('path',{d:`M${r.geo.cx} ${r.geo.cy} L${x} ${y+6}`,class:'leader','data-for':r.code},leaders);
    const g=node('g',{class:'label-group','data-region':r.code,role:'button',tabindex:0,'aria-label':`${r.name} tafsilotlari`,'aria-pressed':'false'},labelLayer);
    text.split('|').forEach((line,i)=>node('text',{x,y:y+i*20},g,line));
    const box=g.getBBox();const hit=node('rect',{x:box.x-10,y:box.y-10,width:box.width+20,height:Math.max(40,box.height+20),class:'label-hit',rx:4},g);g.insertBefore(hit,g.firstChild);labelGroups.set(r.code,g);
    if(r.critical||r.warning||r.offline||r.state==='unknown'){
      const marker=node('g',{class:`signal-marker ${r.state}`,'data-for':r.code,transform:`translate(${r.geo.cx},${r.geo.cy})`},markers);
      node('circle',{r:13},marker);node('text',{x:0,y:0},marker,r.state==='unknown'?'?':r.critical+r.warning||'!');
    }
  });
  const picker=document.getElementById('region-picker');
  picker.add(new Option('Respublika bo‘yicha','all'));
  const regionButtons=document.getElementById('region-buttons');
  const smallButtons=document.getElementById('small-region-buttons');
  data.forEach(r=>{
    picker.add(new Option(r.name,r.code));
    const button=document.createElement('button');button.type='button';button.className='region-button';button.dataset.region=r.code;button.setAttribute('aria-pressed','false');
    button.setAttribute('aria-label',`${r.name}: ${statusText[r.state]}${r.stale?', ma’lumot eskirgan':''}`);
    const swatch=document.createElement('i');swatch.className=`map-swatch ${r.state}`;swatch.setAttribute('aria-hidden','true');
    const content=document.createElement('span'),name=document.createElement('b'),note=document.createElement('small');name.textContent=r.short;
    note.textContent=r.state==='unknown'?'Ma’lumot yo‘q':r.stale?`${time(r.updatedAt)} · Eskirgan`:`${time(r.updatedAt)} · ${r.critical+r.warning} signal`;
    content.append(name,note);button.append(swatch,content);regionButtons.append(button);
    if(['UZ-TK','UZ-NG','UZ-AN','UZ-FA'].includes(r.code)){
      const quick=document.createElement('button');quick.type='button';quick.className='small-region-button';quick.dataset.region=r.code;quick.textContent=r.short;quick.setAttribute('aria-label',`${r.name}ni tanlash`);quick.setAttribute('aria-pressed','false');smallButtons.append(quick);
    }
  });
  let selected='all',zoomed=false;
  const defaultView='-28 -36 944 600';
  const zoomButton=document.getElementById('zoom');
  function updateZoom(){
    svg.classList.toggle('zoomed',zoomed);
    // Hidden SVG text has no measurable bounds; restore it before fitting.
    labelGroups.forEach((g,code)=>{
      g.style.display='';
      const [x,y]=labels[code];
      g.setAttribute('transform',zoomed?`translate(${x} ${y}) scale(.55) translate(${-x} ${-y})`:'');
    });
    if(!zoomed||selected==='all')svg.setAttribute('viewBox',defaultView);
    else{
      const a=shapes.get(selected).getBBox(),b=labelGroups.get(selected).getBBox();
      const left=Math.min(a.x,b.x)-28,top=Math.min(a.y,b.y)-28;
      const width=Math.max(230,Math.max(a.x+a.width,b.x+b.width)-left+28);
      const height=Math.max(180,Math.max(a.y+a.height,b.y+b.height)-top+28);
      svg.setAttribute('viewBox',`${left} ${top} ${width} ${height}`);
    }
    labelGroups.forEach((g,code)=>{g.style.display=zoomed&&code!==selected?'none':'';});
    svg.querySelectorAll('[data-for]').forEach(el=>{el.style.display=zoomed&&(el.dataset.for!==selected||el.classList.contains('signal-marker'))?'none':'';});
    zoomButton.disabled=selected==='all';zoomButton.setAttribute('aria-pressed',String(zoomed));
    zoomButton.innerHTML=icon(zoomed?'minus':'search')+(zoomed?'Masshtabni qaytarish':'Tanlangan hudud');
    zoomButton.setAttribute('aria-label',zoomed?'Xarita masshtabini qaytarish':'Tanlangan hududni kattalashtirish');
  }
  function revealDetails(){
    const panel=document.querySelector('.detail-panel'),rect=panel.getBoundingClientRect();
    if(rect.top<0||rect.top+100>window.innerHeight){panel.focus({preventScroll:true});panel.scrollIntoView({block:'start',behavior:'instant'});}
  }
  function select(code,reveal=false){
    const r=code==='all'?all:data.find(row=>row.code===code);if(!r)return;selected=code;if(code==='all')zoomed=false;
    document.querySelectorAll('[data-region]').forEach(el=>{const active=el.dataset.region===code;el.classList.toggle('selected',active);if(!el.classList.contains('priority-item'))el.setAttribute('aria-pressed',String(active));});
    if(code!=='all')faces.appendChild(shapes.get(code));
    picker.value=code;put('detail-category',code==='all'?'RESPUBLIKA BO‘YICHA':'TANLANGAN HUDUD');put('detail-name',r.name);
    put('detail-status',statusText[r.state]);
    const stamp=document.getElementById('detail-time');stamp.className='';
    if(code==='all'){stamp.textContent=`Eng so‘nggi xabar: ${time(asOf)} · ${stale.length} eskirgan · ${missing.length} ma’lumot yo‘q`;stamp.className=stale.length?'freshness-stale':'';}
    else if(r.updatedAt===null){stamp.textContent='Oxirgi xabar: yo‘q · Holat baholanmagan';stamp.className='freshness-unknown';}
    else{stamp.textContent=`Oxirgi xabar: ${time(r.updatedAt)} · ${r.age} daqiqa oldin${r.stale?' · Eskirgan':''} (namuna)`;stamp.className=r.stale?'freshness-stale':'';}
    put('detail-signal-total',r.critical===null?'—':`${r.critical+r.warning} ta`);
    put('detail-critical',r.critical);put('detail-warning',r.warning);put('detail-offline',r.offline);
    put('detail-online',r.sites===null?null:r.sites-r.offline);put('detail-sites',r.sites);put('detail-stock',r.stock);
    put('signal-change',r.critical===null?'Oldingi kun bilan taqqoslab bo‘lmaydi':`Jiddiy: ${delta(r.critical,r.previous.critical)} · Ogohlantirish: ${delta(r.warning,r.previous.warning)}`);
    put('connection-change',r.offline===null?'Aloqa holati noma’lum':`Oflayn: ${delta(r.offline,r.previous.offline)} · Alohida obyekt hisobi`);
    put('detail-note',code==='all'?`${known.length} hudud yig‘indisi; ${stale.length} tasining ma’lumoti eskirgan.`:r.stale?'Oxirgi ma’lum qiymatlar; yangilanish kutilmoqda.':r.sites===null?'Ma’lumot yo‘qligi nol hisoblanmaydi.':'Hudud bo‘yicha namunaviy hisob.');
    put('comparison-period',`Taqqoslash: ${date(previousAsOf)} ${time(previousAsOf)} → ${date(asOf)} ${time(asOf)} (UTC+5). ${code==='all'?`Bir xil ${comparable.length} hudud; Namangan hisobga kiritilmagan. `:''}Eskirish chegarasi: ${staleMinutes} daqiqa. Vaqtlar namunaviy.`);
    put('map-selection',code==='all'?'Respublika ko‘rinishi':`Tanlangan: ${r.short}`);
    updateZoom();if(reveal)revealDetails();
  }
  document.addEventListener('click',event=>{const target=event.target.closest('[data-region]');if(target)select(target.dataset.region,true);});
  svg.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){const target=event.target.closest('[data-region]');if(target){event.preventDefault();select(target.dataset.region,true);}}});
  picker.addEventListener('change',()=>select(picker.value));
  const filter=document.getElementById('focus-alerts');
  function focusAlerts(on){filter.setAttribute('aria-pressed',String(on));data.forEach(r=>shapes.get(r.code).classList.toggle('muted',on&&r.state==='stable'&&!r.stale));}
  filter.addEventListener('click',()=>focusAlerts(filter.getAttribute('aria-pressed')!=='true'));
  zoomButton.addEventListener('click',()=>{if(selected==='all')return;zoomed=!zoomed;updateZoom();svg.scrollIntoView({block:'nearest',behavior:'instant'});});
  document.getElementById('reset').addEventListener('click',()=>{focusAlerts(false);select('all',true);});
  const themeButton=document.getElementById('theme');
  themeButton.addEventListener('click',()=>{const light=document.documentElement.dataset.theme!=='light';document.documentElement.dataset.theme=light?'light':'dark';themeButton.innerHTML=`<span>${icon(light?'moon':'sun')}</span><span>${light?'Tungi rejim':'Kunduzgi rejim'}</span>`;themeButton.setAttribute('aria-label',light?'Tungi rejimga o‘tish':'Kunduzgi rejimga o‘tish');});
  select('all');
})();
