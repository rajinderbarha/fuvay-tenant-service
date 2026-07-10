/**
 * Playwright global setup: log in once per role and save storageState.
 * The loginViaUi helper reads these cached states to avoid repeated
 * login API calls that exhaust the rate limit (100 req / 900s).
 */
import { chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { SUPER_ADMIN, TENANT_OWNER, TENANT_READONLY } from './api';

const APP = (process.env.E2E_APP || 'admin') as 'admin' | 'tenant';
const BASE_URL = APP === 'tenant' ? 'http://localhost:3001' : 'http://localhost:3000';
const STATE_DIR = path.join(__dirname, '..', '..', '.auth');

async function saveState(email: string, password: string, file: string) {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.addInitScript(() => {
    window.localStorage.setItem('serviceos_disable_tour_e2e', 'true');
    window.localStorage.setItem('serviceos-tenant-tour-done', 'true');
  });

  await page.goto(`${BASE_URL}/login`);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();

  await page.waitForURL(
    url => !url.pathname.includes('/login') && !url.pathname.includes('/change-password'),
    { timeout: 20_000 }
  );
  await page.waitForTimeout(500);

  await context.storageState({ path: file });
  await browser.close();
  console.log(`[global-setup] saved auth state: ${path.basename(file)}`);
}

export default async function globalSetup() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });

  if (APP === 'admin') {
    await saveState(SUPER_ADMIN.email, SUPER_ADMIN.password, path.join(STATE_DIR, 'admin.json'));
  } else {
    await saveState(TENANT_OWNER.email, TENANT_OWNER.password, path.join(STATE_DIR, 'tenant-owner.json'));
    await saveState(TENANT_READONLY.email, TENANT_READONLY.password, path.join(STATE_DIR, 'tenant-readonly.json'));
  }
}
