const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1300 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('response', r => { if (r.status() >= 400) errors.push('HTTP ' + r.status() + ' ' + r.url()); });
  await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], input[name="email"]', 'admin@serviceos.local');
  await page.fill('input[type="password"], input[name="password"]', 'Password123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  await page.goto('http://localhost:3000/admin/master-services', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const skip = await page.$('text=Skip tour');
  if (skip) { await skip.click(); await page.waitForTimeout(500); }
  await page.waitForTimeout(2000);
  console.log('ERRORS:', JSON.stringify(errors));
  await page.screenshot({ path: 'C:/Users/AIVIQT~1/AppData/Local/Temp/claude/g--serviceos/801c33fd-0cb7-440b-b373-18d797169700/scratchpad/master_services.png', fullPage: true });
  await browser.close();
})();
