const { chromium } = require('playwright');
const TOKEN = process.env.UX05_TOKEN;
const STAFF_ID = process.env.UX05_STAFF_ID;
const TENANT_ID = process.env.UX05_TENANT_ID;

let shotN = 0;
async function shot(page, name) {
  const path = `/tmp/ux05_review5_${shotN++}_${name}.png`;
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

  // Click bottom-tab Profile (5th tab icon row, avoid the stack push we hit before)
  const profileTab = page.locator('text=/^profile$/i').last();
  await profileTab.click({ force: true, timeout: 8000 });
  await page.waitForTimeout(1200);
  await shot(page, 'profile_light');

  const toggle = page.locator('text=/dark mode|switch to dark|theme/i').first();
  const found = await toggle.count();
  console.log('Theme toggle found:', found);
  if (found > 0) {
    await toggle.click({ force: true, timeout: 8000 });
    await page.waitForTimeout(1000);
    await shot(page, 'profile_dark');
  }

  // Now test offline behavior: go back to Home, then simulate offline
  const homeTab = page.locator('text=/^home$/i').last();
  await homeTab.click({ force: true, timeout: 8000 }).catch(e => console.log('home click failed', e.message));
  await page.waitForTimeout(1000);
  await context.setOffline(true);
  await page.waitForTimeout(1000);
  await page.reload({ waitUntil: 'load', timeout: 20000 }).catch(e => console.log('offline reload note:', e.message));
  await page.waitForTimeout(2000);
  await shot(page, 'offline_state');
  const offlineText = await page.evaluate(() => document.body.innerText).catch(() => '(failed to read)');
  console.log('--- OFFLINE STATE TEXT ---\n' + offlineText.slice(0, 800));

  await context.setOffline(false);
  await browser.close();
})();
