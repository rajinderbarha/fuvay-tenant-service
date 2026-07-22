const { chromium } = require('playwright');

const TOKEN = process.env.UX05_TOKEN;
const STAFF_ID = process.env.UX05_STAFF_ID;
const TENANT_ID = process.env.UX05_TENANT_ID;
const NAME = "Technician Two";

let shotN = 0;
async function shot(page, name) {
  const path = `/tmp/ux05_review3_${shotN++}_${name}.png`;
  try { await page.screenshot({ path, fullPage: true }); console.log(`SHOT: ${name} -> ${path}`); }
  catch (e) { console.log(`SHOT FAILED: ${name}: ${e.message}`); }
}
async function dump(page, label) {
  try {
    const text = await page.evaluate(() => document.body.innerText);
    console.log(`--- TEXT [${label}] ---\n${text.slice(0, 1200)}\n--- END ---`);
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
    await page.waitForTimeout(3000);
    await shot(page, 'home');
    await dump(page, 'home');
  }, 'Load app + Home (technician with real jobs)');

  await step(async () => {
    const t = page.locator('text=/my work/i').first();
    if (await t.count() > 0) { await t.click({ force: true }); await page.waitForTimeout(1500); }
    await shot(page, 'my_work_all');
    await dump(page, 'my_work_all');
  }, 'My Work — All');

  await step(async () => {
    const t = page.locator('text=/^today$/i').first();
    if (await t.count() > 0) { await t.click({ force: true, timeout: 8000 }); await page.waitForTimeout(1200); }
    await shot(page, 'my_work_today');
    await dump(page, 'my_work_today');
  }, 'My Work — Today filter');

  let jobOpenedFrom = null;
  await step(async () => {
    // Look for job card text patterns (job_number often like AC-... or similar); fall back to any card in the list
    const anyCard = page.locator('div[role="button"], [class*="Card"], text=/service|job|AC |plumb/i').first();
    if (await anyCard.count() > 0) {
      await anyCard.click({ force: true, timeout: 8000 });
      await page.waitForTimeout(1500);
      jobOpenedFrom = 'my_work';
    }
    await shot(page, 'job_open_attempt_from_mywork');
    await dump(page, 'job_open_attempt_from_mywork');
  }, 'Open a job from My Work');

  await step(async () => {
    const t = page.locator('text=/schedule/i').first();
    if (await t.count() > 0) { await t.click({ force: true }); await page.waitForTimeout(1200); }
    await shot(page, 'schedule');
    await dump(page, 'schedule');
  }, 'Schedule tab');

  await step(async () => {
    const t = page.locator('text=/alert|notification/i').first();
    if (await t.count() > 0) { await t.click({ force: true }); await page.waitForTimeout(1200); }
    await shot(page, 'notifications');
    await dump(page, 'notifications');
  }, 'Notifications/Alerts tab');

  await step(async () => {
    const t = page.locator('text=/profile/i').first();
    if (await t.count() > 0) { await t.click({ force: true }); await page.waitForTimeout(1200); }
    await shot(page, 'profile_light');
    await dump(page, 'profile_light');
  }, 'Profile (light)');

  await step(async () => {
    const t = page.locator('text=/dark mode|light mode|theme/i').first();
    if (await t.count() > 0) { await t.click({ force: true, timeout: 8000 }); await page.waitForTimeout(1000); }
    await shot(page, 'profile_dark');
    await dump(page, 'profile_dark');
  }, 'Toggle dark mode');

  console.log('\n=== CONSOLE ERRORS ===\n', JSON.stringify(consoleErrors, null, 2));
  console.log('=== PAGE ERRORS ===\n', JSON.stringify(pageErrors, null, 2));
  console.log('JOB_OPENED_FROM:', jobOpenedFrom);

  await browser.close();
})();
