const { chromium } = require('playwright');
const https = require('http');

function loginNode() {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({email: 'admin@serviceos.in', password: 'Password123!'});
    const req = https.request('http://localhost:8000/v1/auth/login', {
      method: 'POST', headers: {'Content-Type': 'application/json', 'Content-Length': data.length}
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => resolve(JSON.parse(body)));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

(async () => {
  const loginRes = await loginNode();
  const token = loginRes.data.access_token;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  await page.addInitScript((tok) => {
    localStorage.setItem('serviceos_admin_token', tok);
    // try to suppress onboarding tour if it's driven by a localStorage flag
    localStorage.setItem('serviceos_onboarding_tour_dismissed', 'true');
    localStorage.setItem('onboarding_tour_completed', 'true');
    localStorage.setItem('command_center_tour_seen', 'true');
  }, token);

  await page.goto('http://localhost:3000/admin/home-services/service-jobs/9ac88101-caf9-4e21-94c9-7c8d5a5fca88', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1500);

  // Try clicking "Skip tour" if present
  const skipBtn = await page.$('text=Skip tour');
  if (skipBtn) { await skipBtn.click(); await page.waitForTimeout(500); }

  await page.screenshot({ path: '/tmp/job_page_clean.png', fullPage: false });

  const tabButtons = await page.$$eval('[role="tab"]', els => els.map(e => e.textContent));
  console.log('TAB_BUTTONS:', JSON.stringify(tabButtons));

  await browser.close();
})();
