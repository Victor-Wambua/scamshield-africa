// Generates grayscale, annotated wireframes (HTML) into design/wireframes/. Run: node tools/build-wireframes.mjs
import fs from 'fs';
const OUT='design/wireframes';fs.mkdirSync(OUT,{recursive:true});
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const a=(n,h)=>`<div class="a"><i class="pin">${n}</i>${h}</div>`;
const H=t=>`<div class="h">${esc(t)}</div>`, T=t=>`<div class="t">${esc(t)}</div>`, S=t=>`<div class="t s">${esc(t)}</div>`;
const B=(t,p)=>`<div class="b ${p?'p':''}">${esc(t)}</div>`, I=(l,ph='')=>`<div class="i"><label>${esc(l)}</label><div class="in">${esc(ph)}</div></div>`;
const BX=(t,h=80)=>`<div class="bx" style="height:${h}px">${esc(t)}</div>`, CH=t=>`<span class="ch">${esc(t)}</span>`;
const ROW=(...x)=>`<div class="r">${x.join('')}</div>`, COL=(...x)=>`<div class="c" style="--n:${x.length}">${x.map(y=>`<div>${y}</div>`).join('')}</div>`;
const LI=a=>`<ul class="l">${a.map(x=>`<li>${x}</li>`).join('')}</ul>`;
const TB=(h,rows)=>`<table class="tb"><tr>${h.map(x=>`<th>${esc(x)}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</table>`;
const TAB=(...x)=>`<div class="tabs">${x.map((y,i)=>`<span class="${i?'':'on'}">${esc(y)}</span>`).join('')}</div>`;
const CHART=(t,h=110)=>`<div class="bx chart" style="height:${h}px"><svg viewBox="0 0 200 60" preserveAspectRatio="none"><polyline points="0,50 25,40 50,44 75,30 100,34 125,20 150,24 175,12 200,16" fill="none" stroke="#555" stroke-width="2"/></svg><span>${esc(t)}</span></div>`;
const DLG=(t,...x)=>`<div class="scrim"><div class="dlg"><div class="h">${esc(t)}</div>${x.join('')}</div></div>`;
const demo=`<div class="demo">Simulated — design wireframe · synthetic demonstration data</div>`;
const dtop=(items,on=0)=>`<div class="topbar"><b>◧ ScamShield</b>${items.map((x,i)=>`<span class="${i===on?'on':''}">${esc(x)}</span>`).join('')}<em>☾ ☰</em></div>`;
const side=(title,items,on=0)=>`<div class="topbar"><b>◧ ScamShield</b><span>${esc(title)}</span><em>☾ ☰</em></div><div class="shellrow"><div class="side">${items.map((x,i)=>`<span class="${i===on?'on':''}">${esc(x)}</span>`).join('')}</div><div class="pane">`;
const endside=`</div></div>`;
const mtop=`<div class="topbar m"><b>◧ ScamShield</b><em>☾ ☰</em></div>`;
const mtab=(items,on=0)=>`<div class="tabbar">${items.map((x,i)=>`<span class="${i===on?'on':''}">▢<br>${esc(x)}</span>`).join('')}</div>`;
const PUB=['Check','Report','Analyse','Sign in'], PUBM=['Check','Report','Analyse','Sign in'], REP=['Check','Report','Analyse','My reports','Alerts'];
const F=(dev,title,notes,body)=>({dev,title,notes,body});
const D=(title,notes,...b)=>F('d',title,notes,b.join('')), M=(title,notes,...b)=>F('m',title,notes,mtop+`<div class="mb">${b.join('')}</div>`);
const pages=[];
const P=(file,title,intro,frames)=>pages.push({file,title,intro,frames});

/* 1 AUTH */
P('01-auth','Login, register, password recovery, MFA','Public auth is minimal. Staff roles get a mandatory second step. Errors are inline and also summarised.',[
 M('Login (mobile)',['Single column, 48px fields, email OR phone accepted','Show/hide password toggle; never block paste','Forgot password link is always visible','Error text sits under the field and in a summary'],H('Sign in'),I('Email or phone','name@example.test'),I('Password','••••••••'),a(1,B('Sign in',1)),a(2,T('Forgot password? · Create account')),a(3,S('Error: Enter your email or phone and password')),demo),
 D('Login (desktop)',['Centered 440px card on the paper background','Same copy as mobile; no marketing panel to slow loading'],dtop(PUB,3),`<div class="narrow">`,H('Sign in'),I('Email or phone'),I('Password'),B('Sign in',1),T('Forgot password? · Create account'),`</div>`),
 D('Register',['Password strength meter with plain-language label','Required terms and privacy checkbox','Phone OR email, verified by one-time code (production)'],dtop(PUB,3),`<div class="narrow">`,H('Create an account'),I('Name'),I('Email or phone'),I('Password','At least 10 characters'),BX('Strength meter',14),'<div class="chk">☐ I accept the terms and privacy notice</div>',B('Create account',1),`</div>`),
 M('Password recovery',['Same confirmation shown whether or not the account exists (prevents account probing)','Link expires in 30 minutes (production)'],H('Reset your password'),I('Email'),B('Send reset link',1),BX('Success: If an account exists, a reset link is on its way',60)),
 D('MFA (privileged roles)',['Required for moderator, analyst, admin, org admin','6-digit authenticator code; recovery codes behind a link','Three failures lock for 5 minutes'],dtop(['Check'],-1),`<div class="narrow">`,H('Two-step check'),T('Enter the 6-digit code from your authenticator app.'),I('6-digit code','_ _ _ _ _ _'),B('Verify',1),S('Use a recovery code'),`</div>`)
]);
/* 2 ONBOARDING + HOME */
P('02-onboarding-home','Onboarding and public home','Mobile-first. The search box is the first thing; reporting is one tap away.',[
 M('Onboarding 1 of 3',['Three skippable cards shown once after registration','Explains the labels: reported, unverified, verified with evidence'],H('Check before you pay'),BX('illustration: phone + shield',120),T('Search a number, link or till. See what others reported and how well it is backed up.'),a(1,B('Next',1)),S('Skip')),
 M('Onboarding 2 of 3',['Sets expectation: not an accusation list'],H('Reports, not accusations'),BX('three chips: reported / unverified / verified',100),T('We show indicators and evidence, never names of people.'),B('Next',1)),
 M('Onboarding 3 of 3',['Opt-in email alerts (SMS/WhatsApp later)','Language choice English / Kiswahili'],H('Stay informed'),I('Alert email (optional)'),'<div class="chk">☐ New verified threats in my categories</div>',B('Done',1)),
 M('Public home (mobile)',['Search is the hero; type auto-detected','Quick actions as large cards','Verified warnings list with status chips','Bottom tab bar: Check, Report, Analyse, My reports/Sign in'],H('Check before you pay or reply.'),a(1,I('Number, link, email or till')),B('Search',1),ROW(CH('0700 000 101'),CH('pesa-reversal.example')),COL(B('Report a scam'),B('Analyse a message')),H('Verified warnings'),BX('result card · status chip · risk chip',60),BX('result card',60),mtab(PUBM,0)),
 D('Public home (desktop)',['Same content; three action cards in a row','Sidebar with "Stay safe" tips','Language and theme in header'],dtop(PUB,0),H('Check before you pay or reply.'),ROW('<div style="flex:1">'+I('Number, link, email or till')+'</div>',B('Search',1)),COL(BX('Report a scam',70),BX('Analyse a message',70),BX('How we label things',70)),`<div class="c" style="--n:2">`,'<div>'+H('Verified warnings this week')+BX('result card',50)+BX('result card',50)+'</div>','<div>'+BX('Stay safe tips',120)+'</div>','</div>')
]);
/* 3 SEARCH + DETAIL */
const rcard=(v,s,r)=>`<div class="bx" style="text-align:left;height:auto;padding:8px"><b>${v}</b> ${CH(s)}<br>${CH(r)} <span class="xs">n independent reports · updated date</span></div>`;
P('03-search-detail','Search results and indicator detail','Detail states: verified/high, unverified, under correction, not reported. Language never accuses a person.',[
 M('Search results (mobile)',['Filters collapse into a "Filter" sheet','Result card: value, status chip, risk chip, report count, last updated','Skeleton while loading'],I('Search','0700'),ROW(B('Type ▾'),B('Status ▾'),B('Risk ▾')),rcard('0700 000 101','Verified','Higher risk'),rcard('0700 000 214','Unverified','Some warning signs'),S('2 records · synthetic demonstration data'),mtab(PUBM,0)),
 D('Search results (desktop)',['Filters inline above the list','Results are links to the record'],dtop(PUB,0),I('Search','0700'),ROW(B('Type ▾'),B('Status ▾'),B('Risk ▾')),rcard('0700 000 101','Verified with evidence','Higher risk'),rcard('0700 000 214','Reported, unverified','Some warning signs')),
 M('No result: not reported',['"Not reported does not mean safe" is mandatory copy','Offers Report and Analyse','Safety steps listed'],H('No reports found'),T('Not reported does not mean safe.'),B('Report it',1),B('Analyse the message'),LI(['Do not send money','Call the official number'])),
 D('Detail: verified, higher risk',['1 Verdict banner states status and basis (counts, moderator-checked)','2 Why we say this: reasons in plain words','3 Evidence confidence with meter and "how it is worked out"','4 Record fields (type, risk category, first reported, last observed, independent reports, verification, source, ID)','5 Review history (moderator names hidden publicly)','6 Actions: add report, request correction','7 Safety advice'],dtop(PUB,0),H('0700 000 101'),ROW(CH('Phone'),CH('Verified with evidence'),CH('Higher risk')),a(1,BX('VERDICT: Reported as higher risk · 14 independent reports · moderator-checked evidence',50)),`<div class="c" style="--n:2">`,'<div>'+a(2,BX('Why we say this',70))+a(3,BX('Evidence confidence: High (91%) ▓▓▓▓▓▓▓▓░',60))+a(4,BX('Record details table',90))+a(5,BX('Review history timeline',70))+'</div>','<div>'+a(7,BX('What to do',80))+a(6,B('Add your report',1)+B('Request a correction'))+'</div>','</div>'),
 M('Detail: unverified',['Verdict banner is neutral, not alarming','Confidence low/medium with text "not proof"','Evidence count not shown publicly'],H('0700 000 214'),ROW(CH('Reported, unverified'),CH('Some warning signs')),BX('Banner: 3 reports so far. A moderator has not confirmed it.',60),BX('Why we say this',60),BX('Confidence: Medium (48%)',40),B('Add your report',1)),
 M('Detail: correction requested',['Chip changes to Correction requested','Wording softened until re-check completes','Visible history entry'],H('@quick_forex_ke (profile)'),ROW(CH('Correction requested')),BX('Banner: The owner asked for a correction. We are re-checking.',60),BX('Reasons (softened)',60)),
]);
/* 4 REPORT FLOW */
const stepper=n=>`<div class="stepper">${[0,1,2,3,4,5].map(i=>`<i class="${i<n?'d':i===n?'n':''}"></i>`).join('')}</div>`;
P('04-report-flow','Report flow (type, details, evidence, consent, review, confirmation)','Six steps on mobile and desktop. One question per screen on mobile. Drafts are kept in memory and (production) on device so a dropped connection does not lose work.',[
 M('1 Type (mobile)',['Eight type cards, 48px+ targets','No account required'],stepper(0),H('What do you want to report?'),...['Phone number or call','Link or fake website','Email','Scam message / payment request','Social account','Business impersonation','Wallet address','Investment-scam ad'].map(x=>BX('○ '+x,28)),B('Continue',1)),
 M('2 Details (mobile)',['Type-specific field and format hint','Inline validation; error summary on submit','Description minimum 20 characters, live counter'],stepper(1),H('Tell us what happened'),I('Phone number','0700 000 101'),I('What did they say or ask for?'),BX('textarea',70),I('When? (optional)'),I('Amount lost KES (optional)'),ROW(B('Back'),B('Continue',1))),
 M('3 Evidence (mobile)',['Camera or gallery; up to 5 images','Reminder to hide others personal data'],stepper(2),H('Add evidence'),BX('Choose photos',60),BX('Paste message text',80),'<div class="chk">☐ I removed personal details not part of the scam</div>',ROW(B('Back'),B('Continue',1))),
 M('4 Consent (mobile)',['Plain-language privacy summary','Two required checkboxes, two optional','Link to full notice'],stepper(3),H('Consent and privacy'),BX('What we publish: indicator + status. Never your name.',70),'<div class="chk">☐ Required: I read the privacy notice</div>','<div class="chk">☐ Required: what I wrote is true</div>','<div class="chk">☐ Optional: share with partners</div>','<div class="chk">☐ Optional: contact me</div>',ROW(B('Back'),B('Continue',1))),
 M('5 Review (mobile)',['Summary with edit links','Network error state keeps answers and offers retry'],stepper(4),H('Check your report'),BX('Summary table',110),S('Error: could not send. Your answers are saved.'),ROW(B('Back'),B('Send report',1))),
 M('6 Confirmation (mobile)',['Reference number','Duplicate handling explained','Prompt to create account for tracking'],stepper(5),BX('✔ Thank you. Reference R-2150',60),BX('What happens next: 1 duplicate check 2 linked/new record 3 moderator 4 email',100),B('Create an account to track it',1)),
 D('Report details (desktop)',['Two-column: form left, "what we publish" preview right','Same validation as mobile'],dtop(PUB,1),stepper(1),`<div class="c" style="--n:2">`,'<div>'+H('Tell us what happened')+I('Phone number')+I('What did they say or ask for?')+BX('textarea',80)+ROW(B('Back'),B('Continue',1))+'</div>','<div>'+BX('Public preview: how this will appear (no personal data)',200)+'</div>','</div>'),
 D('Review + consent (desktop)',['Consent and review shown as one page on desktop for speed (still validated as separate steps in the model)'],dtop(PUB,1),stepper(3),H('Consent and review'),COL(BX('Summary',140),BX('Consent checkboxes + privacy summary',140)),B('Send report',1)),
]);
/* 5 ANALYSER */
P('05-analyser','AI message analyser','Never states a message IS a scam. Always shows confidence level and reasons, and compares with prior reports. Prototype is a rule-based simulation.',[
 M('Analyser input (mobile)',['Paste box, sample messages, privacy hint','Label: Simulated in prototype; production names the model/version used'],H('Analyse a message'),BX('textarea: paste message',90),ROW(CH('Sample 1'),CH('Sample 2')),B('Analyse',1),demo),
 M('Analyser result (mobile)',['1 Summary: "Several warning signs" + confidence level and %','2 Message with warning phrases highlighted (colour + underline, not colour alone)','3 Why: one plain sentence per signal','4 Compared with reports: matching indicators','5 Disclaimer: automated guess, not proof'],a(1,BX('Several warning signs · confidence High 80%',50)),a(2,BX('Message with <mark> highlights',80)),a(3,BX('Why list',70)),a(4,BX('Matching records',50)),a(5,BX('Not proof of fraud. Never share PIN or code.',40)),ROW(B('Report this',1),B('Clear'))),
 D('Analyser (desktop)',['Input left, result right once run','Same content blocks'],dtop(PUB,2),COL(BX('Input + samples',200),BX('Result blocks 1-5',200))),
]);
/* 6 MY REPORTS + CORRECTION */
P('06-my-reports-correction','My reports, status tracking, challenge and correction','Everyone can challenge a record. A different moderator handles it. Status tracking shows each stage.',[
 M('My reports (mobile)',['Card per report with 4-stage progress bar','Withdraw and view record actions','Empty state when none'],H('My reports'),BX('R-2030 · 0700 000 214 · ▓▓░░ Moderator review',70),BX('R-2039 · email · ▓░░░ Received',70),B('Report a scam',1),mtab(['Check','Report','Analyse','My reports','Alerts'],3)),
 D('My reports (desktop)',['Same cards in two columns','Filter by status'],dtop(REP,3),H('My reports'),COL(BX('report card + progress',80),BX('report card + progress',80))),
 M('Request a correction',['Reason radio: owner / named or impersonated / personal info / legal / other','Explanation (min 20 chars)','Contact email (moderators only)','Acknowledgement checkbox about false claims'],H('Request a correction'),BX('Record summary',40),BX('○ I own this number or site  ○ I was impersonated  ○ Personal info  ○ Legal request',90),I('What is wrong?'),I('Contact email'),B('Send request',1)),
 M('Correction confirmation',['Reference, expected response time (7 days target)','Record flagged Correction requested immediately'],BX('✔ Request received · C-79',60),T('We marked the record while we check. A different moderator reviews it.'),B('Back to record')),
]);
/* 7 MODERATION */
P('07-moderation','Moderation: queue, review, duplicate merge, evidence request','Decisions need a reason and are audit-logged. Verify is locked until policy criteria are met and the reason is shown.',[
 D('Queue (desktop)',['1 KPI row','2 Filters: needs action / decided / search','3 Table with signals: same reporter, possible duplicate, priority'],side('Moderation',['Queue','Corrections','Audit log','Public check']),COL(BX('Waiting 7',40),BX('Evidence 1',40),BX('Corrections 2',40),BX('Median 1.8d',40)),a(2,ROW(I('Search'),B('Apply'))),a(3,TB(['Report','Indicator','Status','Signals','Evidence','Received'],[['R-2041','0700 000 214','New','','2','08:10'],['R-2042','0700 000 214','New',CH('Same reporter'),'1','08:44'],['R-2043','safaricom-bonus…','New',CH('Priority'),'1','09:02']])),endside),
 M('Queue (mobile)',['Table becomes cards with labelled rows'],H('Moderation queue'),BX('R-2041 · 0700 000 214 · New',60),BX('R-2042 · Same reporter chip',60),BX('R-2043 · Priority chip',60),mtab(['Queue','Corrections','Audit','Check','Alerts'],0)),
 D('Report review (desktop)',['1 Submitted report (pseudonymous reporter id)','2 Evidence thumbnails','3 Indicator record + counts','4 Possible duplicates','5 History','6 Decision panel: Verify (locked with reason), Mark unverified, Request evidence, Merge, Reject, Restrict reporter'],side('Moderation',['Queue','Corrections','Audit log']),`<div class="c" style="--n:2">`,'<div>'+a(1,BX('Submitted report',60))+a(2,BX('Evidence 1 · Evidence 2',60))+a(3,BX('Indicator record',70))+a(4,BX('Possible duplicates',60))+a(5,BX('History',50))+'</div>','<div>'+a(6,B('Verify with evidence',1)+B('Mark unverified')+B('Request more evidence')+B('Merge as duplicate')+B('Reject')+S('Verify is locked: needs 2 independent reporters and 1 checked evidence item'))+'</div>','</div>',endside),
 D('Duplicate merge dialog',['Choose target record','States effect on independent count','Same reporter: count unchanged, shown explicitly','Reason required'],side('Moderation',['Queue']),BX('(review page behind)',60),DLG('Merge as duplicate',T('Link R-2042 to an existing record.'),BX('○ 0700 000 214 · 3 independent reports',30),S('Same reporter: independent count stays 3'),I('Reason'),ROW(B('Cancel'),B('Merge',1))),endside),
 M('Request evidence (mobile sheet)',['Bottom sheet on mobile, dialog on desktop','Message template editable, reason logged'],BX('(review page behind)',60),DLG('Request more evidence',I('Message to reporter','Please add the original SMS screenshot'),ROW(B('Cancel'),B('Send',1)))),
 D('Corrections queue',['Accept, decline, or remove data (legal)','Remove data asks a second approver in production'],side('Moderation',['Queue','Corrections','Audit log'],1),BX('C-77 on @quick_forex_ke · requester statement · [Accept] [Decline] [Remove data]',80),BX('C-78 …',80),endside),
]);
/* 8 INSTITUTION */
const ORG=['Dashboard','Campaigns','Cases','Exports','Alert rules'];
P('08-institution','Institution dashboard: analytics, campaigns, cases, exports, alerts','Approved partners only. Aggregates respect a minimum group size of 5; no reporter identity is ever exposed.',[
 D('Analytics',['1 KPIs','2 Reports per day with range selector','3 Threat categories (click filters)','4 County table with small-number suppression'],side('Org',ORG,0),COL(BX('Reports 1,365',40),BX('Campaigns 5',40),BX('Verified 5',40),BX('Median 1.8d',40)),`<div class="c" style="--n:2">`,'<div>'+a(2,CHART('Reports per day ▾ 30 days'))+'</div>','<div>'+a(3,BX('Category bars',110))+'</div>','</div>',a(4,BX('County bars · <5 shown as "<5"',80)),endside),
 M('Analytics (mobile)',['KPIs 2x2','Charts full width, simplified labels'],H('Dashboard'),COL(BX('1,365',40),BX('5',40)),CHART('Reports per day',90),BX('Categories',90),mtab(['Dashboard','Campaigns','Cases','Exports','Alerts'],0)),
 D('Campaigns',['Rows link indicators into a campaign','Investigate dialog: linked indicators, create case'],side('Org',ORG,1),TB(['Campaign','Category','Reports','Trend','Areas',''],[['Fake M-PESA reversal','Reversal','25',CH('Rising'),'Nairobi, Kiambu',B('Investigate')],['Tax refund email wave','Tax','6',CH('Rising'),'Nairobi',B('Investigate')]]),endside),
 D('Case management',['Cases with owner and status','Internal notes visible only inside the organisation','Close/reopen'],side('Org',ORG,2),ROW(T('2 cases'),B('New case',1)),BX('K-201 · Investigating · [Open case and notes]',60),BX('K-202 · Open',60),endside),
 D('Exports',['Choose columns and scope; reporter data is never available','Export log records who, when, rows'],side('Org',ORG,3),COL(BX('Column checkboxes · scope select · [Download CSV]',160),BX('Export log',160)),endside),
 D('Alert subscriptions',['Rule = category + channel (email) + trigger','Toggle on/off; SMS and WhatsApp shown as later'],side('Org',ORG,4),BX('Fake reversal · Email · ON',40),BX('Investment · Email · OFF',40),B('New rule',1),endside),
]);
/* 9 DEV */
const DEVN=['API keys','Docs','Usage','Try a request'];
P('09-developer-portal','Developer portal: keys, docs, usage, try-it','Keys are shown once. Test keys return synthetic data; live keys need organisation approval.',[
 D('Keys',['1 Create key dialog: name, scopes, environment','2 Secret shown once with Copy','3 Table with prefix, scopes, last used, Revoke'],side('Developer',DEVN,0),a(2,BX('Key created. Copy it now. ssa_test_…',40)),a(1,B('Create key',1)),a(3,TB(['Name','Key','Env','Scopes','Last used','State'],[['Fraud desk lookup','ssa_test_…7f2c','test','lookup','2026-11-26','active']])),endside),
 D('API docs (OpenAPI-style)',['Endpoint list: lookup, report submission, incident status, threat-intel, org analytics','Parameters table, example response, error codes','Auth and rate limit up top'],side('Developer',DEVN,1),BX('Base URL · Bearer auth · 60 req/min',40),BX('▸ GET /v1/indicators/lookup',34),BX('▸ POST /v1/reports',34),BX('▸ GET /v1/reports/{id}/status',34),BX('▸ GET /v1/intel/threats',34),BX('▸ GET /v1/org/analytics',34),endside),
 D('Usage',['Requests per day, error rate, quota'],side('Developer',DEVN,2),COL(BX('3,412',40),BX('0.4%',40),BX('34% of quota',40)),CHART('Requests per day'),endside),
 M('Try a request (mobile)',['Pick endpoint, value, simulate 200/404/429','Shows curl and JSON response'],I('Endpoint'),I('Value'),I('Simulate response'),B('Send',1),BX('curl …',50),BX('{ "status": "verified" … }',80)),
]);
/* 10 NOTIF + SETTINGS */
P('10-notifications-settings','Notifications, preferences, profile and settings','Email first. SMS and WhatsApp are visibly disabled until provider verification.',[
 D('Notification preferences',['Categories, event types, channels, frequency','Dirty-state indicator and explicit Save','SMS / WhatsApp disabled with reason'],dtop(REP,4),COL(BX('Categories toggles · Event toggles',180),BX('Email ✔ · SMS (later) · WhatsApp (later) · Frequency · [Save]',180)),BX('Recent notifications',60)),
 M('Notification preferences (mobile)',['Single column; switches 48px'],H('Notifications'),BX('Categories',90),BX('Events',90),BX('Channels',90),B('Save preferences',1)),
 D('Profile and settings',['Profile, language, MFA setup, data download, delete account (reason dialog)'],dtop(REP,0),COL(BX('Profile form',160),BX('Security · Your data (download / delete)',160))),
]);
/* 11 ADMIN */
const ADM=['Users','Roles','Audit log','Moderation'];
P('11-platform-admin','Platform admin: users, roles, audit log','MFA required. All changes need a reason and write to an append-only log.',[
 D('Users',['Role change and restrict/restore, each with reason','MFA column'],side('Admin',ADM,0),TB(['User','Role','State','2-step',''],[['Reporter A','Registered reporter','active','Off',B('Change role')],['Moderator M-07','Moderator','active','On',B('Restrict')]]),endside),
 D('Roles matrix',['Permissions by role; read-only reference in v1'],side('Admin',ADM,1),BX('Permission × role matrix',160),endside),
 D('Audit log',['Time, actor, action, reason, chained hash','Filter by actor/date; export for regulators'],side('Admin',ADM,2),TB(['Time','Actor','Action','Reason','Hash'],[['09:20','M-07','Verified I-1001','14 reports','a91c…'],['08:02','System','Linked R-2042','Counts once','7be2…']]),endside),
]);
/* 12 STATES */
P('12-states','Empty, loading, error, success and offline states','Reusable patterns. Each has icon, plain sentence, and one next action.',[
 M('Empty',['Explains what will appear and offers the primary action'],BX('📄',40),H('No reports yet'),T('Reports you make will appear here.'),B('Report a scam',1)),
 M('Loading',['Skeleton shapes match final layout; aria-busy; no spinner-only screens'],BX('████████ title',24),BX('██████████████',18),BX('██████████',18)),
 M('Error',['Says what happened, that work is safe, and offers retry'],BX('⚠ We could not reach the lookup service. Your search was not lost.',60),B('Try again',1)),
 M('Success',['role=status; reference number shown'],BX('✔ Report received. Reference R-2150',60)),
 M('Offline / slow data',['Saved on device; sends when online'],BX('⚠ You are offline. Your report is saved and will send when you reconnect.',70)),
 D('Access restricted / partial data',['Role-gated pages explain who can see them','Aggregates explain suppression'],dtop(PUB,-1),BX('🔒 This area is for approved partner organisations',60),BX('ℹ Some counties are hidden: fewer than 5 reports',50)),
]);

/* ---------- render ---------- */
const css=`*{box-sizing:border-box}body{font:14px/1.4 Arial,Helvetica,sans-serif;color:#222;background:#e9e9e9;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px}p.intro{max-width:80ch;color:#444}.nav{margin:0 0 16px;font-size:13px}.nav a{margin-right:12px;color:#222}
.fig{display:flex;gap:20px;align-items:flex-start;margin:0 0 36px;flex-wrap:wrap}.fig h2{font-size:15px;margin:0 0 8px;width:100%}
.dev{background:#fff;border:2px solid #555;position:relative;overflow:hidden}.dev.d{width:880px}.dev.m{width:320px}
.notes{flex:1;min-width:240px;max-width:420px}.notes ol{padding-left:20px;margin:0}.notes li{margin:0 0 6px;font-size:13px}
.topbar{display:flex;gap:14px;align-items:center;padding:10px 14px;border-bottom:2px solid #555;background:#f3f3f3}.topbar b{margin-right:8px}.topbar span{padding:4px 10px;border-radius:14px}.topbar span.on{background:#cfcfcf;font-weight:700}.topbar em{margin-left:auto;font-style:normal}
.shellrow{display:flex}.side{width:150px;border-right:2px solid #555;padding:10px;background:#f7f7f7;min-height:300px}.side span{display:block;padding:7px 10px;border-radius:14px;margin-bottom:2px}.side span.on{background:#cfcfcf;font-weight:700}.pane{flex:1;padding:14px;min-width:0}
.mb{padding:12px;min-height:420px}.dev.d>.h,.dev.d>.t,.dev.d>.i,.dev.d>.r,.dev.d>.c,.dev.d>.bx,.dev.d>.b,.dev.d>.tb,.dev.d>.a,.dev.d>.stepper,.dev.d>.l,.dev.d>.narrow{margin-left:14px;margin-right:14px}
.h{font-size:18px;font-weight:700;margin:10px 0 8px}.t{margin:6px 0}.t.s,.xs,.s{font-size:12px;color:#555}
.b{display:inline-block;border:2px solid #444;border-radius:8px;padding:9px 14px;margin:4px 6px 4px 0;font-weight:700;background:#fff;min-width:80px;text-align:center}.b.p{background:#444;color:#fff}
.i{margin:8px 0}.i label{display:block;font-size:12px;font-weight:700;margin-bottom:3px}.in{border:2px solid #666;border-radius:8px;height:36px;padding:7px 9px;color:#888;font-size:12px;background:#fff}
.bx{border:2px dashed #888;background:#f2f2f2;margin:8px 0;display:flex;align-items:center;justify-content:center;text-align:center;padding:6px;font-size:12px;color:#444;border-radius:6px}
.bx.chart{position:relative}.bx.chart svg{position:absolute;inset:8px;width:calc(100% - 16px);height:calc(100% - 16px)}.bx.chart span{position:relative;background:#f2f2f2;padding:0 4px}
.ch{display:inline-block;border:1px solid #666;border-radius:12px;padding:1px 9px;font-size:12px;margin:2px 4px 2px 0;background:#fff}
.r{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap}.c{display:grid;grid-template-columns:repeat(var(--n),1fr);gap:12px}.c>div{min-width:0}
.l{margin:6px 0;padding-left:20px}.chk{margin:8px 0;font-size:13px}
.tb{border-collapse:collapse;width:calc(100% - 28px);font-size:12px;margin:8px 14px}.pane .tb{margin:8px 0;width:100%}.tb th,.tb td{border:1px solid #999;padding:6px 8px;text-align:left;vertical-align:top}.tb th{background:#ddd}
.tabs{display:flex;gap:4px;border-bottom:2px solid #888}.tabs span{padding:6px 12px}.tabs .on{border-bottom:3px solid #222;font-weight:700}
.stepper{display:flex;gap:4px;margin:6px 0}.stepper i{flex:1;height:7px;border-radius:4px;background:#ccc}.stepper i.d{background:#555}.stepper i.n{background:#999;outline:1px solid #333}
.tabbar{position:absolute;bottom:0;left:0;right:0;display:grid;grid-auto-flow:column;grid-auto-columns:1fr;border-top:2px solid #555;background:#f3f3f3;text-align:center;font-size:10px;padding:6px 0}.tabbar .on{font-weight:700;border-top:3px solid #222}
.dev.m{min-height:560px;padding-bottom:50px}.narrow{max-width:360px;margin:20px auto!important}
.a{position:relative}.pin{position:absolute;left:-2px;top:-2px;z-index:2;background:#222;color:#fff;border-radius:50%;width:18px;height:18px;font:700 11px/18px Arial;text-align:center;font-style:normal}
.scrim{position:absolute;inset:0;background:rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center}.dlg{background:#fff;border:2px solid #333;border-radius:10px;padding:14px;width:min(340px,90%)}
.demo{margin-top:10px;border:2px dashed #888;padding:4px 8px;font-size:11px;font-weight:700;text-align:center}.narrow .demo{margin-top:12px}`;
const nav=`<div class="nav">${pages.map(p=>`<a href="${p.file}.html">${p.file.slice(0,2)}</a>`).join('')}<a href="index.html">Index</a></div>`;
let frameCount=0;
for(const p of pages){
  const figs=p.frames.map((f,i)=>{frameCount++;return `<div class="fig"><h2>${p.file.slice(0,2)}.${i+1} ${esc(f.title)} <span class="s">(${f.dev==='d'?'desktop 880px':'mobile 320px'})</span></h2><div class="dev ${f.dev}">${f.body}</div><div class="notes"><b>Annotations</b><ol>${f.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ol></div></div>`}).join('');
  fs.writeFileSync(`${OUT}/${p.file}.html`,`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(p.title)} · wireframe</title><style>${css}</style><body>${nav}<h1>${esc(p.title)}</h1><p class="intro">${esc(p.intro)} Grayscale low-fidelity wireframe. Simulated design material, synthetic data.</p>${figs}</body></html>`);
}
fs.writeFileSync(`${OUT}/index.html`,`<!doctype html><html lang="en"><meta charset="utf-8"><title>Wireframes · ScamShield Africa</title><style>${css}</style><body><h1>ScamShield Africa wireframes</h1><p class="intro">${frameCount} annotated frames across ${pages.length} sheets. Open any sheet; PNG exports are in ./png.</p><ul>${pages.map(p=>`<li><a href="${p.file}.html">${p.file} ${esc(p.title)}</a> (${p.frames.length} frames)</li>`).join('')}</ul></body>`);
console.log(frameCount+' frames,'+pages.length+' sheets');
