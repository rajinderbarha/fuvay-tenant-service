const { chromium } = require('playwright');

const TOKEN = process.env.UX05_TOKEN;
const STAFF_ID = process.env.UX05_STAFF_ID;
const TENANT_ID = process.env.UX05_TENANT_ID;
const NAME = "Demo Staff";

let shotN = 0;
async function shot(page, name) {
  const path = `/tmp/ux05_review2_${shotN++}_${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`SHOT: ${name} -> ${path}`);
}
async function dump(page, label) {
  const text = await page.evaluate(() => document.body.innerText);
  console.log(`--- TEXT [${label}] ---\n${text.slice(0, 1500)}\n--- END ---`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const consoleErrors = [];
  const pageErrors = [];
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(err.message));

  // Inject a valid session BEFORE the app boots, bypassing the broken
  // /v1/auth/staff/login form so we can review the actual authenticated
  // screens against real data via the real (working) /v1/auth/me endpoint.
  await page.addInitScript(([token, staffId, tenantId, name]) => {
    localStorage.setItem('serviceos_staff_token', token);
    localStorage.setItem('serviceos_staff_id', staffId);
    localStorage.setItem('serviceos_tenant_id', tenantId);
    localStorage.setItem('serviceos_staff_name', name);
  }, [TOKEN, STAFF_ID, TENANT_ID, NAME]);

  console.log('=== Load app (with injected session) ===');
  await page.goto('http://localhost:3030', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  await shot(page, '01_home_authenticated');
  await dump(page, 'home');

  console.log('=== My Work ===');
  const myWorkTab = page.locator('text=/my work/i').first();
  if (await myWorkTab.count() > 0) { await myWorkTab.click(); await page.waitForTimeout(1500); }
  await shot(page, '02_my_work');
  await dump(page, 'my_work');

  console.log('=== Today filter ===');
  const todayChip = page.locator('text=/^today$/i').first();
  if (await todayChip.count() > 0) { await todayChip.click(); await page.waitForTimeout(1000); }
  await shot(page, '03_my_work_today');
  await dump(page, 'my_work_today');

  console.log('=== Open first job card ===');
  // Job cards render job_number / status text; click the first tappable card-like element
  const cards = page.locator('text=/JOB-|SJ-|#/').first();
  let jobOpened = false;
  if (await cards.count() > 0) {
    await cards.click({ timeout: 5000 }).catch(e => console.log('card click failed:', e.message));
    await page.waitForTimeout(1500);
    jobOpened = true;
  }
  await shot(page, '04_job_detail_or_fail');
  await dump(page, 'job_detail_attempt');
  console.log('JOB_OPENED:', jobOpened);

  console.log('=== Schedule tab ===');
  const scheduleTab = page.locator('text=/schedule/i').first();
  if (await scheduleTab.count() > 0) { await scheduleTab.click(); await page.waitForTimeout(1200); }
  await shot(page, '05_schedule');
  await dump(page, 'schedule');

  console.log('=== Notifications tab ===');
  const notifTab = page.locator('text=/notification/i').first();
  if (await notifTab.count() > 0) { await notifTab.click(); await page.waitForTimeout(1200); }
  await shot(page, '06_notifications');
  await dump(page, 'notifications');

  console.log('=== Profile + theme toggle (dark mode check) ===');
  const profileTab = page.locator('text=/profile/i').first();
  if (await profileTab.count() > 0) { await profileTab.click(); await page.waitForTimeout(1200); }
  await shot(page, '07_profile_light');
  await dump(page, 'profile');
  const themeToggle = page.locator('text=/dark mode|light mode|theme/i').first();
  if (await themeToggle.count() > 0) {
    await themeToggle.click().catch(e => console.log('theme toggle click failed:', e.message));
    await page.waitForTimeout(1000);
  }
  await shot(page, '08_profile_dark');
  await dump(page, 'profile_dark');

  console.log('=== CONSOLE ERRORS ===', JSON.stringify(consoleErrors, null, 2));
  console.log('=== PAGE ERRORS ===', JSON.stringify(pageErrors, null, 2));

  await browser.close();
})();
