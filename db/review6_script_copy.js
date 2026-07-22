const { chromium } = require('playwright');
const TOKEN = process.env.UX05_TOKEN;
const STAFF_ID = process.env.UX05_STAFF_ID;
const TENANT_ID = process.env.UX05_TENANT_ID;

let shotN = 0;
async function shot(page, name) {
  const path = `/tmp/ux05_review6_${shotN++}_${name}.png`;
  await page.screenshot({ path, fullPage: true });
  console.log(`SHOT: ${name} -> ${path}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.addInitScript(([token, staffId, tenantId]) => {
    localStorage.setItem('serviceos_staff_token', token);
    localStorage.setItem('serviceos_staff_id', staffId);
    localStorage.setItem('serviceos_tenant_id', tenantId);
    localStorage.setItem('serviceos_staff_name', 'Technician Two');
  }, [TOKEN, STAFF_ID, TENANT_ID]);

  await page.goto('http://localhost:3030', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);

  const profileTab = page.locator('text=/^profile$/i').last();
  await profileTab.click({ force: true, timeout: 8000 });
  await page.waitForTimeout(1200);

  const darkBtn = page.locator('text=/^dark$/i').first();
  await darkBtn.click({ force: true, timeout: 8000 });
  await page.waitForTimeout(1000);
  await shot(page, 'profile_dark_mode');

  // Navigate to Home in dark mode to check global reactivity
  const homeTab = page.locator('text=/^home$/i').last();
  await homeTab.click({ force: true, timeout: 8000 });
  await page.waitForTimeout(1200);
  await shot(page, 'home_dark_mode');

  // My Work in dark mode
  const myWorkTab = page.locator('text=/my work/i').first();
  await myWorkTab.click({ force: true, timeout: 8000 });
  await page.waitForTimeout(1200);
  await shot(page, 'mywork_dark_mode');

  await browser.close();
})();
