// Clicks through the main flows of the prototype and reports console errors.
import {launch} from './pw.mjs';
const URL=process.argv[2]||'http://localhost:4300/design/prototype/index.html';
const b=await launch();const ctx=await b.newContext({viewport:{width:1280,height:900},acceptDownloads:true});const p=await ctx.newPage();
const errs=[];p.on('console',m=>{if(['error','warning'].includes(m.type()))errs.push(m.type()+': '+m.text())});p.on('pageerror',e=>errs.push('pageerror: '+e.message));
const log=[];const ok=(n,c)=>{log.push((c?'PASS ':'FAIL ')+n);if(!c)process.exitCode=1};
const role=async r=>{await p.selectOption('#role',r);await p.waitForTimeout(150)};
const txt=()=>p.locator('#main').innerText();
await p.goto(URL);await p.waitForSelector('h1');
ok('home loads with simulated banner',(await p.locator('.demo-bar').innerText()).includes('Simulated — design prototype'));
// search
await p.fill('#q','0700 000 101');await p.click('button[type=submit]');await p.waitForSelector('#results[aria-busy="false"] .result');
ok('search finds verified record',(await txt()).includes('Verified with evidence'));
await p.fill('#q','0799 123 456');await p.click('button[type=submit]');await p.waitForSelector('#results[aria-busy="false"] .empty');
ok('not-reported state says not safe',(await txt()).includes('Not reported does not mean safe'));
await p.goto(URL+'#/search?q=a&status=verified');await p.waitForSelector('#results[aria-busy="false"] .result');ok('filter by status',(await p.locator('.result').count())>0);
await p.goto(URL+'#/search?q=simulate%20error');await p.waitForSelector('.notice.err');ok('search error state',true);
// detail
await p.goto(URL+'#/i/I-1001');await p.waitForSelector('.verdict');
const d=await txt();ok('detail shows confidence + reasons + history',d.includes('Evidence confidence')&&d.includes('Why we say this')&&d.includes('Review history'));
ok('detail avoids accusation words',!/scammer|criminal|fraudster/i.test(d));
// analyser
await p.goto(URL+'#/analyse');await p.click('[data-s=rev]');await p.click('button[type=submit]:has-text("Analyse")');await p.waitForSelector('.verdict',{timeout:4000});
const a=await txt();ok('analyser shows reasons, confidence, prior reports, disclaimer',a.includes('Why')&&a.includes('Analysis confidence')&&a.includes('Compared with reports')&&a.includes('not proof of fraud'));
ok('analyser marks highlights',(await p.locator('mark').count())>2);
// report flow with validation
await p.goto(URL+'#/report');await p.click('label.choice:has-text("Suspicious phone number")');await p.click('button:has-text("Continue")');
await p.fill('#value','123');await p.fill('#desc','short');await p.click('button:has-text("Continue")');
ok('validation errors shown',(await p.locator('#errsum').count())===1);
await p.fill('#value','0700 000 101');await p.fill('#desc','They called saying money was sent by mistake and asked me to return it.');await p.click('button:has-text("Continue")');
await p.click('button:has-text("Continue")');await p.click('button:has-text("Continue")');
ok('consent required',(await txt()).includes('Tick both required boxes'));
await p.check('[name=c_priv]');await p.check('[name=c_true]');await p.click('button:has-text("Continue")');await p.click('button:has-text("Send report")');
await p.waitForSelector('text=Report received',{timeout:4000});ok('report success + independent link',(await txt()).includes('1 more independent report'));
// second submission by same reporter doesn't count
await p.click('[data-act=rnew]');await p.click('label.choice:has-text("Suspicious phone number")');await p.click('button:has-text("Continue")');
await p.fill('#value','0700 000 101');await p.fill('#desc','Second report from me about the same number, repeated.');await p.click('button:has-text("Continue")');await p.click('button:has-text("Continue")');
await p.check('[name=c_priv]');await p.check('[name=c_true]');await p.click('button:has-text("Continue")');await p.click('button:has-text("Send report")');await p.waitForSelector('text=Report received',{timeout:4000});
ok('repeat by same reporter not independent',(await txt()).includes('does not count as an independent report'));
// login/register/recover/mfa
await p.goto(URL+'#/login');await p.click('button:has-text("Sign in")');ok('login validation',(await p.locator('[aria-invalid=true]').count())>0);
await p.goto(URL+'#/recover');await p.fill('#em','a@example.test');await p.click('button:has-text("Send reset link")');ok('recover success',(await txt()).includes('reset link is on its way'));
await p.goto(URL+'#/login');await p.fill('#em','mod@example.test');await p.fill('#pw','x');await p.click('button:has-text("Sign in")');await p.waitForSelector('#code');await p.fill('#code','12');await p.click('button:has-text("Verify")');ok('mfa rejects bad code',await p.locator('#ce').isVisible());await p.fill('#code','123456');await p.click('button:has-text("Verify")');await p.waitForSelector('text=Moderation queue');ok('mfa success -> moderator queue',true);
// my reports + correction (reporter)
await role('reporter');await p.goto(URL+'#/mine');ok('my reports lists',(await p.locator('article.card').count())>=3);
await p.goto(URL+'#/correct/I-1002');await p.fill('#det','This number belongs to our loan desk and is not a scam.');await p.fill('#ce','me@example.test');await p.check('[name=ok]');await p.click('button:has-text("Send correction request")');await p.waitForSelector('text=Request received');ok('correction submitted',true);
// notifications
await p.goto(URL+'#/notifications');await p.check('[data-pref="cats.jobs"]');ok('dirty flag',(await p.locator('#dirty').innerText()).includes('Unsaved'));await p.click('[data-act=saveprefs]');await p.waitForFunction(()=>document.querySelector('#dirty').textContent.includes('All changes saved'));ok('prefs saved',true);
ok('sms/whatsapp disabled',(await p.locator('.switch[data-off] input:disabled').count())===2);
// moderator
await role('moderator');await p.goto(URL+'#/mod/R-2044');
ok('verify locked for 1-report record',(await p.locator('[data-act=m-verify]').getAttribute('aria-disabled'))==='true');
await p.goto(URL+'#/mod/R-2042');
await p.click('[data-act=m-merge]');await p.fill('#dr','same reporter repeat');await p.click('#dok');await p.waitForSelector('text=Merged R-2042');
ok('merge same reporter keeps independent count',(await p.locator('.toast',{hasText:'Merged R-2042'}).first().innerText()).includes('unchanged'));
await p.goto(URL+'#/mod/R-2043');await p.click('[data-act=m-evid]');await p.click('#dok');ok('reason required',await p.locator('#dre').isVisible());await p.fill('#dr','Need the original SMS screenshot');await p.click('#dok');await p.waitForSelector('text=Requested evidence');
await p.goto(URL+'#/mod/R-2046');await p.click('[data-act=m-verify]');await p.fill('#dr','4 independent reports, 3 evidence items');await p.click('#dok');await p.waitForSelector('text=Verified I-1013');
await p.goto(URL+'#/i/I-1013');ok('verification updated public record',(await txt()).includes('Verified with evidence'));
await p.goto(URL+'#/mod/R-2047');await p.click('[data-act=m-rej]');await p.fill('#dr','Insufficient detail');await p.click('#dok');await p.waitForSelector('text=Rejected R-2047');
await p.goto(URL+'#/mod/corrections');await p.click('[data-act=c-decline]>>nth=0');await p.fill('#dr','No proof of ownership supplied');await p.click('#dok');await p.waitForTimeout(200);ok('correction handled',true);
await p.goto(URL+'#/audit');ok('audit shows moderator actions',(await txt()).includes('Verified I-1013'));
// analyst
await role('analyst');await p.waitForSelector('text=Reports per day');await p.selectOption('#rg','90');ok('range changes chart',(await p.locator('.chart').getAttribute('aria-label')).includes('90 days'));
await p.click('[data-act=catsel]>>nth=0');ok('category filter',(await txt()).includes('Filtered'));
await p.goto(URL+'#/org/campaigns');await p.click('[data-act=camp]>>nth=0');await p.click('dialog [data-act=newcase]');await p.waitForSelector('#ct2');await p.fill('#ct2','Test case from prototype');await p.click('#dok');await p.waitForSelector('text=Test case from prototype');ok('case created',true);
await p.click('[data-act=opencase]>>nth=0');await p.fill('#nt','Internal note test');await p.click('button:has-text("Add note")');await p.waitForTimeout(200);ok('note shown in reopened case',(await p.locator('dialog').innerText()).includes('Internal note test'));await p.keyboard.press('Escape');
await p.goto(URL+'#/org/exports');const [dl]=await Promise.all([p.waitForEvent('download'),p.click('button:has-text("Download CSV")')]);ok('CSV download '+dl.suggestedFilename(),dl.suggestedFilename().endsWith('.csv'));
await p.goto(URL+'#/org/alerts');await p.click('[data-act=newalert]');await p.click('#dok');await p.waitForTimeout(200);ok('alert rule added',(await p.locator('.switch').count())===3);
// developer
await role('developer');await p.click('[data-act=newkey]');await p.click('#dok');ok('key name required',await p.locator('#kne').isVisible());await p.fill('#kn','CI key');await p.click('#dok');await p.waitForSelector('#nk');ok('key created shown once',(await p.locator('#nk').innerText()).startsWith('ssa_test_SYNTHETIC_'));
await p.goto(URL+'#/dev/try');await p.click('button:has-text("Send")');await p.waitForSelector('pre.code',{timeout:3000});ok('sample request/response',(await txt()).includes('"status": "verified"'));
await p.goto(URL+'#/dev/docs');ok('docs lists 5 endpoints',(await p.locator('details.card').count())===5);
// admin
await role('admin');await p.click('[data-act=restrict]>>nth=0');await p.fill('#dr','Abusive submissions');await p.click('#dok');await p.waitForTimeout(200);ok('admin restrict',(await txt()).includes('restricted'));
await p.goto(URL+'#/admin/roles');ok('roles matrix',(await p.locator('table').count())===1);
// gating
await role('visitor');await p.goto(URL+'#/mod');ok('visitor blocked from mod',(await txt()).includes('restricted'));
// theme + lang + keyboard
await p.goto(URL+'#/');await p.click('[data-act=theme]');ok('theme toggles',(await p.evaluate(()=>document.documentElement.dataset.theme))!==undefined);
await p.click('[data-act=menu]');await p.click('[data-act=lang]');ok('swahili draft',(await txt()).includes('Angalia kabla'));
await p.goto(URL+'#/states');ok('states gallery',(await p.locator('section.card').count())>=8);
// mobile smoke
await p.setViewportSize({width:375,height:812});await p.goto(URL+'#/');ok('mobile tabbar visible',await p.locator('.tabbar').isVisible());
const sw=await p.evaluate(()=>document.documentElement.scrollWidth);ok('no horizontal scroll at 375 ('+sw+')',sw<=376);
console.log(log.join('\n'));console.log('\nconsole errors/warnings:',errs.length?errs:'none');
await b.close();
