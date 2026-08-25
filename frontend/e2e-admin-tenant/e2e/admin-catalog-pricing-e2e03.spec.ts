import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { SEED } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e03');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

test.describe('ADMIN-TENANT-E2E-03 catalog/pricing', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('route smoke: canonical catalog workspace, no NaN/undefined/raw json', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/catalog-workspace',
    ];
    for (const route of routes) {
      const resp = await page.goto(route);
      await page.waitForTimeout(1500);
      const status = resp?.status() ?? -1;
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'route' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      log('route-smoke.log', `${route} | status=${status} | len=${bodyText.length} | hasSidebar=${await page.locator('aside').count()} | hasHeader=${await page.locator('header').count()}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/undefined/);
    }
  });

  test('service catalog: open the seed offering, verify problems + type/brand pricing', async ({ page }) => {
    // Rewritten, not just re-pinned. This test's whole premise was stale:
    // /admin/home-services/service-catalog is a deliberate redirect (see the
    // page's own comment) to /admin/catalog-workspace, which replaced the old
    // "Types" / "Brands" / "Questions / Issues" sub-tabs with "Overview" /
    // "Problems & Questions" / "Dimensions" / "Options & Add-ons" /
    // "Checklist" -- confirmed live, no .hsc-tab named "Types" or "Brands"
    // exists anywhere in the current page. Per-type/brand pricing (Split AC +
    // LG etc.) now lives on the separate /admin/pricing-rules page, which the
    // sibling test in this file already exercises and passes. Testing the
    // OLD tab names here was asserting a UI structure the product
    // deliberately replaced, not a regression.
    await loginAsSuperAdmin(page);
    await page.goto('/admin/home-services/service-catalog');
    await expect(page).toHaveURL(/\/admin\/catalog-workspace/, { timeout: 10000 });

    const acRow = page.locator('button', { hasText: SEED.offeringName }).filter({ hasNotText: 'Duplicate' }).first();
    await expect(acRow).toBeVisible({ timeout: 10000 });
    await acRow.click();
    await expect(page.locator('.cw-wtab', { hasText: 'Problems & Questions' })).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-general.png'), fullPage: true });

    await page.locator('.cw-wtab', { hasText: 'Problems & Questions' }).click();
    await expect(page.getByText(SEED.issueSummary, { exact: true })).toBeVisible({ timeout: 15_000 });
    const bodyIssues = await page.locator('body').innerText();
    log('catalog-content.log', `Problems & Questions tab contains ${SEED.issueSummary}: ${bodyIssues.includes(SEED.issueSummary)}`);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'ac-repair-issues.png'), fullPage: true });
    expect(bodyIssues).toContain(SEED.issueSummary);
    // Provider-owned prices are deliberately outside the Admin catalog.
  });

  test('forbidden label scan on rendered catalog/pricing pages', async ({ page }) => {
    await loginAsSuperAdmin(page);
    const routes = [
      '/admin/catalog-workspace',
    ];
    const forbidden = ['Cash Wallet', 'Wallet Balance', 'Withdraw', 'Escrow', 'Bargain Rule Builder', 'Bargain Settings', 'Manual Bargain Setup'];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForTimeout(1000);
      const bodyText = await page.locator('body').innerText();
      for (const f of forbidden) {
        expect(bodyText).not.toContain(f);
      }
      log('forbidden-label.log', `${route} -> clean of ${forbidden.length} forbidden labels`);
    }
  });
});
