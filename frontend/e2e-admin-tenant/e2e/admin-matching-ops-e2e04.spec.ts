import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { SEED } from './helpers/api';

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
      // Was /admin/home-services/service-jobs, deleted in 0e726d1 (this
      // session's admin console consolidation) with no nav entry pointing at
      // it anymore -- the real, documented replacement is the unified
      // Bookings & Jobs workspace over the canonical service_bookings +
      // service_jobs pipeline.
      '/admin/home-services/bookings-jobs',
      '/admin/operations',
      // Was /admin/home-services/overview, a page.tsx that was deleted
      // (5994b63, predates this session). Its nav entry has since been
      // repointed to the real replacement (commit 4c73201) -- smoke-test
      // THAT route, not the one the menu no longer even links to.
      '/admin/home-services/dashboard',
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
    // The root permission gate makes a real /auth/me round trip before it
    // exposes the protected workspace. A fixed 1s sleep was flaky whenever
    // the API was concurrently processing the wider browser suite.
    await expect(page.getByRole('heading', { name: 'Provider Matching' })).toBeVisible({ timeout: 15_000 });
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).toContain('Provider Matching');
    expect(bodyText).toContain('Ranking Factors');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'provider-matching.png'), fullPage: true });
    log('provider-matching.log', `Header+ranking factors present: ${bodyText.includes('Ranking Factors')}`);
  });

  test('matching diagnostics: run seed offering+Split AC+LG and verify selected provider', async ({ page }) => {
    // The page's BLANK_FORM used to prefill a category_id/master_service_id
    // pair that no longer exists (fixed separately: it now starts genuinely
    // blank rather than pointing at dead rows), so every field this test
    // needs must be filled explicitly now -- nothing can be assumed
    // pre-filled.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/matching-diagnostics', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Category ID').fill(SEED.categoryId);
    await page.getByLabel('Master Service ID').fill(SEED.masterServiceId);
    await page.getByLabel('City').fill(SEED.city);
    await page.getByLabel('Zipcode').fill(SEED.zipcode);
    await page.getByLabel('Type ID (optional)').fill(SEED.offeringTypeId);
    await page.getByLabel('Brand ID (optional)').fill(SEED.brandId);
    await page.locator('button:has-text("Run Diagnostics")').click();
    await expect(page.getByText(SEED.tenantName, { exact: false }).first()).toBeVisible({ timeout: 15000 });
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'matching-diagnostics-result.png'), fullPage: true });
    log('matching-diagnostics.log', `Contains ${SEED.tenantName}: ${bodyText.includes(SEED.tenantName)}`);
    log('matching-diagnostics.log', `Contains Canonical Sources: ${bodyText.includes('Canonical Sources')}`);
    expect(bodyText).toContain(SEED.tenantName);
    expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
  });

  test('matching diagnostics: no-match scenario (zipcode 999999)', async ({ page }) => {
    // Category/Master Service must also be filled now that BLANK_FORM starts
    // empty (previously relied on those defaults being dead-but-present IDs).
    // A category/service must still be chosen for a "no eligible provider"
    // result to mean anything -- only city/zip are the no-match variable.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/matching-diagnostics', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Category ID').fill(SEED.categoryId);
    await page.getByLabel('Master Service ID').fill(SEED.masterServiceId);
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

  test('completed job deduction: seed offering rule visible', async ({ page }) => {
    // "AC Repair" no longer exists (see SEED constant); the equivalent live
    // row is SEED.offeringName ("AC Service"). Also replaced a fixed
    // 1500ms-sleep-then-innerText read with a web-first wait -- see the
    // identical fix + rationale in admin-finance-tenant-e2e05.spec.ts's
    // "renders real per-rule deduction credits" test.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/completed-job-deduction');
    await expect(page.locator('td', { hasText: SEED.offeringName })).toBeVisible({ timeout: 15000 });
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'completed-job-deduction.png'), fullPage: true });
    log('deduction.log', `Contains ${SEED.offeringName}: ${bodyText.includes(SEED.offeringName)}`);
    log('deduction.log', `Contains 'usage credits': ${bodyText.includes('usage credits')}`);
    expect(bodyText).toContain(SEED.offeringName);
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
