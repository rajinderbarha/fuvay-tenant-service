const { chromium } = require('playwright');
const http = require('http');

function loginNode() {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({email: 'admin@serviceos.in', password: 'Password123!'});
    const req = http.request('http://localhost:8000/v1/auth/login', {
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
  const netLog = [];
  page.on('response', async res => {
    if (res.url().includes('/review')) {
      let body = '';
      try { body = await res.text(); } catch(e) {}
      netLog.push({ url: res.url(), status: res.status(), body: body.slice(0, 500) });
    }
  });
  await page.addInitScript((tok) => {
    localStorage.setItem('serviceos_admin_token', tok);
  }, token);

  await page.goto('http://localhost:3000/admin/home-services/service-jobs/9ac88101-caf9-4e21-94c9-7c8d5a5fca88', { waitUntil: 'networkidle', timeout: 30000 });
  const skipBtn = await page.$('text=Skip tour');
  if (skipBtn) { await skipBtn.click(); await page.waitForTimeout(300); }

  // click Review & Feedback tab
  await page.click('text=Review & Feedback');
  await page.waitForTimeout(2000);

  console.log('NETWORK_LOG:', JSON.stringify(netLog, null, 2));

  const bodyText = await page.textContent('body');
  const idx = bodyText.indexOf('Review');
  console.log('BODY_AROUND_REVIEW:', bodyText.slice(Math.max(0, idx-50), idx+500));

  await page.screenshot({ path: '/tmp/review_tab.png', fullPage: true });
  await browser.close();
})();
