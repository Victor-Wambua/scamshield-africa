/* SYNTHETIC DEMONSTRATION DATA. Numbers, domains, wallets and names are invented. */
window.SS = window.SS || {};
SS.TYPES = {phone:'Phone number',url:'Website / link',email:'Email address',wallet:'Wallet address',social:'Social account',pay:'Payment reference',biz:'Business name'};
SS.CATS = ['Fake reversal / sent-by-mistake','Phishing link','Tax-authority impersonation','Investment scam','Advance-fee loan','Fake job offer','Fake online shop','Delivery-fee scam','Prize / lottery'];
SS.STATUS = {verified:'Verified with evidence',unverified:'Reported, unverified',review:'Under review',disputed:'Correction requested'};
SS.ind = [
 {id:'I-1001',type:'phone',value:'0700 000 101',cat:SS.CATS[0],status:'verified',risk:'high',conf:91,reports:14,raw:19,evidence:9,first:'2026-09-03',last:'2026-11-24',source:'Public reports + moderator review',camp:'C1',reasons:['14 independent reporters describe the same story: a call or SMS saying money was sent by mistake and asking for it back.','9 pieces of evidence (screenshots, message text) were checked by a moderator.','The same number appears in a campaign with 2 linked websites.'],hist:[['2026-11-20','Moderator M-07','Marked verified with evidence (14 independent reports, 9 evidence items)'],['2026-10-02','System','Linked 6 repeat reports from the same reporters; counted once'],['2026-09-03','System','First report received']]},
 {id:'I-1002',type:'phone',value:'0700 000 214',cat:SS.CATS[4],status:'unverified',risk:'med',conf:48,reports:3,raw:5,evidence:2,first:'2026-10-19',last:'2026-11-22',source:'Public reports',camp:null,reasons:['3 independent reports mention an upfront "processing fee" before a loan is released.','Evidence has not been checked by a moderator yet.'],hist:[['2026-11-22','System','Third independent report received'],['2026-10-19','System','First report received']]},
 {id:'I-1003',type:'url',value:'pesa-reversal-help.example',cat:SS.CATS[1],status:'verified',risk:'high',conf:88,reports:11,raw:13,evidence:7,first:'2026-09-07',last:'2026-11-23',source:'Public reports + moderator review',camp:'C1',reasons:['The page asks visitors to type an M-PESA PIN, which a genuine service never asks for on a web page.','11 independent reports; 7 screenshots show the same page.','The domain was registered recently (synthetic example signal).'],hist:[['2026-11-01','Moderator M-03','Marked verified with evidence'],['2026-09-07','System','First report received']]},
 {id:'I-1004',type:'url',value:'safaricom-bonus-claim.test',cat:SS.CATS[8],status:'review',risk:'med',conf:35,reports:2,raw:2,evidence:1,first:'2026-11-12',last:'2026-11-21',source:'Public reports',camp:null,reasons:['2 independent reports describe a "bonus" link sent by SMS.','Only one evidence item so far; a moderator is reviewing it.'],hist:[['2026-11-21','System','Sent to moderation queue']]},
 {id:'I-1005',type:'email',value:'support@kra-refund-notice.example',cat:SS.CATS[2],status:'verified',risk:'high',conf:76,reports:6,raw:6,evidence:4,first:'2026-10-05',last:'2026-11-18',source:'Public reports + moderator review',camp:'C2',reasons:['6 independent reporters received an email claiming a tax refund and asking for ID and bank details.','The sender domain does not match any official tax authority domain.'],hist:[['2026-11-02','Moderator M-07','Marked verified with evidence']]},
 {id:'I-1006',type:'wallet',value:'0xSYNTH000000000000000000000000000000AB12',cat:SS.CATS[3],status:'unverified',risk:'med',conf:52,reports:4,raw:4,evidence:3,first:'2026-10-28',last:'2026-11-20',source:'Public reports',camp:'C4',reasons:['4 independent reports were told to send crypto to this address for a "guaranteed return".','Wallet activity is not checked by this prototype; a real system would link public chain data.'],hist:[['2026-11-20','System','Fourth independent report received']]},
 {id:'I-1007',type:'social',value:'@quick_forex_ke (synthetic profile)',cat:SS.CATS[3],status:'disputed',risk:'med',conf:40,reports:5,raw:6,evidence:2,first:'2026-09-30',last:'2026-11-10',source:'Public reports',camp:'C4',flag:true,reasons:['5 reports mention forex "signals" with promised daily profit.','The account holder has asked for a correction. The record is being re-checked and wording is softened until then.'],hist:[['2026-11-22','System','Correction request C-77 opened'],['2026-09-30','System','First report received']]},
 {id:'I-1008',type:'phone',value:'0711 000 330',cat:SS.CATS[0],status:'unverified',risk:'none',conf:20,reports:1,raw:1,evidence:0,first:'2026-11-25',last:'2026-11-25',source:'Public reports',camp:null,reasons:['Only 1 report and no evidence yet. This is not enough to say anything about this number.'],hist:[['2026-11-25','System','First report received']]},
 {id:'I-1009',type:'url',value:'jobs-abroad-visa.example',cat:SS.CATS[5],status:'verified',risk:'high',conf:82,reports:8,raw:9,evidence:6,first:'2026-08-22',last:'2026-11-15',source:'Public reports + partner feed (synthetic)',camp:'C3',reasons:['8 independent reports describe a site charging a "visa processing fee" for overseas jobs.','Matches a partner-supplied indicator reviewed by a moderator.'],hist:[['2026-10-10','Moderator M-03','Marked verified with evidence']]},
 {id:'I-1010',type:'biz',value:'Bright Horizon Agro Ltd (synthetic)',cat:SS.CATS[6],status:'unverified',risk:'med',conf:30,reports:2,raw:2,evidence:1,first:'2026-11-08',last:'2026-11-19',source:'Public reports',camp:null,reasons:['2 reports say someone used this business name to take deposits. This may be impersonation of a real business, so no conclusion is drawn about any person.'],hist:[['2026-11-19','System','Second independent report received']]},
 {id:'I-1011',type:'pay',value:'Till 000000 (synthetic)',cat:SS.CATS[6],status:'unverified',risk:'med',conf:44,reports:3,raw:3,evidence:2,first:'2026-11-02',last:'2026-11-21',source:'Public reports',camp:null,reasons:['3 independent reports paid this till for goods that never arrived.'],hist:[['2026-11-21','System','Third independent report received']]},
 {id:'I-1012',type:'phone',value:'0100 000 777',cat:SS.CATS[7],status:'verified',risk:'high',conf:79,reports:7,raw:8,evidence:5,first:'2026-10-14',last:'2026-11-22',source:'Public reports + moderator review',camp:'C5',reasons:['7 independent reports describe a "parcel held, pay delivery fee" message.','5 evidence items checked.'],hist:[['2026-11-05','Moderator M-07','Marked verified with evidence']]},
 {id:'I-1013',type:'url',value:'shop-deals-nairobi.test',cat:SS.CATS[6],status:'unverified',risk:'med',conf:55,reports:4,raw:4,evidence:3,first:'2026-11-01',last:'2026-11-23',source:'Public reports',camp:null,reasons:['4 independent reports paid for items from this site and received nothing.'],hist:[['2026-11-23','System','Fourth independent report received']]},
 {id:'I-1014',type:'email',value:'winner@prize-draw.example',cat:SS.CATS[8],status:'unverified',risk:'med',conf:33,reports:2,raw:2,evidence:1,first:'2026-11-10',last:'2026-11-18',source:'Public reports',camp:null,reasons:['2 reports of an unexpected "you have won" email asking for a fee.'],hist:[['2026-11-18','System','Second independent report received']]}
];
SS.queue = [
 {id:'R-2041',ind:'I-1002',reporter:'rep-2291',ev:2,when:'2026-11-26 08:10',prio:'normal',status:'new',text:'Caller said my loan of KES 20,000 was approved but I must first send KES 1,500 "processing fee" to this number. I did not send. (synthetic report)',dups:['I-1002']},
 {id:'R-2042',ind:'I-1002',reporter:'rep-2291',ev:1,when:'2026-11-26 08:44',prio:'normal',status:'new',text:'Same number called me again with the same loan fee story. (synthetic report, same reporter as R-2041)',dups:['I-1002'],sameRep:true},
 {id:'R-2043',ind:'I-1004',reporter:'rep-1180',ev:1,when:'2026-11-26 09:02',prio:'high',status:'new',text:'SMS: "You have received a Safaricom bonus, claim: safaricom-bonus-claim.test". (synthetic report)',dups:['I-1004']},
 {id:'R-2044',ind:'I-1008',reporter:'rep-3302',ev:0,when:'2026-11-26 09:15',prio:'low',status:'new',text:'Got a call from 0711 000 330 saying money was sent in error. No screenshot. (synthetic report)',dups:['I-1008','I-1001']},
 {id:'R-2045',ind:'I-1006',reporter:'rep-4410',ev:3,when:'2026-11-25 17:30',prio:'normal',status:'evidence',text:'Telegram group admin asked me to send crypto to the address for a 3x return. (synthetic report)',dups:['I-1006']},
 {id:'R-2046',ind:'I-1013',reporter:'rep-5521',ev:3,when:'2026-11-25 15:12',prio:'normal',status:'new',text:'Paid KES 4,200 for a phone at shop-deals-nairobi.test. Nothing delivered, chat blocked. (synthetic report)',dups:['I-1013']},
 {id:'R-2047',ind:'I-1010',reporter:'rep-6633',ev:1,when:'2026-11-24 12:00',prio:'normal',status:'new',text:'A person used the name Bright Horizon Agro to ask me for a KES 5,000 "supplier deposit". The real company says it did not contact me. (synthetic report)',dups:['I-1010']}
];
SS.corrections = [
 {id:'C-77',ind:'I-1007',by:'Account holder (identity check pending)',reason:'I run a genuine forex education page',detail:'My profile is educational and makes no profit promises. Please remove the label. (synthetic request)',status:'open',when:'2026-11-22'},
 {id:'C-78',ind:'I-1010',by:'Business representative (documents attached)',reason:'Our business name is being impersonated',detail:'We are not the source of these messages and ask that the record says so clearly. (synthetic request)',status:'open',when:'2026-11-24'}
];
SS.mine = [
 {id:'R-1990',type:'url',value:'jobs-abroad-visa.example',when:'2026-10-09',step:3,out:'Linked to verified record I-1009',ind:'I-1009'},
 {id:'R-2030',type:'phone',value:'0700 000 214',when:'2026-11-18',step:2,out:'In moderator review',ind:'I-1002'},
 {id:'R-2039',type:'email',value:'winner@prize-draw.example',when:'2026-11-26',step:1,out:'Received. Checking for duplicates',ind:'I-1014'}
];
SS.camps = [
 {id:'C1',name:'Fake M-PESA reversal (call + link)',cat:SS.CATS[0],inds:['I-1001','I-1003'],reports:25,trend:'up',first:'2026-09-03',counties:'Nairobi, Kiambu, Mombasa'},
 {id:'C2',name:'Tax refund email wave',cat:SS.CATS[2],inds:['I-1005'],reports:6,trend:'up',first:'2026-10-05',counties:'Nairobi, Nakuru'},
 {id:'C3',name:'Overseas job fees',cat:SS.CATS[5],inds:['I-1009'],reports:8,trend:'flat',first:'2026-08-22',counties:'Nairobi, Kisumu, Uasin Gishu'},
 {id:'C4',name:'Forex and crypto "guaranteed returns"',cat:SS.CATS[3],inds:['I-1006','I-1007'],reports:9,trend:'up',first:'2026-09-30',counties:'Nairobi, Mombasa'},
 {id:'C5',name:'Parcel delivery fee',cat:SS.CATS[7],inds:['I-1012'],reports:7,trend:'down',first:'2026-10-14',counties:'Nairobi, Machakos'}
];
SS.cases = [
 {id:'K-201',title:'Investigate C1 call numbers for telco escalation',camp:'C1',status:'Investigating',owner:'Analyst A. (synthetic)',notes:[['2026-11-24','Analyst A.','Shared the verified phone indicator with the telco fraud desk contact. Awaiting reply.']]},
 {id:'K-202',title:'Customer complaints citing pesa-reversal-help.example',camp:'C1',status:'Open',owner:'Analyst B. (synthetic)',notes:[]}
];
SS.counties = [['Nairobi',142],['Mombasa',61],['Kisumu',38],['Nakuru',33],['Kiambu',29],['Uasin Gishu',22],['Machakos',17],['Kajiado',4],['Lamu',2]];
SS.alerts = [{id:'A1',cat:'Fake M-PESA reversal / sent-by-mistake',ch:'Email',on:true},{id:'A2',cat:'Investment and crypto scams',ch:'Email',on:false}];
SS.keys = [{id:'K1',name:'Fraud desk lookup (test)',env:'test',prefix:'ssa_test_SYNTH…7f2c',scopes:['lookup'],created:'2026-11-10',last:'2026-11-26',state:'active'}];
SS.users = [
 {id:'U-101',name:'Reporter A (synthetic)',email:'a@example.test',role:'Registered reporter',state:'active',mfa:'Off'},
 {id:'U-102',name:'Contributor B (synthetic)',email:'b@example.test',role:'Verified contributor',state:'active',mfa:'On'},
 {id:'U-103',name:'Moderator M-07 (synthetic)',email:'m07@example.test',role:'Moderator',state:'active',mfa:'On'},
 {id:'U-104',name:'Analyst A. (synthetic)',email:'analyst@bank.example',role:'Organization analyst',state:'active',mfa:'On'},
 {id:'U-105',name:'Reporter X (synthetic)',email:'x@example.test',role:'Registered reporter',state:'restricted',mfa:'Off'}
];
SS.audit = [
 {t:'2026-11-26 09:20',who:'M-07',act:'Verified indicator I-1001',reason:'14 independent reports, 9 evidence items',h:'a91c…'},
 {t:'2026-11-26 08:02',who:'System',act:'Linked repeat report R-2042 to R-2041 (same reporter)',reason:'Counts once',h:'7be2…'},
 {t:'2026-11-25 16:40',who:'Admin AD-01',act:'Approved organization "Example Bank (synthetic)"',reason:'Partner agreement ref PA-3',h:'03dd…'}
];
SS.roles = {visitor:'Visitor',reporter:'Registered reporter',moderator:'Moderator',analyst:'Organization analyst',developer:'Developer (org)',admin:'Platform administrator'};
SS.series = Array.from({length:90},(_,i)=>Math.round(18+i*0.28+8*Math.sin(i/3.2)+((i*37)%11)));
