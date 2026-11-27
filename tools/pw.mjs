// Shared Playwright launcher. Set PW_DIR to a folder whose node_modules contains playwright.
const PW=process.env.PW_DIR||'/path/to/playwright-dir';
const {chromium}=await import(PW+'/node_modules/playwright/index.mjs');
export const launch=()=>chromium.launch({executablePath:process.env.CHROME||'/Users/<you>/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'});
