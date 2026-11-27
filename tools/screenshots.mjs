import {launch} from './pw.mjs';
const U='http://localhost:4300/design/prototype/index.html';
const SHOTS=[
 ['home','',  'visitor'],['search','#/search?q=0700','visitor'],['indicator-verified','#/i/I-1001','visitor'],['indicator-unverified','#/i/I-1008','visitor'],
 ['report','#/report?v=0700%20000%20101&t=phone','visitor'],['analyser','#/analyse','visitor','analyse'],['my-reports','#/mine','reporter'],
 ['mod-queue','#/mod','moderator'],['mod-review','#/mod/R-2041','moderator'],['org-dashboard','#/org','analyst'],['org-cases','#/org/cases','analyst'],
 ['dev-keys','#/dev','developer'],['dev-docs','#/dev/docs','developer'],['notifications','#/notifications','reporter'],['admin-users','#/admin','admin'],['states','#/states','visitor']];
const b=await launch();let n=0;
for(const [dev,vp] of [['desktop',{width:1280,height:860}],['mobile',{width:390,height:844}]])for(const theme of ['light','dark']){
  const ctx=await b.newContext({viewport:vp,deviceScaleFactor:1,colorScheme:theme});const p=await ctx.newPage();
  await p.goto(U);await p.evaluate(t=>{SS.state.theme=t},theme);
  for(const [name,hash,role,act] of SHOTS){
    await p.evaluate(([r,t])=>{SS.state.role=r;SS.state.theme=t},[role,theme]);
    await p.goto(U+hash);await p.evaluate(([r,t])=>{SS.state.role=r;SS.state.theme=t;SS.render()},[role,theme]);
    if(act==='analyse'){await p.click('[data-s=rev]');await p.click('button:has-text("Analyse")');await p.waitForTimeout(1000)}
    await p.waitForTimeout(700);
    await p.screenshot({path:`design/screenshots/${name}-${dev}-${theme}.png`,fullPage:name==='states'||dev==='mobile'&&false});n++;
  }
  await ctx.close();
}
await b.close();console.log(n+' screenshots');
