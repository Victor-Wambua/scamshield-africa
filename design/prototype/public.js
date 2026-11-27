(function(){
const {esc,ico,toast,statusChip,riskChip,confLevel,getInd,audit,simTag,synth,typeIco,normV,t,$,$$}=SS.u;
const ST=SS.state;
const indCard=i=>`<a class="result" href="#/i/${i.id}"><div class="row between"><span class="row" style="gap:8px">${ico(typeIco[i.type],'ico-sm')}<b class="mono">${esc(i.value)}</b></span>${statusChip(i)}</div>
 <div class="row" style="margin-top:8px;gap:8px">${riskChip(i.risk)}<span class="small muted">${i.reports} independent report${i.reports===1?'':'s'} · updated ${i.last}</span></div><div class="small muted" style="margin-top:6px">${esc(i.cat)}</div></a>`;
const field=(id,label,{type='text',hint='',val='',req=true,ph='',err=''}={})=>`<div class="field"><label for="${id}">${label}${req?'':' <span class="muted">(optional)</span>'}</label>${hint?`<div class="hint" id="${id}-h">${hint}</div>`:''}<input id="${id}" name="${id}" type="${type}" value="${esc(val)}" placeholder="${esc(ph)}" ${req?'required':''} ${err?'aria-invalid="true"':''} aria-describedby="${hint?id+'-h ':''}${err?id+'-e':''}" autocomplete="off">${err?`<div class="err" id="${id}-e">${ico('alert','ico-sm')}${err}</div>`:''}</div>`;
SS.field=field;

/* HOME */
SS.route(/^\/$/,()=>{
  const top=SS.ind.filter(i=>i.status==='verified').slice(0,3);
  return `<section class="hero"><h1>${t('h1')}</h1><p class="muted" style="max-width:60ch">${t('sub')}</p>
  <form class="searchbox" role="search" action="#" data-form="search"><div style="flex:1"><label for="q" class="sr-only">${t('q')}</label><input id="q" name="q" type="search" placeholder="${t('ph')}" autocomplete="off" required aria-describedby="qh"></div><button class="btn" type="submit">${ico('search')}${t('search')}</button></form>
  <p id="qh" class="small muted" style="margin-top:8px">Try <button class="btn ghost sm" data-act="ex" data-v="0700 000 101">0700 000 101</button> <button class="btn ghost sm" data-act="ex" data-v="pesa-reversal-help.example">pesa-reversal-help.example</button> <button class="btn ghost sm" data-act="ex" data-v="0722 000 999">0722 000 999</button> ${synth}</p></section>
  <div class="grid g3" style="margin:var(--sp-4) 0"><a class="card" href="#/report" style="text-decoration:none;color:inherit">${ico('flag')}<h2>${t('report_cta')}</h2><p class="small muted">Takes about 3 minutes. Works on a slow connection.</p></a>
  <a class="card" href="#/analyse" style="text-decoration:none;color:inherit">${ico('spark')}<h2>${t('analyse_cta')}</h2><p class="small muted">Paste an SMS or chat and see the warning signs, with reasons.</p></a>
  <a class="card" href="#/about" style="text-decoration:none;color:inherit">${ico('shield')}<h2>How we label things</h2><p class="small muted">Reported, unverified, or verified with evidence. Never an accusation.</p></a></div>
  <div class="grid g-main"><section><h2>${t('verified_title')}</h2><div class="stack-s">${top.map(indCard).join('')}</div></section>
  <aside class="card"><h2>Stay safe</h2><ul class="small" style="padding-left:18px;margin:0"><li>Nobody genuine asks for your PIN or one-time code.</li><li>Do not pay to receive a loan, prize or job.</li><li>Call the organisation on a number from its official website.</li><li>If you already paid, tell your mobile-money provider straight away.</li></ul></aside></div>`;
});
SS.acts.ex=a=>{location.hash='#/search?q='+encodeURIComponent(a.dataset.v)};
SS.forms.search=f=>{const q=f.q.value.trim();if(!q)return;location.hash='#/search?q='+encodeURIComponent(q)};

SS.route(/^\/about$/,()=>`<h1>How we label things</h1><div class="stack"><p>ScamShield Africa is not a list of people. It records <b>reports about phone numbers, links, emails, payment references and wallets</b> and shows how well each one is backed up.</p>
<div class="card"><h3>${statusChip({status:'unverified'})}</h3><p class="small">Someone reported it. We have not confirmed it. Treat with care, do not treat as proof.</p></div>
<div class="card"><h3>${statusChip({status:'review'})}</h3><p class="small">A moderator is checking the evidence.</p></div>
<div class="card"><h3>${statusChip({status:'verified'})}</h3><p class="small">At least 2 independent reporters and checked evidence, or an authorised source. Repeat reports from one person count once.</p></div>
<div class="notice info">${ico('info')}<span>If a record is wrong, anyone can ask for a correction. See "Request a correction" on every record.</span></div></div>`);

/* SEARCH */
SS.route(/^\/search$/,q=>{
  const query=(q.q||'').trim();
  const f={type:q.type||'',status:q.status||'',risk:q.risk||''};
  SS.after=()=>setTimeout(()=>{const box=$('#results');if(!box)return;fillResults(box,query,f);},450);
  return `<h1>Results</h1><form class="stack-s" role="search" data-form="search2"><div class="searchbox"><div style="flex:1"><label for="q" class="sr-only">${t('q')}</label><input id="q" name="q" type="search" value="${esc(query)}" required></div><button class="btn" type="submit">${ico('search')}${t('search')}</button></div>
  <div class="grid g3"><div><label for="ft">Type</label><select id="ft" name="type"><option value="">All types</option>${Object.entries(SS.TYPES).map(([k,v])=>`<option value="${k}" ${f.type===k?'selected':''}>${v}</option>`).join('')}</select></div>
  <div><label for="fs">Status</label><select id="fs" name="status"><option value="">Any status</option>${Object.entries(SS.STATUS).map(([k,v])=>`<option value="${k}" ${f.status===k?'selected':''}>${v}</option>`).join('')}</select></div>
  <div><label for="fr">Risk level</label><select id="fr" name="risk"><option value="">Any</option><option value="high" ${f.risk==='high'?'selected':''}>Higher risk</option><option value="med" ${f.risk==='med'?'selected':''}>Some warning signs</option><option value="none" ${f.risk==='none'?'selected':''}>Not enough information</option></select></div></div></form>
  <div id="results" style="margin-top:var(--sp-4)" aria-live="polite" aria-busy="true">${SS.skeleton()}</div>`;
});
SS.forms.search2=f=>{const p=new URLSearchParams({q:f.q.value.trim()});['type','status','risk'].forEach(k=>f[k].value&&p.set(k,f[k].value));location.hash='#/search?'+p;};
function fillResults(box,query,f){
  box.setAttribute('aria-busy','false');
  if(/simulate error/i.test(query)){box.innerHTML=`<div class="notice err" role="alert">${ico('alert')}<div><b>We could not reach the lookup service.</b><br>Check your connection and try again. Your search was not saved.<div style="margin-top:8px"><button class="btn sm" data-act="retry">Try again</button></div></div></div>`;return}
  const n=normV(query);
  let list=SS.ind.filter(i=>query?(normV(i.value).includes(n)||i.cat.toLowerCase().includes(query.toLowerCase())||i.value.toLowerCase().includes(query.toLowerCase())):true);
  if(f.type)list=list.filter(i=>i.type===f.type);if(f.status)list=list.filter(i=>f.status==='disputed'?i.flag:i.status===f.status&&!i.flag);if(f.risk)list=list.filter(i=>i.risk===f.risk);
  if(!list.length){
    const filtered=f.type||f.status||f.risk;
    box.innerHTML=`<div class="empty">${ico('search')}<h2>${filtered?'No matches for these filters':'No reports found for "'+esc(query)+'"'}</h2>
    <p class="muted" style="max-width:52ch;margin-inline:auto"><b>Not reported does not mean safe.</b> Many scams are new. ${filtered?'Clear a filter or search again.':'If this message or call feels wrong, trust that feeling.'}</p>
    <div class="btn-row" style="justify-content:center"><a class="btn" href="#/report?v=${encodeURIComponent(query)}">Report it</a><a class="btn secondary" href="#/analyse">Analyse the message</a></div>
    <ul class="small muted" style="text-align:left;max-width:46ch;margin:16px auto 0;padding-left:20px"><li>Do not send money or share a PIN or code.</li><li>Call the organisation using its official number.</li></ul></div>`;return}
  box.innerHTML=`<p class="small muted">${list.length} record${list.length===1?'':'s'} · ${synth}</p><div class="stack-s">${list.map(indCard).join('')}</div>`;
  announce2(list.length+' results');
}
function announce2(m){$('#live').textContent=m}
SS.acts.retry=()=>{SS.render()};

/* INDICATOR DETAIL */
SS.route(/^\/i\/(I-\d+)$/,(q,id)=>{
  const i=getInd(id);if(!i)return `<div class="empty"><h1>Record not found</h1><a class="btn" href="#/">Back</a></div>`;
  const staff=['moderator','admin','analyst'].includes(ST.role);
  const head={high:['Reported as higher risk','alert'],med:['Some warning signs have been reported','alert'],none:['Not enough information yet','info'],low:['Few warning signs','check']}[i.risk];
  const sub={verified:`${i.reports} independent people reported this and a moderator checked the evidence.`,unverified:`${i.reports} report${i.reports>1?'s':''} so far. A moderator has not confirmed it. This is not proof.`,review:'A moderator is checking the evidence now.',disputed:'The owner asked for a correction. We are re-checking and have softened the wording until then.'}[i.flag?'disputed':i.status];
  return `<p class="small"><a href="#/search?q=${encodeURIComponent(i.value)}">&larr; Back to results</a></p>
  <div class="row between"><h1 class="mono" style="margin:0">${esc(i.value)}</h1><span>${synth}</span></div>
  <div class="row" style="margin:8px 0 16px">${ico(typeIco[i.type],'ico-sm')}<span>${SS.TYPES[i.type]}</span>${statusChip(i)}${riskChip(i.risk)}</div>
  <div class="verdict ${i.risk}" role="note">${ico(head[1])}<div><h2 style="margin:0 0 4px">${head[0]}</h2><p style="margin:0">${sub}</p></div></div>
  <div class="grid g-main" style="margin-top:var(--sp-4)"><div class="stack">
   <section class="card"><h2>Why we say this</h2><ul style="padding-left:20px;margin:0" class="stack-s">${i.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>
    <p class="small muted" style="margin-top:12px">This summary is based on reports. It is not a finding that any person committed a crime.</p></section>
   <section class="card"><h2>Evidence confidence: ${confLevel(i.conf)} (${i.conf}%)</h2><div class="meter" role="img" aria-label="Evidence confidence ${i.conf} percent"><i style="width:${i.conf}%"></i></div>
    <p class="small muted" style="margin-top:8px">Confidence shows how well this record is backed up. It is not the chance that something is a scam.</p>
    <details><summary class="small" style="cursor:pointer;min-height:44px;display:flex;align-items:center">How is this worked out?</summary><ul class="small" style="padding-left:20px"><li>Independent reporters: ${i.reports} (repeat reports from one person count once)</li><li>Evidence items: ${i.evidence}</li><li>Moderator checked: ${i.status==='verified'?'yes':'no'}</li><li>Age and recency of reports</li></ul></details></section>
   <section class="card"><h2>Record details</h2><dl class="kv"><dt>Indicator type</dt><dd>${SS.TYPES[i.type]}</dd><dt>Risk category</dt><dd>${esc(i.cat)}</dd><dt>First reported</dt><dd>${i.first}</dd><dt>Last observed</dt><dd>${i.last}</dd><dt>Independent reports</dt><dd>${i.reports}${staff?` (${i.raw} submissions in total)`:''}</dd><dt>Evidence</dt><dd>${i.evidence} item${i.evidence===1?'':'s'}${staff?'':' (not shown publicly)'}</dd><dt>Verification</dt><dd>${SS.STATUS[i.status]}</dd><dt>Source</dt><dd>${esc(i.source)}</dd><dt>Record ID</dt><dd class="mono">${i.id}</dd></dl></section>
   <section class="card"><h2>Review history</h2><ol class="timeline">${i.hist.map(h=>`<li><b>${h[0]}</b> · ${staff?esc(h[1]):(h[1].startsWith('Moderator')?'Moderator':esc(h[1]))}<br>${esc(h[2])}</li>`).join('')}</ol></section></div>
  <aside class="stack"><section class="card"><h2>What to do</h2><ul style="padding-left:20px;margin:0" class="small stack-s"><li>Do not send money or share a PIN or one-time code.</li><li>Do not click links or call back numbers from the message.</li><li>Check with the organisation using its official contact.</li><li>Already paid? Contact your mobile-money provider now.</li></ul></section>
   <section class="card"><h2>Seen this too?</h2><a class="btn block" href="#/report?v=${encodeURIComponent(i.value)}&t=${i.type}">Add your report</a><div style="height:8px"></div><a class="btn secondary block" href="#/correct/${i.id}">This looks wrong. Request a correction</a><div style="height:8px"></div><button class="btn ghost block" data-act="copylink">${ico('copy','ico-sm')}Copy link to this record</button></section>
   ${staff?`<section class="card"><h2>Staff view</h2><p class="small muted">Visible to your role only.</p><a class="btn sm secondary" href="#/mod">Open moderation queue</a></section>`:''}</aside></div>`;
});
SS.acts.copylink=()=>{try{navigator.clipboard.writeText(location.href).catch(()=>{})}catch(e){}toast('Link copied')};

/* REPORT FLOW */
const STEPS=['Type','Details','Evidence','Consent','Review','Done'];
const D=()=>ST.draft;
SS.route(/^\/report$/,q=>{
  if(q.v&&!D().value){ST.draft={type:q.t||guess(q.v),value:q.v,desc:'',ev:[],text:'',consent:{},errs:{}};ST.step=q.t||guess(q.v)?1:0}
  if(!ST.draft.type&&!ST.draft.errs)ST.draft={type:'',value:'',desc:'',ev:[],text:'',consent:{},errs:{}};
  ST.draft.errs=ST.draft.errs||{};
  return stepView();
});
const guess=v=>/^[\d\s+]{9,}$/.test(v)?'phone':/@/.test(v)?'email':/\./.test(v)?'url':'';
function stepView(){
  const d=D(),s=ST.step,e=d.errs||{};
  const prog=`<ol class="stepper" aria-label="Progress">${STEPS.map((_,i)=>`<li class="${i<s?'done':i===s?'now':''}" ${i===s?'aria-current="step"':''}></li>`).join('')}</ol><p class="small muted" style="margin-bottom:var(--sp-3)">Step ${Math.min(s+1,6)} of 6: <b>${STEPS[s]}</b> · ${simTag}</p>`;
  const errSum=Object.keys(e).length?`<div class="notice err" role="alert" tabindex="-1" id="errsum">${ico('alert')}<div><b>Please fix ${Object.keys(e).length} thing${Object.keys(e).length>1?'s':''}:</b><ul style="margin:4px 0 0;padding-left:18px">${Object.entries(e).map(([k,v])=>`<li><a href="#" data-act="focusf" data-f="${k}">${v}</a></li>`).join('')}</ul></div></div><div style="height:12px"></div>`:'';
  let body='';
  const nav=(back,next,label='Continue')=>`<div class="btn-row" style="margin-top:var(--sp-4)">${back?`<button class="btn secondary" type="button" data-act="rback">Back</button>`:''}<button class="btn" type="submit" style="flex:1;min-width:160px">${label}</button></div>`;
  if(s===0)body=`<h1>What do you want to report?</h1><p class="muted">Choose the closest match. You can change it later.</p><fieldset><legend class="sr-only">Report type</legend><div class="choices two">${[['phone','Suspicious phone number or call','phone'],['url','Phishing link or fake website','link'],['email','Suspicious email','mail'],['pay','Scam message or payment request','wallet'],['social','Fake or fraudulent social account','user'],['biz','Business impersonation','store'],['wallet','Suspicious wallet address','wallet'],['invest','Investment-scam ad','chart']].map(([k,l,ic])=>`<label class="choice"><input type="radio" name="type" value="${k}" ${d.type===k?'checked':''}>${ico(ic,'ico-sm')}<span>${l}</span></label>`).join('')}</div></fieldset>${e.type?`<div class="err" id="type-e">${ico('alert','ico-sm')}${e.type}</div>`:''}${nav(false,true)}`;
  if(s===1){const lab={phone:'Phone number',url:'Website address',email:'Email address',pay:'Number, till or reference',social:'Account name or link',biz:'Business name',wallet:'Wallet address',invest:'Website, account or number in the ad'}[d.type]||'Indicator';
    body=`<h1>Tell us what happened</h1>${field('value',lab,{val:d.value,err:e.value,hint:d.type==='phone'?'Example: 0700 000 101':d.type==='url'?'Example: pay-now.example. Do not open it.':''})}
    <div class="field"><label for="desc">What did they say or ask for?</label><div class="hint" id="desc-h">At least 20 characters. Do not include other people's names or ID numbers.</div><textarea id="desc" name="desc" required aria-describedby="desc-h ${e.desc?'desc-e':''}" ${e.desc?'aria-invalid="true"':''}>${esc(d.desc)}</textarea>${e.desc?`<div class="err" id="desc-e">${ico('alert','ico-sm')}${e.desc}</div>`:''}</div>
    <div class="grid g2"><div class="field"><label for="when">When did it happen? <span class="muted">(optional)</span></label><input type="date" id="when" name="when" value="${esc(d.when||'')}" max="2026-11-27"></div><div class="field"><label for="amt">Amount lost, KES <span class="muted">(optional)</span></label><input type="number" id="amt" name="amt" min="0" inputmode="numeric" value="${esc(d.amt||'')}"></div></div>${nav(true,true)}`}
  if(s===2)body=`<h1>Add evidence <span class="muted" style="font-weight:400">(optional, but it helps)</span></h1>
    <div class="field"><label for="ev">Screenshots or photos</label><div class="hint" id="ev-h">Up to 5 images, 5 MB each. Hide other people's names and numbers first.</div><input id="ev" name="ev" type="file" accept="image/*" multiple aria-describedby="ev-h"><ul class="small" style="padding-left:18px">${(d.ev||[]).map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>
    <div class="field"><label for="text">Paste the message text</label><textarea id="text" name="text">${esc(d.text)}</textarea></div>
    <label class="check"><input type="checkbox" name="redact" ${d.redact?'checked':''}><span>I removed personal details that are not part of the scam.</span></label>
    <p class="small muted">Prototype: files are not uploaded. Only the file names are kept in memory.</p>${nav(true,true,'Continue')}`;
  if(s===3){const c=d.consent||{};body=`<h1>Consent and privacy</h1><div class="card flat stack-s"><h2>How we use your report</h2><ul class="small" style="padding-left:18px;margin:0"><li>We publish only the indicator (for example a number), the status and a summary. Never your name or contact.</li><li>Moderators and approved partner organisations may see your evidence to check it.</li><li>You can ask us to correct or delete your report. Kenya Data Protection Act 2019 rights apply.</li></ul><p class="small"><a href="#/about">Read the full privacy notice</a> (prototype placeholder)</p></div><div style="height:12px"></div>
    <label class="check"><input type="checkbox" name="c_priv" ${c.priv?'checked':''} ${e.priv?'aria-invalid="true"':''}><span><b>Required.</b> I have read the privacy notice and agree to this processing.</span></label>
    <label class="check"><input type="checkbox" name="c_true" ${c.true?'checked':''}><span><b>Required.</b> To the best of my knowledge, what I wrote is true.</span></label>
    <label class="check"><input type="checkbox" name="c_share" ${c.share?'checked':''}><span>Optional. Share the indicator with approved partner organisations.</span></label>
    <label class="check"><input type="checkbox" name="c_contact" ${c.contact?'checked':''}><span>Optional. You may contact me if more evidence is needed.</span></label>
    ${e.priv?`<div class="err">${ico('alert','ico-sm')}${e.priv}</div>`:''}${nav(true,true)}`}
  if(s===4)body=`<h1>Check your report</h1><dl class="kv"><dt>Type</dt><dd>${SS.TYPES[d.type]||d.type}</dd><dt>Indicator</dt><dd class="mono">${esc(d.value)}</dd><dt>What happened</dt><dd>${esc(d.desc)}</dd><dt>Evidence</dt><dd>${(d.ev||[]).length} file(s)${d.text?', message text added':''}</dd><dt>Consent</dt><dd>Privacy and truth confirmed${d.consent.share?'; sharing allowed':''}</dd></dl>
    <div class="row" style="margin-top:12px"><button class="btn ghost sm" type="button" data-act="rjump" data-s="1">Edit details</button><button class="btn ghost sm" type="button" data-act="rjump" data-s="2">Edit evidence</button></div>
    ${d.submitErr?`<div class="notice err" role="alert" style="margin-top:12px">${ico('alert')}<div><b>Could not send your report.</b> Your answers are saved on this device. Try again when your connection is better.</div></div>`:''}
    <div class="notice info" style="margin-top:12px">${ico('info')}<span>Submitting does not make a public accusation. We check for repeats, then a moderator reviews.</span></div>${nav(true,true,d.submitErr?'Try again':'Send report')}`;
  if(s===5)return `<div class="stack">${prog.replace('Step 6 of 6','Step 6 of 6')}<div class="notice ok" role="status">${ico('check')}<div><h1 style="margin:0 0 4px">Thank you. Report received.</h1><p style="margin:0">Reference <b class="mono">${d.ref}</b></p></div></div>
    <div class="card"><h2>What happens next</h2><ol class="small" style="padding-left:18px;margin:0" class="stack-s"><li>We check whether others reported the same indicator.</li><li>${d.dupMsg}</li><li>A moderator may ask for more evidence.</li><li>We email you when the status changes (if you signed in).</li></ol></div>
    <div class="btn-row"><a class="btn" href="#/${ST.role==='visitor'?'register':'mine'}">${ST.role==='visitor'?'Create an account to track it':'Track my reports'}</a><button class="btn secondary" data-act="rnew">Report another</button></div></div>`;
  return `<div class="stack" style="max-width:720px;margin:0 auto">${prog}${errSum}<form data-form="report" novalidate>${body}</form></div>`;
}
SS.acts.focusf=(a,e)=>{e.preventDefault();const el=$('#'+a.dataset.f)||$(`[name=${a.dataset.f}]`);el&&el.focus()};
SS.acts.rback=()=>{ST.step=Math.max(0,ST.step-1);rerender()};
SS.acts.rjump=a=>{ST.step=+a.dataset.s;rerender()};
SS.acts.rnew=()=>{ST.draft={};ST.step=0;rerender()};
const rerender=()=>{$('#main').innerHTML=stepView();const h=$('#main h1');h.tabIndex=-1;h.focus();window.scrollTo(0,0)};
function validate(s,f){const d=D(),e={};
  if(s===0){const v=(f.querySelector('[name=type]:checked')||{}).value;if(!v)e.type='Choose what you want to report';else d.type=v}
  if(s===1){d.value=f.value.value.trim();d.desc=f.desc.value.trim();d.when=f.when.value;d.amt=f.amt.value;
    if(!d.value)e.value='Enter the indicator';
    else if(d.type==='phone'&&!/^(\+?254|0)[17]\d{8}$/.test(d.value.replace(/[\s-]/g,'')))e.value='Enter a Kenyan phone number, like 0700 000 101';
    else if(d.type==='email'&&!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.value))e.value='Enter an email address like name@example.test';
    else if(d.type==='url'&&!/^[^\s]+\.[^\s]{2,}$/.test(d.value))e.value='Enter a website address, like pay-now.example';
    else if(d.type==='wallet'&&d.value.length<26)e.value='Wallet addresses are usually 26 characters or longer';
    if(d.desc.length<20)e.desc='Write at least 20 characters ('+d.desc.length+' so far)'}
  if(s===2){d.ev=[...f.ev.files].map(x=>x.name).slice(0,5);d.text=f.text.value;d.redact=f.redact.checked}
  if(s===3){d.consent={priv:f.c_priv.checked,true:f.c_true.checked,share:f.c_share.checked,contact:f.c_contact.checked};if(!d.consent.priv||!d.consent.true)e.priv='Tick both required boxes to continue'}
  return e}
SS.forms.report=f=>{
  const d=D();const e=validate(ST.step,f);d.errs=e;
  if(Object.keys(e).length){rerender();const sum=$('#errsum');sum&&sum.focus();return}
  if(ST.step===4){
    const btn=$('button[type=submit]',f);btn.disabled=true;btn.innerHTML='<span class="spin"></span> Sending…';
    setTimeout(()=>{
      if(/simulate error/i.test(d.desc)&&!d.retried){d.submitErr=true;d.retried=true;rerender();return}
      d.submitErr=false;
      const hit=SS.ind.find(i=>normV(i.value)===normV(d.value));
      d.ref='R-'+(2100+Math.floor(Math.random()*800));
      if(hit){const seen=(ST.reporters[hit.id]=ST.reporters[hit.id]||new Set());
        if(seen.has(ST.me)){hit.raw++;d.dupMsg='You already reported this indicator, so your new submission was linked to your earlier one. It does not count as an independent report.'}
        else{seen.add(ST.me);hit.raw++;hit.reports++;d.dupMsg='This matches an existing record ('+hit.id+'). Your report was linked to it as 1 more independent report. Now '+hit.reports+' in total.'}
      }else{d.dupMsg='No matching record was found, so a new unverified record will be created after review.'}
      SS.mine.unshift({id:d.ref,type:d.type,value:d.value,when:'2026-11-27',step:1,out:'Received. Checking for duplicates',ind:hit?hit.id:null});
      d.retried=false;ST.step=5;rerender();announce2('Report sent')},900);return}
  ST.step++;rerender();
};

/* ANALYSER (rule-based simulation) */
const RULES=[
 {k:'urgency',re:/\b(within \d+ ?(hour|minute|min|hr)s?|immediately|urgent|right now|last chance|haraka|sasa hivi|today only)\b/gi,why:'Pressure to act very fast. Scams use this so you do not stop to check.',w:15},
 {k:'pay',re:/\b(send|tuma|pay|deposit|transfer)\b[^.]{0,40}\b(fee|ksh|kes|\d{3,})\b/gi,why:'Asks you to send money first.',w:20},
 {k:'rev',re:/\b(sent (it )?(by|in) (mistake|error)|reverse|return (the )?money|nimetuma kimakosa|rudisha)\b/gi,why:'"Sent by mistake, please return" is a common mobile-money story.',w:25},
 {k:'prize',re:/\b(you (have )?won|congratulations|winner|bonus|ushindi|prize|free gift)\b/gi,why:'Unexpected prize or bonus.',w:15},
 {k:'cred',re:/\b(pin|otp|password|one[- ]time (code|password)|verification code|nambari ya siri)\b/gi,why:'Asks for a PIN, password or code. Genuine providers never ask for these.',w:30},
 {k:'imp',re:/\b(safaricom|m-?pesa|airtel|kra|equity|kcb|co-?op bank|customer care|ncba|huduma)\b/gi,why:'Names a well-known organisation. Check it on its own official channel.',w:8},
 {k:'url',re:/\b(?:https?:\/\/)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:example|test|xyz|top|click|info|tk|ly)(?:\/\S*)?|\b(?:bit\.ly|tinyurl\.com)\/\S+/gi,why:'Link on an unusual or shortened domain. Do not open it.',w:20,cls:'url'},
 {k:'fee',re:/\b(processing fee|registration fee|visa fee|delivery fee|release fee)\b/gi,why:'Asks you to pay a fee before getting a loan, job or parcel.',w:20}
];
const SAMPLES={rev:'Hello, I sent KES 3,500 to your number by mistake. Please reverse it immediately to 0700 000 101. Thanks. Check: pesa-reversal-help.example',loan:'Congratulations! Your KES 30,000 loan is approved. Pay a KES 1,200 processing fee today only to 0700 000 214 to release it.',ok:'Hi, see you at the 4pm meeting tomorrow. I will bring the printed budget. Safe travels.'};
SS.route(/^\/analyse$/,()=>`<h1>Analyse a message</h1><p class="muted" style="max-width:62ch">Paste a message and we point out warning signs and compare any phone numbers or links with reports. This is <b>not proof</b> that something is a scam, and a clear result is <b>not proof it is safe</b>.</p>
 <p>${simTag} <span class="small muted">This demo uses simple keyword rules, not a real AI model.</span></p>
 <form data-form="analyse" class="stack" novalidate><div class="field"><label for="msg">Message text</label><div class="hint" id="mh">Remove other people's names first. Nothing is sent anywhere in this prototype.</div><textarea id="msg" name="msg" rows="6" aria-describedby="mh merr">${esc((ST.analyse||{}).text||'')}</textarea><div id="merr" class="err" hidden>${ico('alert','ico-sm')}Paste at least 10 characters.</div></div>
 <div class="row"><span class="small muted">Try a sample:</span><button type="button" class="btn ghost sm" data-act="sample" data-s="rev">Reversal story</button><button type="button" class="btn ghost sm" data-act="sample" data-s="loan">Loan fee</button><button type="button" class="btn ghost sm" data-act="sample" data-s="ok">Ordinary message</button></div>
 <button class="btn" type="submit">${ico('spark')}Analyse</button></form><div id="aout" aria-live="polite" style="margin-top:var(--sp-5)">${(ST.analyse||{}).html||''}</div>`);
SS.acts.sample=a=>{$('#msg').value=SAMPLES[a.dataset.s];$('#msg').focus()};
SS.forms.analyse=f=>{
  const text=f.msg.value.trim();const err=$('#merr');
  if(text.length<10){err.hidden=false;f.msg.setAttribute('aria-invalid','true');f.msg.focus();return}
  err.hidden=true;f.msg.removeAttribute('aria-invalid');
  const out=$('#aout');out.innerHTML=SS.skeleton();
  setTimeout(()=>{
    const hits=[];let score=0;const seen={};
    RULES.forEach(r=>{let m;const re=new RegExp(r.re.source,'gi');while((m=re.exec(text))){hits.push({s:m.index,e:m.index+m[0].length,r});if(!seen[r.k]){seen[r.k]=1;score+=r.w}}});
    const phones=[...text.matchAll(/(?:\+?254|0)[17]\d{2}[\s-]?\d{3}[\s-]?\d{3}/g)].map(m=>m[0]);
    const prior=[];SS.ind.forEach(i=>{if(phones.some(p=>normV(p)===normV(i.value))||text.toLowerCase().includes(i.value.toLowerCase()))prior.push(i)});
    prior.forEach(i=>score+=i.status==='verified'?20:8);
    score=Math.min(100,score);
    const level=score>=60?['Several warning signs','high']:score>=25?['Some warning signs','med']:['Few warning signs found','none'];
    const conf=Math.min(92,30+Object.keys(seen).length*10+prior.length*10);
    hits.sort((a,b)=>a.s-b.s);let html='',p=0;hits.forEach(h=>{if(h.s<p)return;html+=esc(text.slice(p,h.s))+`<mark class="mark-hl ${h.r.cls||''}">${esc(text.slice(h.s,h.e))}</mark>`;p=h.e});html+=esc(text.slice(p));
    const reasons=Object.keys(seen).map(k=>RULES.find(r=>r.k===k));
    const res=`<div class="stack"><div class="verdict ${level[1]}">${ico(level[1]==='none'?'info':'alert')}<div><h2 style="margin:0">${level[0]}</h2><p style="margin:4px 0 0">Analysis confidence: <b>${confLevel(conf)} (${conf}%)</b>. ${simTag}</p></div></div>
    <div class="card"><h2>Your message, with warning signs marked</h2><p style="white-space:pre-wrap;line-height:1.9">${html}</p></div>
    <div class="card"><h2>Why</h2>${reasons.length?`<ul class="stack-s" style="padding-left:20px;margin:0">${reasons.map(r=>`<li>${r.why}</li>`).join('')}</ul>`:'<p>We did not find the usual warning words or links. That does not mean the message is safe.</p>'}</div>
    <div class="card"><h2>Compared with reports</h2>${prior.length?prior.map(indCard).join(''):'<p class="muted">No matching number or link in our records. Not reported does not mean safe.</p>'}</div>
    <div class="notice warn">${ico('alert')}<span><b>This is an automated guess, not proof of fraud.</b> If unsure, contact the organisation on its official number. Never share a PIN or code.</span></div>
    <div class="btn-row"><a class="btn" href="#/report?v=${encodeURIComponent(phones[0]||'')}&t=${phones[0]?'phone':''}">Report this</a><button class="btn secondary" data-act="clear-a">Clear</button></div></div>`;
    out.innerHTML=res;ST.analyse={text,html:res};announce2('Analysis finished: '+level[0]);
  },700);
};
SS.acts['clear-a']=()=>{ST.analyse=null;SS.render()};

/* AUTH */
const authWrap=(title,inner)=>`<div style="max-width:440px;margin:0 auto" class="stack"><h1>${title}</h1><p>${simTag}</p>${inner}</div>`;
SS.route(/^\/login$/,()=>authWrap('Sign in',`<form data-form="login" novalidate class="card">${field('em','Email or phone',{type:'text',ph:'name@example.test'})}${field('pw','Password',{type:'password'})}<button class="btn block" type="submit">Sign in</button><p class="small" style="margin-top:12px"><a href="#/recover">Forgot password?</a> · <a href="#/register">Create account</a></p><p class="small muted">Any non-empty values work. Emails starting mod, analyst or admin continue to the two-step check; others sign in as a reporter.</p></form>`));
SS.forms.login=f=>{
  if(!f.em.value.trim()||!f.pw.value){$('#main').querySelector('form').outerHTML=`<form data-form="login" novalidate class="card"><div class="notice err" role="alert">${ico('alert')}<span>Enter your email or phone and your password.</span></div>${field('em','Email or phone',{val:f.em.value,err:f.em.value?'':'Required'})}${field('pw','Password',{type:'password',err:'Required'})}<button class="btn block" type="submit">Sign in</button></form>`;$('#main input[aria-invalid=true]').focus();return}
  if(/^(mod|admin|analyst)/i.test(f.em.value.trim())){ST.pending=/^admin/i.test(f.em.value)?'admin':/^analyst/i.test(f.em.value)?'analyst':'moderator';location.hash='#/mfa';return}
  ST.role='reporter';location.hash='#/';toast('Signed in as a registered reporter');};
SS.route(/^\/register$/,()=>authWrap('Create an account',`<form data-form="register" novalidate class="card">${field('nm','Name',{})}${field('em','Email or phone',{})}<div class="field"><label for="pw">Password</label><div class="hint" id="pwh">At least 10 characters. A few random words is fine.</div><input id="pw" name="pw" type="password" autocomplete="new-password" aria-describedby="pwh pws"><div class="meter" style="margin-top:8px"><i id="pwm" style="width:0"></i></div><div id="pws" class="small muted" aria-live="polite">Strength: not entered</div></div><label class="check"><input type="checkbox" name="ok"><span>I accept the terms and have read the privacy notice.</span></label><div id="rerr" class="err" hidden>${ico('alert','ico-sm')}Fill every field and accept the terms.</div><button class="btn block" type="submit">Create account</button></form>`));
document.addEventListener('input',e=>{if(e.target.id==='pw'&&e.target.name==='pw'&&$('#pwm')){const v=e.target.value;const sc=Math.min(4,(v.length>=10)+(v.length>=14)+/\d/.test(v)+/[^\w]/.test(v));$('#pwm').style.width=sc*25+'%';$('#pws').textContent='Strength: '+['too short','weak','fair','good','strong'][sc]}});
SS.forms.register=f=>{if(!f.nm.value.trim()||!f.em.value.trim()||f.pw.value.length<10||!f.ok.checked){$('#rerr').hidden=false;(f.nm.value?f.em.value?f.pw:f.em:f.nm).focus();return}
  ST.role='reporter';location.hash='#/settings';toast('Account created (simulated). Welcome.')};
SS.route(/^\/recover$/,()=>authWrap('Reset your password',`<form data-form="recover" novalidate class="card">${field('em','Email',{type:'email'})}<button class="btn block" type="submit">Send reset link</button><p class="small muted">We show the same message whether or not the email has an account.</p></form>`));
SS.forms.recover=f=>{if(!/^[^@\s]+@[^@\s]+\.\S+$/.test(f.em.value)){f.em.setAttribute('aria-invalid','true');f.em.focus();toast('Enter a valid email');return}
  $('#main').innerHTML=authWrap('Check your email',`<div class="notice ok" role="status">${ico('check')}<span>If an account exists for <b>${esc(f.em.value)}</b>, a reset link is on its way. No email is actually sent in this prototype.</span></div><a class="btn" href="#/login">Back to sign in</a>`)};
SS.route(/^\/mfa$/,()=>authWrap('Two-step check',`<p>Privileged accounts need a second step. Enter the 6-digit code from your authenticator app.</p><form data-form="mfa" novalidate class="card"><div class="field"><label for="code">6-digit code</label><input id="code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" aria-describedby="ce"><div id="ce" class="err" hidden>${ico('alert','ico-sm')}Enter exactly 6 digits.</div></div><button class="btn block" type="submit">Verify</button><p class="small muted">Prototype: any 6 digits work.</p></form>`));
SS.forms.mfa=f=>{if(!/^\d{6}$/.test(f.code.value)){$('#ce').hidden=false;f.code.setAttribute('aria-invalid','true');f.code.focus();return}ST.mfaDone=true;ST.role=ST.pending||'moderator';location.hash={moderator:'#/mod',admin:'#/admin',analyst:'#/org'}[ST.role];toast('Verified. Signed in as '+SS.roles[ST.role])};

/* MY REPORTS */
SS.route(/^\/mine$/,()=>{
  const steps=['Received','Duplicate check','Moderator review','Outcome'];
  return `<h1>My reports</h1><p class="muted">${synth}</p>${SS.mine.length?`<div class="stack-s">${SS.mine.map(m=>`<article class="card"><div class="row between"><b class="mono">${esc(m.value)}</b><span class="small muted">${m.id} · ${m.when}</span></div><ol class="stepper" style="margin:12px 0 4px" aria-label="Progress">${steps.map((s,i)=>`<li class="${i<m.step?'done':i===m.step?'now':''}"></li>`).join('')}</ol><p class="small" style="margin:0"><b>${steps[Math.min(m.step,3)]}.</b> ${esc(m.out)}</p><div class="btn-row" style="margin-top:12px">${m.ind?`<a class="btn sm secondary" href="#/i/${m.ind}">View record</a>`:''}<button class="btn sm ghost" data-act="withdraw" data-id="${m.id}">Withdraw report</button></div></article>`).join('')}</div>`:`<div class="empty">${ico('list')}<h2>No reports yet</h2><p class="muted">When you report something, you can follow it here.</p><a class="btn" href="#/report">Report a scam</a></div>`}`;
});
SS.acts.withdraw=a=>SS.confirmDlg({title:'Withdraw this report?',body:'<p>Your report is removed from review. It will no longer count towards any record.</p>',confirm:'Withdraw',danger:true,onOk:()=>{const i=SS.mine.findIndex(m=>m.id===a.dataset.id);if(i>-1)SS.mine.splice(i,1);SS.render();toast('Report withdrawn')}});

/* CORRECTION */
SS.route(/^\/correct\/(I-\d+)$/,(q,id)=>{const i=getInd(id);
  return `<div style="max-width:680px;margin:0 auto" class="stack"><p class="small"><a href="#/i/${id}">&larr; Back to record</a></p><h1>Request a correction</h1><div class="card flat"><b class="mono">${esc(i.value)}</b><br>${statusChip(i)}</div><p class="muted">Tell us what is wrong. A moderator who did not handle the original review will look at it. Target response: 7 days. ${simTag}</p>
  <form data-form="correct" data-id="${id}" novalidate class="stack"><fieldset><legend>Your relationship to this record</legend><div class="choices">${['I own or legitimately use this number, site or account','I was named or impersonated and did nothing wrong','The record contains personal information','Legal or takedown request','Something else is inaccurate'].map((l,k)=>`<label class="choice"><input type="radio" name="why" value="${l}" ${k===0?'checked':''}>${l}</label>`).join('')}</div></fieldset>
  <div class="field"><label for="det">What is wrong?</label><textarea id="det" name="det" required aria-describedby="de"></textarea><div class="err" id="de" hidden>${ico('alert','ico-sm')}Explain in at least 20 characters.</div></div>
  ${field('ce','Contact email',{type:'email',hint:'Only moderators see this. Used to reply.'})}
  <label class="check"><input type="checkbox" name="ok"><span>I understand I may be asked to prove ownership, and false claims can lead to action.</span></label><button class="btn" type="submit">Send correction request</button></form></div>`;});
SS.forms.correct=f=>{const bad=f.det.value.trim().length<20;$('#de').hidden=!bad;if(bad){f.det.setAttribute('aria-invalid','true');f.det.focus();return}
  if(!/^[^@\s]+@[^@\s]+\.\S+$/.test(f.ce.value)){f.ce.setAttribute('aria-invalid','true');f.ce.focus();return}
  if(!f.ok.checked){toast('Please tick the confirmation box');return}
  const id='C-'+(79+SS.corrections.length);const ind=getInd(f.dataset.id);ind.flag=true;
  SS.corrections.unshift({id,ind:ind.id,by:'Requester (contact on file)',reason:f.why.value,detail:f.det.value,status:'open',when:'2026-11-27'});ind.hist.unshift(['2026-11-27','System','Correction request '+id+' opened']);audit('System','Correction request '+id+' opened on '+ind.id,'');
  $('#main').innerHTML=`<div class="stack" style="max-width:600px;margin:0 auto"><div class="notice ok" role="status">${ico('check')}<div><h1 style="margin:0 0 4px">Request received</h1><p style="margin:0">Reference <b class="mono">${id}</b>. We marked the record "Correction requested" while we check.</p></div></div><a class="btn" href="#/i/${ind.id}">Back to record</a></div>`;$('#main h1').focus()};

/* NOTIFICATIONS + SETTINGS */
SS.route(/^\/notifications$/,()=>{const p=ST.prefs;
  const sw=(g,k,l,sub)=>`<label class="switch"><span><b>${l}</b>${sub?`<br><span class="small muted">${sub}</span>`:''}</span><input type="checkbox" data-pref="${g}.${k}" ${p[g][k]?'checked':''} role="switch"></label>`;
  return `<h1>Notifications</h1><p>${simTag}</p><div class="grid g2"><section class="card"><h2>Categories to watch</h2>${sw('cats','reversal','Fake reversal / sent-by-mistake')}${sw('cats','phishing','Phishing links')}${sw('cats','invest','Investment and crypto scams')}${sw('cats','jobs','Fake job offers')}${sw('cats','tax','Tax-authority impersonation')}
  <h2 style="margin-top:20px">What to tell me</h2>${sw('ev','newthreat','New verified threats in my categories')}${sw('ev','campaign','Emerging campaigns')}${sw('ev','status','Status changes on records I reported')}${sw('ev','org','Updates from my organisation')}</section>
  <section class="card"><h2>How</h2><label class="switch"><span><b>Email</b><br><span class="small muted">Sent to a***@example.test (synthetic)</span></span><input type="checkbox" checked disabled></label><label class="switch" data-off><span><b>SMS</b><br><span class="small muted">Coming later, after sender-ID and provider verification</span></span><input type="checkbox" disabled></label><label class="switch" data-off><span><b>WhatsApp</b><br><span class="small muted">Coming later, after provider verification</span></span><input type="checkbox" disabled></label>
  <fieldset style="margin-top:16px"><legend>How often</legend><div class="choices">${[['instant','As it happens'],['daily','Daily summary'],['weekly','Weekly summary']].map(([k,l])=>`<label class="choice"><input type="radio" name="freq" value="${k}" data-pref="freq" ${p.freq===k?'checked':''}>${l}</label>`).join('')}</div></fieldset>
  <div class="row between"><span class="small muted" id="dirty" aria-live="polite">${ST.prefsDirty?'Unsaved changes':'All changes saved'}</span><button class="btn" data-act="saveprefs">Save preferences</button></div></section></div>
  <section class="card" style="margin-top:var(--sp-4)"><h2>Recent</h2><ul class="list"><li><b>New verified threat:</b> 0100 000 777 (delivery-fee scam) <span class="small muted">· today</span></li><li><b>Status change:</b> your report R-2030 is in moderator review <span class="small muted">· yesterday</span></li></ul></section>`;});
document.addEventListener('change',e=>{const k=e.target.dataset&&e.target.dataset.pref;if(!k)return;const p=ST.prefs;if(k==='freq')p.freq=e.target.value;else{const[g,n]=k.split('.');p[g][n]=e.target.checked}ST.prefsDirty=true;const dd=$('#dirty');if(dd)dd.textContent='Unsaved changes'});
SS.acts.saveprefs=b=>{b.disabled=true;b.innerHTML='<span class="spin"></span> Saving…';setTimeout(()=>{ST.prefsDirty=false;b.disabled=false;b.textContent='Save preferences';const dd=$('#dirty');if(dd)dd.textContent='All changes saved';toast('Preferences saved (simulated)')},600)};
SS.route(/^\/settings$/,()=>`<h1>Profile and settings</h1><p>${simTag}</p><div class="grid g2"><section class="card"><h2>Profile</h2><form data-form="profile" novalidate>${field('dn','Display name',{val:'Reporter A (synthetic)'})}${field('pe','Email',{type:'email',val:'a@example.test'})}<div class="field"><label for="lg">Language</label><select id="lg"><option>English</option><option>Kiswahili (draft)</option></select></div><button class="btn" type="submit">Save</button></form></section>
 <section class="card"><h2>Security</h2><p class="small">Two-step sign-in: <b>${['reporter'].includes(ST.role)?'Off (optional for reporters)':'On (required for your role)'}</b></p><button class="btn secondary" data-act="mfa-setup">Set up authenticator app</button><h2 style="margin-top:24px">Your data</h2><p class="small">Download or delete your reports and account under the Kenya Data Protection Act 2019.</p><div class="btn-row"><button class="btn secondary sm" data-act="exportme">Download my data</button><button class="btn danger sm" data-act="delme">Delete my account</button></div></section></div>`);
SS.forms.profile=f=>{if(!f.dn.value.trim()){f.dn.setAttribute('aria-invalid','true');f.dn.focus();return}toast('Profile saved (simulated)')};
SS.acts['mfa-setup']=()=>SS.confirmDlg({title:'Set up two-step sign-in',body:'<p>Scan a QR code with an authenticator app, then enter the code. (Simulated: no QR generated.)</p><div class="evid" style="max-width:160px">QR placeholder</div>',confirm:'Done',onOk:()=>toast('Two-step sign-in enabled (simulated)')});
SS.acts.exportme=()=>toast('Your data export would be emailed within 7 days (simulated)');
SS.acts.delme=()=>SS.confirmDlg({title:'Delete your account?',body:'<p>Your account and contact details are erased. Reports you made stay as anonymous evidence unless you withdraw them first.</p>',danger:true,confirm:'Delete account',reason:true,reasonLabel:'Why are you leaving? (optional text, min 8 characters)',onOk:()=>{ST.role='visitor';location.hash='#/';toast('Account deleted (simulated)')}});

/* STATES GALLERY */
SS.route(/^\/states$/,()=>`<h1>UI states gallery</h1><p class="muted">Reference for loading, empty, error, success, offline and limit states. ${simTag}</p><div class="grid g2">
<section class="card"><h2>Loading</h2>${SS.skeleton()}</section>
<section class="card"><h2>Empty</h2><div class="empty" style="padding:24px">${ico('list')}<h3>No reports yet</h3><p class="small muted">Reports you make will appear here.</p><a class="btn sm" href="#/report">Report a scam</a></div></section>
<section class="card"><h2>Error (recoverable)</h2><div class="notice err" role="alert">${ico('alert')}<div><b>We could not reach the lookup service.</b><br>Your search was not lost. <div style="margin-top:8px"><button class="btn sm" data-act="toast-ok">Try again</button></div></div></div></section>
<section class="card"><h2>Success</h2><div class="notice ok" role="status">${ico('check')}<span>Report received. Reference R-2101.</span></div></section>
<section class="card"><h2>Offline / slow data</h2><div class="notice warn">${ico('alert')}<span>You are offline. Your report is saved on this phone and will send when you are back online.</span></div></section>
<section class="card"><h2>Rate limited (API)</h2><div class="notice warn">${ico('alert')}<span>Too many requests. Try again in 30 seconds. HTTP 429 with a Retry-After header.</span></div></section>
<section class="card"><h2>Access restricted</h2><div class="notice info">${ico('lock')}<span>This area is for approved partner organisations. Request access from your organisation administrator.</span></div></section>
<section class="card"><h2>Partial data</h2><div class="notice info">${ico('info')}<span>Some counties are hidden because fewer than 5 reports could identify individuals.</span></div></section></div>`);
SS.acts['toast-ok']=()=>toast('Retrying (simulated)');
})();
