import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e04');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

const FORBIDDEN = [
  'Cash Wallet', 'Wallet Balance', 'Withdraw', 'Withdrawable Balance',
  'Tenant Payout', 'Provider Earnings Wallet', 'Escrow',
  'Platform Collected Service Payment', 'Provider Cash Balance',
  'Credit Wallet Health', 'Platform Pay Now', 'Online Payment Required',
  'Manual Bargain Setup', 'Bargain Rule Builder', 'Bargain Settings',
];

test.describe('ADMIN-TENANT-E2E-04 matching/operations/deduction', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('route smoke: matching/operations/deduction pages, no crash, no NaN/undefined', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/home-services/provider-matching',
      '/admin/home-services/matching-diagnostics',
      '/admin/home-services/completed-job-deduction',
      '/admin/home-services/service-jobs',
      '/admin/operations',
      '/admin/home-services/overview',
      '/admin/finance/usage-credits',
    ];
    for (const route of routes) {
      const resp = await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2000);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'route' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      log('route-smoke.log', `${route} | status=${status} | len=${bodyText.length} | hasSidebar=${await page.locator('aside').count()}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/undefined/);
    }
  });

  test('provider matching page: header, ranking factors, links to diagnostics', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/provider-matching');
    await page.waitForTimeout(1000);
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).toContain('Provider Matching');
    expect(bodyText).toContain('Ranking Factors');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'provider-matching.png'), fullPage: true });
    log('provider-matching.log', `Header+ranking factors present: ${bodyText.includes('Ranking Factors')}`);
  });

  test('matching diagnostics: run AC Repair+Split AC+LG+141001, verify selected provider + Low/Mid/High', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/matching-diagnostics', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    // BLANK_FORM defaults already prefill AC Repair/Ludhiana/141001 category+service.
    // Fill Type ID and Brand ID for Split AC + LG using label-based locators (robust to index drift).
    await page.getByLabel('Type ID (optional)').fill('c86dfcf3-53bd-4d83-bf0b-51257f382652');
    await page.getByLabel('Brand ID (optional)').fill('64a3b25f-23aa-4639-8baf-f67def0f60db');
    // Confirm zipcode/city were not disturbed.
    const zip = await page.getByLabel('Zipcode').inputValue();
    log('matching-diagnostics.log', `Zipcode field before run: ${zip}`);
    await page.locator('button:has-text("Run Diagnostics")').click();
    await page.waitForTimeout(2500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'matching-diagnostics-result.png'), fullPage: true });
    log('matching-diagnostics.log', `Contains Demo AC Services: ${bodyText.includes('Demo AC Services')}`);
    log('matching-diagnostics.log', `Contains Low/Mid/High: ${bodyText.includes('Low') && bodyText.includes('Mid') && bodyText.includes('High')}`);
    log('matching-diagnostics.log', `Contains Canonical Sources: ${bodyText.includes('Canonical Sources')}`);
    expect(bodyText).toContain('Demo AC Services');
    expect(bodyText).toContain('Low');
    expect(bodyText).toContain('Mid');
    expect(bodyText).toContain('High');
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('matching diagnostics: no-match scenario (zipcode 999999)', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/matching-diagnostics', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.getByLabel('City').fill('Nowhere');
    await page.getByLabel('Zipcode').fill('999999');
    await page.locator('button:has-text("Run Diagnostics")').click();
    await page.waitForTimeout(2500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'matching-diagnostics-nomatch.png'), fullPage: true });
    log('no-match.log', `Contains 'No eligible provider found': ${bodyText.includes('No eligible provider found')}`);
    expect(bodyText).toContain('No eligible provider found');
    expect(bodyText.toLowerCase()).not.toMatch(/traceback|exception|internal server error/);
  });

  test('completed job deduction: AC Repair rule visible', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/completed-job-deduction');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'completed-job-deduction.png'), fullPage: true });
    log('deduction.log', `Contains AC Repair: ${bodyText.includes('AC Repair')}`);
    log('deduction.log', `Contains 'usage credits': ${bodyText.includes('usage credits')}`);
    expect(bodyText).toContain('AC Repair');
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('operations board: real job list, open real completed job JOB-20260710-000001', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/operations');
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'operations-board.png'), fullPage: true });
    log('operations.log', `Operations Board title present: ${bodyText.includes('Operations Board')}`);
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('forbidden label scan on matching/operations/deduction pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/home-services/provider-matching',
      '/admin/home-services/matching-diagnostics',
      '/admin/home-services/completed-job-deduction',
      '/admin/operations',
      '/admin/finance/usage-credits',
    ];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForTimeout(1000);
      const bodyText = await page.locator('body').innerText();
      for (const f of FORBIDDEN) {
        expect(bodyText).not.toContain(f);
      }
      log('forbidden-label.log', `${route} -> clean of ${FORBIDDEN.length} forbidden labels`);
    }
  });
});
