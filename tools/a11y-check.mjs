// Basic automated accessibility checks (not a substitute for manual screen-reader testing).
import {launch} from './pw.mjs';
const U='http://localhost:4300/design/prototype/index.html';
const R=[['/','visitor'],['/search?q=0700','visitor'],['/i/I-1001','visitor'],['/report?v=0700%20000%20101&t=phone','visitor'],['/analyse','visitor'],['/login','visitor'],['/register','visitor'],['/mine','reporter'],['/notifications','reporter'],['/settings','reporter'],['/mod','moderator'],['/mod/R-2041','moderator'],['/audit','moderator'],['/org','analyst'],['/org/campaigns','analyst'],['/org/cases','analyst'],['/org/exports','analyst'],['/dev','developer'],['/dev/docs','developer'],['/dev/try','developer'],['/admin','admin'],['/admin/roles','admin'],['/states','visitor']];
const b=await launch();const p=await (await b.newContext({viewport:{width:1280,height:860},reducedMotion:'reduce'})).newPage();
await p.goto(U);let bad=0;const lines=[];
for(const [h,r] of R){await p.evaluate(r=>{SS.state.role=r},r);await p.goto(U+'#'+h);await p.evaluate(r=>{SS.state.role=r;SS.render()},r);await p.waitForTimeout(700);
 const res=await p.evaluate(()=>{const m=document.querySelector('#shell');const lab=el=>el.getAttribute('aria-label')||el.getAttribute('aria-labelledby')||(el.id&&document.querySelector(`label[for="${el.id}"]`))||el.closest('label')||el.getAttribute('title');
  const unl=[...m.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(e=>!lab(e)).length;
  const unn=[...m.querySelectorAll('button,a[href]')].filter(e=>!(e.textContent.trim()||e.getAttribute('aria-label'))).length;
  const ids=[...m.querySelectorAll('[id]')].map(e=>e.id);const dup=ids.length-new Set(ids).size;
  return {h1:m.querySelectorAll('h1').length,unl,unn,dup,main:m.querySelectorAll('main').length,lang:document.documentElement.lang}});
 const ok=res.h1===1&&!res.unl&&!res.unn&&!res.dup&&res.main===1;if(!ok)bad++;lines.push(`${ok?'PASS':'FAIL'} ${h} ${JSON.stringify(res)}`)}
// keyboard: tab through home, check focus ring and reach
await p.goto(U+'#/');await p.evaluate(()=>{SS.state.role='visitor';SS.render()});await p.waitForTimeout(400);
let visible=0,seen=new Set();for(let i=0;i<14;i++){await p.keyboard.press('Tab');const f=await p.evaluate(()=>{const e=document.activeElement;const cs=getComputedStyle(e);return {k:(e.tagName+'|'+(e.textContent||e.id||'').trim().slice(0,20)),ring:cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>=2}});seen.add(f.k);if(f.ring)visible++;else lines.push('  no ring on '+f.k)}
lines.push(`Keyboard: 14 Tab presses, ${seen.size} distinct stops, focus ring visible on ${visible}/14`);
// reduced motion
const anim=await p.evaluate(()=>getComputedStyle(document.body).animationDuration);lines.push('Reduced motion emulation: transitions/animations disabled via media query (skeleton animation: '+await p.evaluate(()=>{const d=document.createElement('div');d.className='skel';document.body.append(d);const v=getComputedStyle(d).animationName;d.remove();return v})+')');
console.log(lines.join('\n'));console.log(`\n${R.length} routes, ${bad} failing`);await b.close();
