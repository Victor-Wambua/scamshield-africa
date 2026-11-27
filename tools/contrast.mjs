// WCAG 2.x contrast check of palette token pairs. Run: node tools/contrast.mjs
import fs from 'fs';
const t=JSON.parse(fs.readFileSync('design/design-tokens.json','utf8')).color;
const lum=h=>{const c=[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255).map(v=>v<=.03928?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]};
const cr=(a,b)=>{const[x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return (x+.05)/(y+.05)};
const pairs=[['ink','bg',4.5],['ink','surface',4.5],['ink2','bg',4.5],['ink2','surface',4.5],['ink2','surface2',4.5],['brand','bg',4.5],['brand','surface',4.5],['brandInk','brand',4.5],['brandSoftInk','brandSoft',4.5],['accentInk','accent',4.5],['riskHigh','riskHighBg',4.5],['riskMed','riskMedBg',4.5],['ok','okBg',4.5],['unknown','unknownBg',4.5],['info','infoBg',4.5],['riskHigh','surface',4.5],['ok','surface',4.5],['focus','bg',3],['focus','surface',3],['line','bg',1],['ink','riskHighBg',4.5],['ink','riskMedBg',4.5]];
let fail=0,out=[];
for(const th of ['light','dark'])for(const [f,b,min] of pairs){const r=cr(t[th][f],t[th][b]);const ok=r>=min;if(!ok&&min>1)fail++;if(min>1)out.push(`${th.padEnd(5)} ${f} on ${b}: ${r.toFixed(2)} (need ${min}) ${ok?'PASS':'FAIL'}`)}
console.log(out.join('\n'));console.log(`\n${out.length} pairs, ${fail} failing`);
