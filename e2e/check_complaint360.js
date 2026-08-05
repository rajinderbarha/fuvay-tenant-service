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
  await page.addInitScript((tok) => { localStorage.setItem('serviceos_admin_token', tok); }, token);
  await page.goto('http://localhost:3000/admin/home-services/complaints/00000000-0000-0000-0000-000000000000', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  const skip = await page.$('text=Skip tour');
  if (skip) { await skip.click(); await page.waitForTimeout(300); }
  const bodyText = await page.textContent('body');
  console.log('HAS_BACK_LINK:', bodyText.includes('Back to Complaints'));
  console.log('HAS_TABS:', bodyText.includes('Job Context') && bodyText.includes('Evidence') && bodyText.includes('Conversation'));
  await page.screenshot({ path: '/tmp/complaint360.png', fullPage: true });
  await browser.close();
})();
