// UX-05 manual review script — drives the real technician workflow via Playwright/Chromium
// against a real Expo web build, for a genuine usability + pipeline-integrity review.
const { chromium } = require('playwright');

const shots = [];
async function shot(page, name) {
  const path = `/tmp/ux05_review_${shots.length}_${name}.png`;
  await page.screenshot({ path, fullPage: true });
  shots.push({ name, path });
  console.log(`SHOT: ${name} -> ${path}`);
}

async function textDump(page, label) {
  const text = await page.evaluate(() => document.body.innerText);
  console.log(`--- TEXT DUMP [${label}] ---`);
  console.log(text.slice(0, 2000));
  console.log('--- END DUMP ---');
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const consoleErrors = [];
  const pageErrors = [];
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } }); // iPhone-ish portrait
  const page = await context.newPage();
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(err.message));

  console.log('=== STEP: Load app ===');
  await page.goto('http://localhost:3030', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);
  await shot(page, '01_initial_load');
  await textDump(page, 'initial');

  console.log('=== STEP: Login as technician ===');
  // Try to find email/password fields generically
  const emailInput = page.locator('input[type="email"], input[placeholder*="mail" i]').first();
  const passInput = page.locator('input[type="password"], input[placeholder*="assword" i]').first();
  if (await emailInput.count() > 0) {
    await emailInput.fill('staff@serviceos.local');
    await passInput.fill('Password123!');
    await shot(page, '02_login_filled');
    const loginBtn = page.locator('text=/log ?in/i').first();
    await loginBtn.click();
    await page.waitForTimeout(3000);
  } else {
    console.log('WARNING: no email input found on load');
  }
  await shot(page, '03_after_login');
  await textDump(page, 'after_login');

  console.log('=== STEP: Home screen — current/next job ===');
  await shot(page, '04_home');
  await textDump(page, 'home');

  console.log('=== STEP: Navigate to My Work ===');
  const myWorkTab = page.locator('text=/my work/i').first();
  if (await myWorkTab.count() > 0) {
    await myWorkTab.click();
    await page.waitForTimeout(1500);
  }
  await shot(page, '05_my_work');
  await textDump(page, 'my_work');

  console.log('=== STEP: Filter today ===');
  const todayFilter = page.locator('text=/^today$/i').first();
  if (await todayFilter.count() > 0) {
    await todayFilter.click();
    await page.waitForTimeout(1000);
  }
  await shot(page, '06_my_work_today_filter');

  console.log('=== STEP: Open a job ===');
  const jobCard = page.locator('[testID="pipeline-badge"], text=/ServiceJob/i').first();
  let openedJob = false;
  if (await jobCard.count() > 0) {
    await jobCard.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1500);
    openedJob = true;
  } else {
    console.log('WARNING: no job card found to open');
  }
  await shot(page, '07_job_detail');
  await textDump(page, 'job_detail');

  console.log('=== STEP: Dark mode check (Profile > theme toggle) ===');
  const profileTab = page.locator('text=/profile/i').first();
  if (await profileTab.count() > 0) {
    await profileTab.click();
    await page.waitForTimeout(1000);
    await shot(page, '08_profile_light');
    const themeToggle = page.locator('text=/dark|theme/i').first();
    if (await themeToggle.count() > 0) {
      await themeToggle.click().catch(() => {});
      await page.waitForTimeout(1000);
      await shot(page, '09_profile_dark_toggled');
    }
  }

  console.log('=== CONSOLE ERRORS ===');
  console.log(JSON.stringify(consoleErrors, null, 2));
  console.log('=== PAGE ERRORS ===');
  console.log(JSON.stringify(pageErrors, null, 2));

  await browser.close();
})();
