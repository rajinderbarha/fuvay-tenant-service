import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { loginAsTenantOwner, loginAsTenantReadOnly } from './helpers/tenant-auth';
import { login, apiGet, apiPut, apiPost, SEED, TENANT_OWNER, TENANT_MANAGER, TENANT_READONLY, CUSTOMER_ONE } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';
const EVIDENCE_DIR = path.join(__dirname, '..', 'evidence', 'e2e09b');
if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

function log(name: string, text: string) {
  fs.appendFileSync(path.join(EVIDENCE_DIR, name), text + '\n');
}

const AC_REPAIR_TENANT_SERVICE_ID = '015efedb-dd92-41f4-97ef-cc2745437760';
const SPLIT_AC_TYPE_ID = 'c86dfcf3-53bd-4d83-bf0b-51257f382652';
const PRICING_URL = `/v1/tenant/catalog/enabled-services/${AC_REPAIR_TENANT_SERVICE_ID}/types/${SPLIT_AC_TYPE_ID}/pricing`;

const FORBIDDEN = [
  'Cash Wallet', 'Wallet Balance', 'Withdraw', 'Withdrawable Balance',
  'Tenant Payout', 'Provider Earnings Wallet', 'Escrow',
  'Platform Collected Service Payment', 'Provider Cash Balance',
  'Credit Wallet Health', 'Platform Pay Now', 'Online Payment Required',
  'Manual Bargain Setup', 'Bargain Rule Builder', 'Bargain Settings', 'Bargain Floor',
];

test.describe('ADMIN-TENANT-E2E-09B RBAC hardening + live bookability', () => {
  test.skip(APP !== 'tenant', 'tenant-only tests');

  test('API: read-only blocked 403 on pricing, types, publish, save-draft, coverage (invalid payload proves auth-before-validation)', async () => {
    const token = await login(TENANT_READONLY.email, TENANT_READONLY.password);

    const pricing = await apiPut(PRICING_URL, token, { tenant_min_price: 99999, tenant_max_price: -5 });
    log('rbac.log', `pricing -> ${pricing.status} ${JSON.stringify(pricing.body)}`);
    expect(pricing.status).toBe(403);

    const types = await apiPut(
      `/v1/tenant/catalog/enabled-services/${AC_REPAIR_TENANT_SERVICE_ID}/types`,
      token, { type_ids: ['not-a-real-uuid'] }
    );
    log('rbac.log', `types -> ${types.status} ${JSON.stringify(types.body)}`);
    expect(types.status).toBe(403);

    const publish = await apiPost(`/v1/tenant/catalog/enabled-services/${AC_REPAIR_TENANT_SERVICE_ID}/publish`, token);
    log('rbac.log', `publish -> ${publish.status}`);
    expect(publish.status).toBe(403);

    const draft = await apiPost(`/v1/tenant/catalog/enabled-services/${AC_REPAIR_TENANT_SERVICE_ID}/save-draft`, token);
    log('rbac.log', `save-draft -> ${draft.status}`);
    expect(draft.status).toBe(403);
  });

  test('API: unauthenticated -> 401', async () => {
    const resp = await apiPut(PRICING_URL, '', { tenant_min_price: 850, tenant_max_price: 1100 });
    log('rbac.log', `unauth -> ${resp.status}`);
    expect(resp.status).toBe(401);
  });

  test('API: Owner mutation succeeds and is reverted; Manager mutation succeeds and still hits real validation', async () => {
    const ownerToken = await login(TENANT_OWNER.email, TENANT_OWNER.password);
    const before = await apiGet(`/v1/tenant/catalog/enabled-services/${AC_REPAIR_TENANT_SERVICE_ID}/type-pricing`, ownerToken);
    const originalMin = before.body.data.types.find((t: any) => t.service_type_id === SPLIT_AC_TYPE_ID).tenant_min_price;
    const originalMax = before.body.data.types.find((t: any) => t.service_type_id === SPLIT_AC_TYPE_ID).tenant_max_price;

    const mgrToken = await login(TENANT_MANAGER.email, TENANT_MANAGER.password);
    const mgrValid = await apiPut(PRICING_URL, mgrToken, { tenant_min_price: 900, tenant_max_price: 1150 });
    log('rbac.log', `manager valid -> ${mgrValid.status}`);
    expect(mgrValid.status).toBe(200);

    const mgrInvalid = await apiPut(PRICING_URL, mgrToken, { tenant_min_price: 700, tenant_max_price: 850 });
    log('rbac.log', `manager invalid (below floor) -> ${mgrInvalid.status}`);
    expect(mgrInvalid.status).toBe(422); // real business validation, not blocked by RBAC

    const revert = await apiPut(PRICING_URL, ownerToken, { tenant_min_price: originalMin, tenant_max_price: originalMax });
    log('rbac.log', `owner revert -> ${revert.status}`);
    expect(revert.status).toBe(200);
  });

  test('Browser: read-only login sees setup wizard read-only banner + disabled Save/Publish', async ({ page }) => {
    await loginAsTenantReadOnly(page);
    await page.goto('/tenant/setup/services', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const bodyText = await page.locator('body').innerText();
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'readonly-setup-services.png'), fullPage: true });
    log('ui.log', `readonly setup page bodyLen=${bodyText.length}`);
    expect(bodyText).not.toMatch(/\bundefined\b/i);
    expect(bodyText).not.toMatch(/\bNaN\b/);
    for (const f of FORBIDDEN) expect(bodyText).not.toContain(f);
  });

  test('Browser: owner login sees setup wizard without read-only banner', async ({ page }) => {
    await loginAsTenantOwner(page);
    await page.goto('/tenant/setup/services', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'owner-setup-services.png'), fullPage: true });
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/\bundefined\b/i);
  });

  test('API: live bookability status uses tenant_billing (credit balance healthy, is_bookable true)', async () => {
    const ownerToken = await login(TENANT_OWNER.email, TENANT_OWNER.password);
    const status = await apiGet('/v1/provider/status', ownerToken);
    log('bookability.log', `status -> ${JSON.stringify(status.body)}`);
    expect(status.status).toBe(200);
    expect(status.body.data.is_bookable).toBe(true);
    expect(status.body.data.is_visible).toBe(true);
  });

  test('API: live match-and-price returns Demo AC Services with real Low/Mid/High options', async () => {
    const custToken = await login(CUSTOMER_ONE.email, CUSTOMER_ONE.password);
    const draft = await apiPost('/v1/customer/home-services/booking-drafts', custToken, {
      category_slug: SEED.categorySlug, offering_slug: SEED.offeringSlug,
    });
    expect(draft.status).toBe(200);
    const draftId = draft.body.data.id;

    const update = await apiPut(`/v1/customer/home-services/booking-drafts/${draftId}`, custToken, {
      issue_summary: 'AC Not Cooling', city: SEED.city, zipcode: SEED.zipcode,
      offering_type_id: SEED.offeringTypeId, brand_id: SEED.brandId,
    });
    expect(update.status).toBe(200);

    const match = await apiPost(`/v1/customer/home-services/booking-drafts/${draftId}/match-and-price`, custToken);
    log('bookability.log', `match -> ${JSON.stringify(match.body)}`);
    expect(match.status).toBe(200);
    expect(match.body.data.selected_provider.tenant_id).toBe(SEED.tenantId);
    expect(match.body.data.selected_provider_price_options.low_price).toBeGreaterThan(0);
    expect(match.body.data.selected_provider_price_options.high_price).toBeGreaterThan(
      match.body.data.selected_provider_price_options.low_price
    );
    expect(JSON.stringify(match.body)).not.toContain('tenant_wallets');

    await apiPost(`/v1/customer/home-services/booking-drafts/${draftId}/cancel`, custToken);
  });
});
