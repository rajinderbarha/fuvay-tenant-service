const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle', timeout: 30000 });
  await page.fill('input[placeholder="Enter your email or mobile number"]', 'provider@serviceos.in');
  await page.fill('input[placeholder="Enter your password"]', 'DevOwner123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);
  await page.goto('http://localhost:3001/home-services/dispatch', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);
  const skip = await page.$('text=Skip tour');
  if (skip) { await skip.click(); await page.waitForTimeout(500); }
  await page.click('text=JOB-20260729-000004');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'C:/Users/AIVIQT~1/AppData/Local/Temp/claude/g--serviceos/a23ec8bc-eea0-4408-a4db-3f68a7a34e07/scratchpad/dispatch_panel.png', fullPage: true });
  await browser.close();
})();
