const { chromium } = require('playwright');

const TOKEN = process.env.UX05_TOKEN;
const STAFF_ID = process.env.UX05_STAFF_ID;
const TENANT_ID = process.env.UX05_TENANT_ID;
const NAME = "Technician Two";

let shotN = 0;
async function shot(page, name) {
  const path = `/tmp/ux05_review4_${shotN++}_${name}.png`;
  try { await page.screenshot({ path, fullPage: true }); console.log(`SHOT: ${name} -> ${path}`); }
  catch (e) { console.log(`SHOT FAILED: ${name}: ${e.message}`); }
}
async function dump(page, label) {
  try {
    const text = await page.evaluate(() => document.body.innerText);
    console.log(`--- TEXT [${label}] ---\n${text.slice(0, 1500)}\n--- END ---`);
  } catch (e) { console.log(`DUMP FAILED [${label}]: ${e.message}`); }
}
async function step(fn, label) {
  console.log(`\n=== STEP: ${label} ===`);
  try { await fn(); } catch (e) { console.log(`STEP FAILED [${label}]: ${e.message}`); }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const consoleErrors = [];
  const pageErrors = [];
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(err.message));

  await page.addInitScript(([token, staffId, tenantId, name]) => {
    localStorage.setItem('serviceos_staff_token', token);
    localStorage.setItem('serviceos_staff_id', staffId);
    localStorage.setItem('serviceos_tenant_id', tenantId);
    localStorage.setItem('serviceos_staff_name', name);
  }, [TOKEN, STAFF_ID, TENANT_ID, NAME]);

  await step(async () => {
    await page.goto('http://localhost:3030', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2500);
  }, 'Load app');

  await step(async () => {
    // Click directly on the "Needs Your Action" job card for L501-JOB-0001
    const card = page.locator('text=L501-JOB-0001').first();
    await card.click({ force: true, timeout: 8000 });
    await page.waitForTimeout(1500);
    await shot(page, 'assigned_job_detail');
    await dump(page, 'assigned_job_detail');
  }, 'Open Assigned job L501-JOB-0001');

  await step(async () => {
    // Look for accept/reject or a next-status-transition button
    const acceptBtn = page.locator('text=/^accept job$/i').first();
    if (await acceptBtn.count() > 0) {
      console.log('Found Accept button, clicking...');
      await acceptBtn.click({ force: true, timeout: 8000 });
      await page.waitForTimeout(1500);
    } else {
      console.log('No Accept button found -- looking for other next-action buttons');
    }
    await shot(page, 'after_accept_attempt');
    await dump(page, 'after_accept_attempt');
  }, 'Accept the job (first status transition)');

  await step(async () => {
    // Look for "On the way" / next transition button now
    const btns = await page.locator('button, [role="button"], div[dir="auto"]').allTextContents();
    console.log('Visible text nodes after accept attempt:', JSON.stringify(btns.filter(t => t && t.length < 40).slice(0, 60)));
  }, 'Enumerate visible action labels');

  console.log('\n=== CONSOLE ERRORS ===\n', JSON.stringify(consoleErrors, null, 2));
  console.log('=== PAGE ERRORS ===\n', JSON.stringify(pageErrors, null, 2));

  await browser.close();
})();
