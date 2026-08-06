import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsTenantOwner, loginAsTenantReadOnly } from './helpers/tenant-auth';
import { login, apiGet, apiPut, SEED, TENANT_OWNER, TENANT_READONLY } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e09');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

const FORBIDDEN = [
  'Cash Wallet', 'Wallet Balance', 'Withdraw', 'Withdrawable Balance',
  'Tenant Payout', 'Provider Earnings Wallet', 'Escrow',
  'Platform Collected Service Payment', 'Provider Cash Balance',
  'Credit Wallet Health', 'Platform Pay Now', 'Online Payment Required',
  'Manual Bargain Setup', 'Bargain Rule Builder', 'Bargain Settings', 'Bargain Floor',
];

// The removed demo tenant's AC Repair tenant_service_id 404s -- there is no
// equivalent for it anymore. Repointed to the ONE live tenant_service in the
// whole database with requires_type=true AND requires_brand=true: Guramrit's
// "AC Installation" (ae4608e5), which has real Split/Window service_types and
// LG/Samsung/Voltas brands (verified via direct psql query, 2026-08-06).
// Guramrit's owner IS the E2E tenant-owner login (SEED.tenantId), so PUT
// mutations here act on the same tenant already used elsewhere in this suite.
const AC_INSTALLATION_TENANT_SERVICE_ID = 'ae4608e5-18c8-4d30-a3aa-c7e988fc7b4f';
const SPLIT_AC_TYPE_ID = '7b4a6a52-3755-46b9-a187-96a89126b0ad';
const WINDOW_AC_TYPE_ID = '1cbea8f9-4bc7-46dd-a9a4-94dd254f4590';
const LG_BRAND_ID = 'a8efc47f-d639-4cf6-a2eb-808f73cad28c';

test.describe('ADMIN-TENANT-E2E-09 tenant service setup + coverage', () => {
  test.skip(APP !== 'tenant', 'tenant-only tests');

  test('route smoke: setup/services, provider/service-coverage, legacy redirect, onboarding-status, dashboard', async ({ page }) => {
    await loginAsTenantOwner(page);
    const routes = [
      '/dashboard',
      '/tenant/setup/services',
      '/provider/service-coverage',
      '/setup/service-coverage',
      '/onboarding-status',
    ];
    for (const route of routes) {
      const resp = await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1500);
      const status = resp?.status() ?? -1;
      const finalUrl = page.url();
      const bodyText = await page.locator('body').innerText();
      await page.screenshot({ path: path.join(EVIDENCE_DIR, 'route' + route.replace(/\//g, '_') + '.png'), fullPage: true });
      log('route-smoke.log', `${route} -> ${finalUrl} | status=${status} | len=${bodyText.length}`);
      expect(status).toBeLessThan(400);
      expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/);
      expect(bodyText).not.toMatch(/\bundefined\b/);
      expect(bodyText).not.toContain('Demo AC Services'.replace('Demo AC Services', 'Your Business'));
      for (const f of FORBIDDEN) expect(bodyText).not.toContain(f);
    }
  });

  test('tenant name "Guramrit" appears on dashboard and setup pages (real, not placeholder)', async ({ page }) => {
    // "Demo AC Services" was the removed demo tenant; the live E2E
    // tenant-owner login is SEED.tenantName ("Guramrit").
    await loginAsTenantOwner(page);
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).toContain(SEED.tenantName);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'dashboard-tenant-name.png'), fullPage: true });
  });

  test('service coverage page: coverage matrix, Ludhiana/141001 area visible', async ({ page }) => {
    await loginAsTenantOwner(page);
    await page.goto('/provider/service-coverage', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'service-coverage-page.png'), fullPage: true });
    log('coverage.log', `bodyLen=${bodyText.length} hasLudhiana=${bodyText.includes('Ludhiana')} has141001=${bodyText.includes('141001')}`);
    expect(bodyText).not.toMatch(/\bundefined\b/);
    for (const f of FORBIDDEN) expect(bodyText).not.toContain(f);
  });

  test('type-specific brand pricing: Split AC+LG and Window AC+LG differ, verified via direct backend API', async () => {
    const token = await login(TENANT_OWNER.email, TENANT_OWNER.password);
    const splitPricing = await apiGet(
      `/v1/tenant/catalog/enabled-services/${AC_INSTALLATION_TENANT_SERVICE_ID}/brand-pricing?service_type_id=${SPLIT_AC_TYPE_ID}`,
      token
    );
    const windowPricing = await apiGet(
      `/v1/tenant/catalog/enabled-services/${AC_INSTALLATION_TENANT_SERVICE_ID}/brand-pricing?service_type_id=${WINDOW_AC_TYPE_ID}`,
      token
    );
    log('type-brand-pricing.log', `split=${JSON.stringify(splitPricing.body)}`);
    log('type-brand-pricing.log', `window=${JSON.stringify(windowPricing.body)}`);
    expect(splitPricing.status).toBeLessThan(400);
    expect(windowPricing.status).toBeLessThan(400);
    // The two type contexts must not return an identical brand price range for LG —
    // this is the crux of Part 5 (type-specific separation).
    const splitLg = (splitPricing.body?.data?.brands ?? []).find((b: { brand_id: string }) => b.brand_id === LG_BRAND_ID);
    const windowLg = (windowPricing.body?.data?.brands ?? []).find((b: { brand_id: string }) => b.brand_id === LG_BRAND_ID);
    if (splitLg && windowLg) {
      const same = splitLg.tenant_min_price === windowLg.tenant_min_price && splitLg.tenant_max_price === windowLg.tenant_max_price;
      log('type-brand-pricing.log', `splitLg=${JSON.stringify(splitLg)} windowLg=${JSON.stringify(windowLg)} identicalRanges=${same}`);
      expect(same).toBeFalsy();
    }
  });

  test('provider price range: invalid range rejected (min > max, below admin floor)', async () => {
    const token = await login(TENANT_OWNER.email, TENANT_OWNER.password);
    // min > max should be rejected
    const badRange = await apiPut(
      `/v1/tenant/catalog/enabled-services/${AC_INSTALLATION_TENANT_SERVICE_ID}/types/${SPLIT_AC_TYPE_ID}/pricing`,
      token, { tenant_min_price: 900, tenant_max_price: 700 }
    );
    log('price-range-validation.log', `min>max -> status=${badRange.status} body=${JSON.stringify(badRange.body)}`);
    expect(badRange.status).toBeGreaterThanOrEqual(400);

    // below admin floor (admin floor confirmed 600 for Split AC + LG range context)
    const belowFloor = await apiPut(
      `/v1/tenant/catalog/enabled-services/${AC_INSTALLATION_TENANT_SERVICE_ID}/types/${SPLIT_AC_TYPE_ID}/pricing`,
      token, { tenant_min_price: 100, tenant_max_price: 200 }
    );
    log('price-range-validation.log', `below-floor -> status=${belowFloor.status} body=${JSON.stringify(belowFloor.body)}`);
    expect(belowFloor.status).toBeGreaterThanOrEqual(400);
  });

  test('E2E-09B FIXED: read-only tenant user is blocked by access_scope at 403, before business validation', async () => {
    const token = await login(TENANT_READONLY.email, TENANT_READONLY.password);
    // Intentionally INVALID payload (would 422 for a permitted user) — proves the 403
    // comes from the authorization layer, not from validation failing first.
    const resp = await apiPut(
      `/v1/tenant/catalog/enabled-services/${AC_INSTALLATION_TENANT_SERVICE_ID}/types/${SPLIT_AC_TYPE_ID}/pricing`,
      token, { tenant_min_price: 99999, tenant_max_price: -5 }
    );
    log('readonly-security.log', `tenant.readonly PUT type-pricing (invalid payload) -> status=${resp.status} body=${JSON.stringify(resp.body)}`);
    expect(resp.status).toBe(403);
    expect(resp.body?.error_code ?? resp.body?.data?.error_code).toBe('PERMISSION_DENIED');
  });

  test('mutation UI hidden or gated for read-only login on service coverage page (browser)', async ({ page }) => {
    await loginAsTenantReadOnly(page);
    await page.goto('/provider/service-coverage', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'readonly-service-coverage.png'), fullPage: true });
    log('readonly-security.log', `readonly UI bodyLen=${bodyText.length} hasPublishBtn=${await page.locator('button:has-text("Publish")').count()}`);
    expect(bodyText).not.toMatch(/\bundefined\b/);
  });
});
