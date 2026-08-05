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
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  await page.addInitScript((tok) => { localStorage.setItem('serviceos_admin_token', tok); }, token);
  await page.goto('http://localhost:3000/admin/dashboard', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1000);
  const navText = await page.textContent('nav, aside').catch(() => 'N/A');
  console.log('CONTAINS_Bookings:', navText.includes('Bookings'));
  console.log('CONTAINS_Jobs:', navText.includes('Jobs'));
  console.log('CONTAINS_Customers:', navText.includes('Customers'));
  console.log('CONTAINS_Complaints:', navText.includes('Complaints'));
  console.log('CONTAINS_Operations_group:', navText.includes('OPERATIONS') || navText.includes('Operations'));
  console.log('PAGE_ERRORS:', JSON.stringify(errors));
  await page.screenshot({ path: '/tmp/nav_check.png', fullPage: true });
  await browser.close();
})();
