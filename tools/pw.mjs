// Shared Playwright launcher. Set PW_DIR to a folder containing node_modules/playwright (npm i playwright there).
// Optionally set CHROME to a Chromium executable path.
import os from 'os';import fs from 'fs';import path from 'path';
const PW=process.env.PW_DIR;if(!PW)throw new Error('Set PW_DIR to a folder containing node_modules/playwright');
const {chromium}=await import(path.join(PW,'node_modules/playwright/index.mjs'));
const cache=path.join(os.homedir(),'Library/Caches/ms-playwright');
const guess=()=>{try{const d=fs.readdirSync(cache).find(x=>/^chromium-\d+$/.test(x));return d&&path.join(cache,d,'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')}catch(e){}};
export const launch=()=>chromium.launch({executablePath:process.env.CHROME||guess()});
