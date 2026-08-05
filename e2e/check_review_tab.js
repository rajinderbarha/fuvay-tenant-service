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
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push('PAGEERROR: ' + err.message));
  page.on('requestfailed', req => errors.push('REQFAIL: ' + req.url() + ' ' + req.failure()?.errorText));

  await page.addInitScript((tok) => {
    localStorage.setItem('serviceos_admin_token', tok);
  }, token);

  await page.goto('http://localhost:3000/admin/home-services/service-jobs/9ac88101-caf9-4e21-94c9-7c8d5a5fca88', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);

  const bodyText = await page.textContent('body');
  console.log('HAS_REVIEW_TAB:', bodyText.includes('Review & Feedback'));
  console.log('HAS_JOB_SUMMARY:', bodyText.includes('Job Summary'));
  console.log('HAS_JOB_NOT_FOUND:', bodyText.includes('Job not found'));
  console.log('BODY_SNIPPET:', bodyText.slice(0, 800));
  console.log('CONSOLE_ERRORS:', JSON.stringify(errors.slice(0, 15), null, 2));

  await page.screenshot({ path: '/tmp/job_page.png', fullPage: true });
  await browser.close();
})();
