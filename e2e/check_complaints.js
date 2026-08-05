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
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [];
  const netFailures = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('response', res => { if (res.status() >= 400 && res.url().includes('localhost:8000')) netFailures.push(res.status() + ' ' + res.url()); });
  await page.addInitScript((tok) => { localStorage.setItem('serviceos_admin_token', tok); }, token);

  await page.goto('http://localhost:3000/admin/home-services/complaints', { waitUntil: 'networkidle', timeout: 30000 });
  const skip = await page.$('text=Skip tour');
  if (skip) { await skip.click(); await page.waitForTimeout(300); }
  await page.waitForTimeout(1500);

  const bodyText = await page.textContent('body');
  console.log('HAS_TITLE:', bodyText.includes('Home Services Complaints'));
  console.log('HAS_BANNER:', bodyText.includes('Central queue'));
  console.log('HAS_KPI_ESCALATED:', bodyText.includes('Escalated'));
  console.log('HAS_ADD_COMPLAINT_BUTTON:', bodyText.includes('Add Complaint'));
  console.log('PAGE_ERRORS:', JSON.stringify(errors.slice(0,5)));
  console.log('NET_FAILURES:', JSON.stringify(netFailures.slice(0,10)));
  await page.screenshot({ path: '/tmp/complaints_queue.png', fullPage: true });

  await browser.close();
})();
