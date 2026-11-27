/* ScamShield Africa clickable prototype. SIMULATED: no network, no real model, no real data. */
(function(){
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store={get(k,d){try{return localStorage.getItem(k)||d}catch(e){return d}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const ST=SS.state={role:'visitor',theme:store.get('ss-theme',''),lang:store.get('ss-lang','en'),mfaDone:false,draft:{},step:0,me:'rep-me',reporters:{},prefs:{cats:{reversal:true,phishing:true,invest:false,jobs:false,tax:true},ev:{newthreat:true,campaign:true,status:true,org:false},freq:'daily',quiet:false},prefsDirty:false,audit:SS.audit,analyse:null,devOut:null,newKey:null};
const I18N={
 en:{nav_check:'Check',nav_report:'Report',nav_analyse:'Analyse',nav_mine:'My reports',nav_signin:'Sign in',h1:'Check before you pay or reply.',sub:'Search a phone number, website, email or payment reference that someone sent you. We show what others have reported and how well it is backed up.',search:'Search',ph:'Number, link, email or till',q:'What do you want to check?',verified_title:'Verified warnings this week',report_cta:'Report a scam',analyse_cta:'Analyse a message'},
 sw:{nav_check:'Angalia',nav_report:'Ripoti',nav_analyse:'Changanua',nav_mine:'Ripoti zangu',nav_signin:'Ingia',h1:'Angalia kabla ya kulipa au kujibu.',sub:'Tafuta namba ya simu, tovuti, barua pepe au kumbukumbu ya malipo uliyotumiwa. Tunaonyesha kile wengine wameripoti na ushahidi uliopo.',search:'Tafuta',ph:'Namba, kiungo, barua pepe au till',q:'Unataka kuangalia nini?',verified_title:'Maonyo yaliyothibitishwa wiki hii',report_cta:'Ripoti utapeli',analyse_cta:'Changanua ujumbe'}
};
const t=k=>(I18N[ST.lang]&&I18N[ST.lang][k])||I18N.en[k]||k;
const IC={
 shield:'<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',search:'<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>',flag:'<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',spark:'<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>',list:'<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',bell:'<path d="M6 9a6 6 0 0112 0c0 6 2 7 2 7H4s2-1 2-7M10 20a2 2 0 004 0"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/>',grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',key:'<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3"/>',code:'<path d="M9 8l-5 4 5 4M15 8l5 4-5 4"/>',users:'<circle cx="9" cy="8" r="3.5"/><path d="M2 20c.7-3.5 3.5-5 7-5s6.300 1.500 7 5M16 5a3.500 3.500 0 010 7M18 15c2 .5 3.500 2 4 5"/>',log:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',check:'<path d="M5 12l5 5 9-10"/>',x:'<path d="M6 6l12 12M18 6L6 18"/>',alert:'<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.500h.01"/>',moon:'<path d="M20 14A8 8 0 1110 4a7 7 0 0010 10z"/>',menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',queue:'<path d="M4 6h16M4 12h10M4 18h6"/><path d="M18 14l3 3-3 3"/>',chart:'<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',case:'<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M3 13h18"/>',download:'<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',plus:'<path d="M12 5v14M5 12h14"/>',phone:'<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',link:'<path d="M10 14a4 4 0 005.700 0l3-3a4 4 0 00-5.700-5.700l-1 1M14 10a4 4 0 00-5.700 0l-3 3a4 4 0 005.700 5.700l1-1"/>',mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',wallet:'<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M16 13h2M3 10h18"/>',store:'<path d="M4 9l1-5h14l1 5M5 9v11h14V9M9 20v-6h6v6"/>',more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V6a2 2 0 012-2h10"/>',lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',home:'<path d="M4 11l8-7 8 7v9H4z"/>'
};
const ico=(n,c='')=>`<svg class="ico ${c}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${IC[n]||''}</svg>`;
const typeIco={phone:'phone',url:'link',email:'mail',wallet:'wallet',social:'user',pay:'wallet',biz:'store'};
const logo=(s=32)=>`<svg width="${s}" height="${s}" viewBox="0 0 48 48" aria-hidden="true"><path d="M24 3l17 7v12c0 11-7 19-17 23C14 41 7 33 7 22V10z" fill="var(--brand)"/><path d="M24 3l17 7v12c0 11-7 19-17 23z" fill="var(--accent)" opacity=".9"/><circle cx="22" cy="22" r="7" fill="none" stroke="#fff" stroke-width="3"/><path d="M27 27l6 6" stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg>`;
SS.ico=ico;SS.esc=esc;

/* ---------- helpers ---------- */
const fmtD=d=>d;
const statusChip=i=>{const s=i.flag?'disputed':i.status;const cls={verified:'verified',unverified:'unverified',review:'review',disputed:'disputed'}[s];const icn={verified:'check',unverified:'info',review:'search',disputed:'alert'}[s];return `<span class="chip ${cls}">${ico(icn,'ico-sm')}${i.flag?SS.STATUS.disputed:SS.STATUS[i.status]}</span>`};
const riskChip=r=>({high:'<span class="chip high">Higher risk</span>',med:'<span class="chip med">Some warning signs</span>',low:'<span class="chip low">Few warning signs</span>',none:'<span class="chip none">Not enough information</span>'}[r]);
const confLevel=c=>c>=75?'High':c>=45?'Medium':'Low';
const normV=s=>String(s).toLowerCase().replace(/[\s\-+()]/g,'').replace(/^254/,'0');
const getInd=id=>SS.ind.find(i=>i.id===id);
const nowS=()=>'2026-11-27 '+new Date().toTimeString().slice(0,5);
function audit(who,act,reason){ST.audit.unshift({t:nowS(),who,act,reason:reason||'',h:Math.random().toString(16).slice(2,6)+'…'})}
function toast(msg){const w=$('#toasts');const d=document.createElement('div');d.className='toast';d.textContent=msg;w.append(d);setTimeout(()=>d.remove(),4200)}
function announce(msg){$('#live').textContent=msg}
const simTag='<span class="sim">Simulated — design prototype</span>';
const synth='<span class="chip demo">Synthetic demonstration data</span>';
SS.u={esc,ico,toast,statusChip,riskChip,confLevel,getInd,audit,simTag,synth,typeIco,normV,t,$,$$};

/* ---------- dialog ---------- */
function openDlg(html,opts={}){
  const d=document.createElement('dialog');d.innerHTML=`<div class="dlg" role="document">${html}</div>`;
  $('#dlg-root').append(d);
  d.addEventListener('close',()=>{d.remove();if(opts.returnFocus&&document.contains(opts.returnFocus))opts.returnFocus.focus()});
  d.addEventListener('click',e=>{if(e.target===d)d.close()});
  d.showModal();return d;
}
SS.openDlg=openDlg;
function confirmDlg({title,body,confirm='Confirm',danger,reason,reasonLabel,onOk,extra}){
  const d=openDlg(`<h2 id="dt">${title}</h2><div class="stack-s">${body||''}</div>${extra||''}
   <form method="dialog" novalidate>${reason?`<div class="field" style="margin-top:16px"><label for="dr">${reasonLabel||'Reason (kept in the audit trail)'}</label><textarea id="dr" required minlength="8" aria-describedby="dre"></textarea><div id="dre" class="err" hidden>${ico('alert','ico-sm')}Enter a reason of at least 8 characters.</div></div>`:''}
   <div class="btn-row"><button class="btn secondary" value="cancel" type="button" data-close>Cancel</button><button class="btn ${danger?'danger':''}" type="submit" id="dok">${confirm}</button></div></form>`,{});
  d.setAttribute('aria-labelledby','dt');
  $('[data-close]',d).onclick=()=>d.close();
  $('form',d).addEventListener('submit',e=>{e.preventDefault();let v='';if(reason){const ta=$('#dr',d);v=ta.value.trim();if(v.length<8){ta.setAttribute('aria-invalid','true');$('#dre',d).hidden=false;ta.focus();return}}
    onOk&&onOk(v,d);d.close()});
  return d;
}
SS.confirmDlg=confirmDlg;

/* ---------- navigation model ---------- */
const NAV={
 visitor:[['/','nav_check','search'],['/report','nav_report','flag'],['/analyse','nav_analyse','spark'],['/login','nav_signin','user']],
 reporter:[['/','nav_check','search'],['/report','nav_report','flag'],['/analyse','nav_analyse','spark'],['/mine','nav_mine','list'],['/notifications','Alerts','bell']],
 moderator:[['/mod','Queue','queue'],['/mod/corrections','Corrections','flag'],['/audit','Audit log','log'],['/','Public check','search'],['/notifications','Alerts','bell']],
 analyst:[['/org','Dashboard','chart'],['/org/campaigns','Campaigns','spark'],['/org/cases','Cases','case'],['/org/exports','Exports','download'],['/org/alerts','Alert rules','bell'],['/','Public check','search']],
 developer:[['/dev','Keys','key'],['/dev/docs','API docs','code'],['/dev/usage','Usage','chart'],['/dev/try','Try a request','search'],['/','Public check','search']],
 admin:[['/admin','Users','users'],['/admin/roles','Roles','lock'],['/audit','Audit log','log'],['/mod','Moderation','queue'],['/','Public check','search']]
};
const ROUTE_ROLES={'/mine':['reporter'],'/notifications':['reporter','moderator','analyst','developer','admin'],'/settings':['reporter','moderator','analyst','developer','admin'],'/mod':['moderator','admin'],'/org':['analyst'],'/dev':['developer'],'/admin':['admin'],'/audit':['moderator','admin']};
function allowed(path){for(const k of Object.keys(ROUTE_ROLES))if(path===k||path.startsWith(k+'/'))return ROUTE_ROLES[k].includes(ST.role);return true}
const routes=[];SS.route=(re,fn)=>routes.push([re,fn]);
const parse=()=>{const h=location.hash.slice(1)||'/';const[p,q]=h.split('?');return{path:p.replace(/\/$/,'')||'/',q:Object.fromEntries(new URLSearchParams(q||''))}};

/* ---------- shell ---------- */
function shell(){
  const staff=['moderator','analyst','developer','admin'].includes(ST.role);
  document.documentElement.dataset.theme=ST.theme||'';if(!ST.theme)document.documentElement.removeAttribute('data-theme');
  document.documentElement.lang=ST.lang;
  const nav=NAV[ST.role];const cur=parse().path;
  const isCur=p=>p==='/'?cur==='/'||cur.startsWith('/search')||cur.startsWith('/i/'):(p==='/org'||p==='/dev'||p==='/admin'||p==='/mod')?cur===p:cur.startsWith(p);
  const links=nav.map(([p,k,i])=>`<a href="#${p}" ${isCur(p)?'aria-current="page"':''}>${ico(i,'ico-sm')}${esc(I18N.en[k]?t(k):k)}</a>`).join('');
  const tabs=nav.slice(0,5).map(([p,k,i])=>`<a href="#${p}" ${isCur(p)?'aria-current="page"':''}>${ico(i)}<span>${esc(I18N.en[k]?t(k):k)}</span></a>`).join('');
  $('#shell').className='shell'+(staff?' has-side':'');
  $('#shell').innerHTML=`
  <a class="skip" href="#main" data-skip>Skip to main content</a>
  <div class="demo-bar" role="region" aria-label="Prototype controls"><span class="demo-note"><strong>Simulated — design prototype.</strong><span class="long"> All data is synthetic demonstration data. Nothing is sent anywhere.</span></span>
   <span class="row" style="gap:8px"><label for="role">Viewing as</label><select id="role">${Object.entries(SS.roles).map(([k,v])=>`<option value="${k}" ${k===ST.role?'selected':''}>${v}</option>`).join('')}</select><button type="button" data-act="reset">Reset demo</button></span></div>
  <header class="topbar"><a class="brand" href="#/">${logo()}<span>ScamShield<small>Africa · Kenya pilot</small></span></a>
   <nav class="nav-desktop" aria-label="Main">${links}</nav><span class="spacer"></span>
   <button class="icon-btn" data-act="theme" aria-label="Switch light or dark theme">${ico('moon')}</button>
   <div class="menu"><button class="icon-btn" data-act="menu" aria-haspopup="true" aria-expanded="false" aria-controls="acct" aria-label="Account and language">${ico(ST.role==='visitor'?'menu':'user')}</button>
    <div class="menu-pop" id="acct" hidden>
     ${ST.role==='visitor'?`<a href="#/login">Sign in</a><a href="#/register">Create account</a>`:`<a href="#/settings">Profile and settings</a><a href="#/notifications">Notifications</a><button data-act="signout">Sign out</button>`}
     <button data-act="lang">${ST.lang==='en'?'Kiswahili (draft translation)':'English'}</button><a href="#/states">UI states gallery</a><a href="#/about">How we label things</a></div></div></header>
  <div class="main"><nav class="side" aria-label="Section">${links}</nav><div class="view"><main id="main" tabindex="-1"></main></div></div>
  <nav class="tabbar" aria-label="Main (mobile)">${tabs}</nav>`;
}

/* ---------- render ---------- */
async function render(){
  shell();const r=parse();const main=$('#main');
  if(!allowed(r.path)){main.innerHTML=gate(r.path);}
  else{let hit;for(const[re,fn]of routes){const m=r.path.match(re);if(m){hit=[fn,m];break}}
    if(hit){const out=hit[0](r.q,...hit[1].slice(1));if(out&&out.then){main.innerHTML=out.skeleton||skeleton();main.innerHTML=await out.then(x=>x)}else main.innerHTML=out}
    else main.innerHTML=`<div class="empty">${ico('search')}<h1>Page not found</h1><p>That page does not exist in this prototype.</p><a class="btn" href="#/">Back to check</a></div>`}
  document.title=(($('h1',main)||{}).textContent||'ScamShield Africa')+' · ScamShield Africa (prototype)';
  const h1=$('h1',main);if(h1){h1.tabIndex=-1;if(!SS.noFocus)h1.focus({preventScroll:true})}
  SS.noFocus=false;if(!SS.keepScroll)window.scrollTo(0,0);SS.keepScroll=false;
  announce('Page loaded: '+(h1?h1.textContent:''));
  SS.after&&SS.after();SS.after=null;
}
SS.render=render;
const skeleton=()=>`<div aria-busy="true" role="status"><span class="sr-only">Loading…</span><div class="skel" style="width:40%;height:28px"></div><div class="skel"></div><div class="skel" style="width:80%"></div><div class="skel"></div></div>`;
SS.skeleton=skeleton;
function gate(path){const need=Object.entries(ROUTE_ROLES).find(([k])=>path===k||path.startsWith(k+'/'));
  return `<div class="empty" role="alert">${ico('lock')}<h1>This area is restricted</h1><p>${ST.role==='visitor'?'Sign in to continue. ':''}This page is for: <b>${(need?need[1]:[]).map(r=>SS.roles[r]).join(', ')}</b>. You are viewing as <b>${SS.roles[ST.role]}</b>.</p>
  <div class="btn-row" style="justify-content:center">${ST.role==='visitor'?'<a class="btn" href="#/login">Sign in</a>':''}<a class="btn secondary" href="#/">Go to public check</a></div><p class="xs muted">Prototype tip: use the "Viewing as" menu to switch role.</p></div>`}

/* ---------- global events ---------- */
document.addEventListener('click',e=>{
  const a=e.target.closest('[data-act]');
  if(!a){if(!e.target.closest('.menu')){const p=$('#acct');if(p&&!p.hidden){p.hidden=true;$('[data-act=menu]').setAttribute('aria-expanded','false')}}return}
  const act=a.dataset.act;
  if(act==='theme'){const dark=document.documentElement.dataset.theme==='dark'||(!ST.theme&&matchMedia('(prefers-color-scheme:dark)').matches);ST.theme=dark?'light':'dark';store.set('ss-theme',ST.theme);shell();SS.keepScroll=true;render()}
  else if(act==='menu'){const p=$('#acct');p.hidden=!p.hidden;a.setAttribute('aria-expanded',String(!p.hidden));if(!p.hidden)$('a,button',p).focus()}
  else if(act==='lang'){ST.lang=ST.lang==='en'?'sw':'en';store.set('ss-lang',ST.lang);SS.keepScroll=true;render();toast(ST.lang==='sw'?'Kiswahili draft shown for key labels. Needs native review.':'English')}
  else if(act==='signout'){ST.role='visitor';ST.mfaDone=false;location.hash='#/';render();toast('Signed out')}
  else if(act==='reset'){location.hash='#/';location.reload()}
  else if(SS.acts&&SS.acts[act]){SS.acts[act](a,e)}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const p=$('#acct');if(p&&!p.hidden){p.hidden=true;const b=$('[data-act=menu]');b.setAttribute('aria-expanded','false');b.focus()}}});
document.addEventListener('change',e=>{if(e.target.id==='role'){ST.role=e.target.value;ST.mfaDone=true;const dflt={visitor:'/',reporter:'/',moderator:'/mod',analyst:'/org',developer:'/dev',admin:'/admin'}[ST.role];location.hash='#'+dflt;render();toast('Viewing as '+SS.roles[ST.role]+' (role switcher is a prototype shortcut)')}});
document.addEventListener('submit',e=>{const f=e.target.closest('form[data-form]');if(f){e.preventDefault();SS.forms[f.dataset.form](f,e)}});
SS.acts=SS.acts||{};SS.forms=SS.forms||{};
window.addEventListener('hashchange',render);
SS.start=()=>{
  document.body.insertAdjacentHTML('afterbegin','<div id="shell"></div><div id="dlg-root"></div><div class="toast-wrap" id="toasts" aria-live="polite"></div><div id="live" class="sr-only" role="status" aria-live="polite"></div>');
  render();
};
})();
