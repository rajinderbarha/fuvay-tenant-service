const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle', timeout: 30000 });
  await page.fill('input[placeholder="Enter your email or mobile number"]', 'rajinderbarha@gmail.com');
  await page.fill('input[placeholder="Enter your password"]', 'DevOwner123!');
  await page.click('button[type="submit"]');
  await page.waitForURL(/.*/, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);
  console.log('URL after login:', page.url());

  await page.goto('http://localhost:3001/dashboard', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);
  const skip = await page.$('text=Skip tour');
  if (skip) { await skip.click(); await page.waitForTimeout(500); }
  console.log('Dashboard URL:', page.url());
  const bodyText = await page.textContent('body').catch(() => 'N/A');
  console.log('HAS_Needs_attention:', bodyText.includes('Needs attention'));
  console.log('HAS_Job_pipeline:', bodyText.includes('Job pipeline'));
  console.log('HAS_Todays_jobs:', bodyText.includes("Today's jobs"));
  console.log('HAS_Staff_capacity:', bodyText.includes('Staff capacity'));
  console.log('HAS_Finance_snapshot:', bodyText.includes('Finance snapshot'));
  console.log('PAGE_ERRORS:', JSON.stringify(errors.slice(0, 20)));
  await page.screenshot({ path: 'C:/Users/AIVIQT~1/AppData/Local/Temp/claude/g--serviceos/a23ec8bc-eea0-4408-a4db-3f68a7a34e07/scratchpad/dashboard.png', fullPage: true });
  await browser.close();
})();
