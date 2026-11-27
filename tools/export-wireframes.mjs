import {launch} from './pw.mjs';import fs from 'fs';
const b=await launch();const p=await b.newPage({viewport:{width:1400,height:900}});fs.mkdirSync('design/wireframes/png',{recursive:true});
const files=fs.readdirSync('design/wireframes').filter(f=>/^\d\d-.*\.html$/.test(f));
for(const f of files){await p.goto('http://localhost:4300/design/wireframes/'+f);await p.screenshot({path:'design/wireframes/png/'+f.replace('.html','.png'),fullPage:true})}
console.log(files.length+' PNGs');await b.close();
