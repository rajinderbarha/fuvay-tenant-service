import { expect, test, type Page, type Route } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const CAPTURE_DIR = path.resolve(process.cwd(), '..', '..', 'test-results', 'platform-settings-audit');

const settings = [
  {
    key: 'max_booking_radius_km', label: 'Maximum booking radius', value: 35, type: 'number',
    description: 'Maximum service radius used by booking eligibility.', is_public: false,
    category: 'booking_and_jobs', allowed_values: null, is_secret: false, risk_level: 'medium',
    requires_approval: false, requires_restart: false, is_runtime_editable: true,
    owner_module: 'booking', status: 'active', updated_at: '2026-08-18T06:30:00Z',
  },
  {
    key: 'tenant_payouts_enabled', label: 'Tenant payouts', value: false, type: 'boolean',
    description: 'Controls whether automated tenant payouts may run.', is_public: false,
    category: 'packages_and_usage_credits', allowed_values: [true, false], is_secret: false,
    risk_level: 'critical', requires_approval: true, requires_restart: false,
    is_runtime_editable: true, owner_module: 'finance', status: 'active', updated_at: '2026-08-17T10:00:00Z',
  },
  {
    key: 'payment_gateway_secret', label: 'Payment gateway secret', value: '********', type: 'secret',
    description: 'Credential used by the payment provider integration.', is_public: false,
    category: 'security', allowed_values: null, is_secret: true, risk_level: 'high',
    requires_approval: true, requires_restart: true, is_runtime_editable: true,
    owner_module: 'payments', status: 'active', updated_at: '2026-08-16T10:00:00Z',
  },
];

const categories = [{
  id: '11111111-1111-4111-8111-111111111111', name: 'Home Cleaning', slug: 'home-cleaning',
  vertical_type: 'home_services', finance_model: 'security_deposit_plus_credit_wallet',
  provider_business_model: 'marketplace', monetization_model: 'commission', is_active: true,
  is_customer_visible: true, pricing_supported: true, payment_collection_enabled: false,
  tenant_payouts_enabled: false,
}];

const plans = [{
  id: '22222222-2222-4222-8222-222222222222', name: 'Enterprise', package_type: 'enterprise',
  plan_level: 'enterprise', billing_cycle: 'monthly', currency: 'INR', included_credit_amount: 25000,
  storage_quota_gb: 100, commission_rate: 12.5, security_deposit_amount: 5000,
  validity_days: 30, is_active: true, vertical_type: 'home_services',
}];

const overrides = [{
  id: '33333333-3333-4333-8333-333333333333', tenant_id: '44444444-4444-4444-8444-444444444444',
  key: 'max_booking_radius_km', value: 50, reason: 'Metro pilot coverage',
  expires_at: '2026-09-01T00:00:00Z', requires_approval: false, status: 'active',
  created_at: '2026-08-18T06:30:00Z',
}];

const flags = [{
  id: '55555555-5555-4555-8555-555555555555', flag_key: 'smart_matching_v2',
  label: 'Smart matching V2', description: 'Progressive release of the new provider matching engine.',
  status: 'enabled', rollout_type: 'percentage', rollout_percent: 20, category_scope: null,
  tenant_scope: null, start_date: null, end_date: null, owner_module: 'matching',
  created_at: '2026-08-15T06:30:00Z', updated_at: '2026-08-18T06:30:00Z',
}];

function envelope(data: unknown) {
  return { success: true, data, request_id: 'e2e-settings-audit', engine_id: 'settings' };
}

async function json(route: Route, data: unknown) {
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(envelope(data)) });
}

async function resetMainScroll(page: Page) {
  await page.locator('.admin-main').evaluate(element => element.scrollTo({ top: 0, behavior: 'instant' }));
}

async function prepareCapture(page: Page) {
  await resetMainScroll(page);
  await page.evaluate(() => document.querySelectorAll('nextjs-portal').forEach(element => element.remove()));
}

async function mockPlatformApis(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('serviceos_admin_token', 'e2e-token');
    localStorage.setItem('serviceos-admin-theme', 'dark');
  });

  await page.route('**/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const method = request.method();

    if (pathname === '/v1/auth/me') return json(route, {
      id: '99999999-9999-4999-8999-999999999999', email: 'admin@serviceos.test',
      full_name: 'Platform Administrator', role: 'super_admin', permissions: ['*'],
      is_active: true, created_at: '2026-01-01T00:00:00Z',
    });
    if (pathname === '/v1/admin/catalog/navigation/effective-menu') return json(route, { verticals: [] });
    if (pathname === '/v1/admin/notifications/unread-count') return json(route, { unread_count: 0 });
    if (pathname === '/v1/admin/settings/summary') return json(route, {
      total_settings: 3, active_settings: 3, invalid_settings: 0, secret_settings: 1,
      pending_approval: 1, tenant_overrides: 1, plan_overrides: 1,
      changed_this_week: 4, rollback_available: 2,
    });
    if (pathname === '/v1/admin/settings/groups') return json(route, { categories: [
      { category: 'booking_and_jobs', setting_count: 1 },
      { category: 'packages_and_usage_credits', setting_count: 1 },
      { category: 'security', setting_count: 1 },
    ] });
    if (pathname === '/v1/admin/settings' && method === 'GET') return json(route, { settings, has_next: false, next_cursor: null });
    if (pathname === '/v1/admin/settings/resolve-effective-value') return json(route, {
      key: 'max_booking_radius_km', default_value: 25, global_value: 35,
      plan_override: null, tenant_override: null, effective_value: 35,
      resolution_path: 'default → global', warnings: [],
    });
    if (pathname.endsWith('/impact-preview')) return json(route, {
      key: pathname.split('/').at(-2), blocked: false, blocker_message: null, risk_level: 'medium',
      requires_approval: false, requires_restart: false, rollback_available: true, warnings: [],
    });
    if (pathname === '/v1/admin/settings/categories') return json(route, { categories });
    if (pathname.startsWith('/v1/admin/settings/categories/') && method === 'PUT') return json(route, categories[0]);
    if (pathname === '/v1/admin/settings/plans') return json(route, { packages: plans });
    if (pathname.startsWith('/v1/admin/settings/plans/') && method === 'PUT') return json(route, plans[0]);
    if (pathname === '/v1/admin/settings/tenant-overrides' && method === 'GET') return json(route, { overrides });
    if (pathname === '/v1/admin/settings/tenant-overrides' && method === 'POST') return json(route, { tenant_id: overrides[0].tenant_id, key: 'tenant_payouts_enabled', value: false });
    if (pathname.startsWith('/v1/admin/settings/tenant-overrides/') && method === 'PUT') return json(route, overrides[0]);
    if (pathname.endsWith('/revoke')) return json(route, { tenant_id: overrides[0].tenant_id, key: overrides[0].key, deleted: true });
    if (pathname === '/v1/admin/settings/feature-flags' && method === 'GET') return json(route, { flags });
    if (pathname === '/v1/admin/settings/feature-flags' && method === 'POST') return json(route, flags[0]);
    if (pathname.startsWith('/v1/admin/settings/feature-flags/') && method === 'PUT') return json(route, flags[0]);
    if (pathname.startsWith('/v1/admin/settings/feature-flags/') && method === 'POST') return json(route, flags[0]);
    if (pathname === '/v1/admin/settings/audit-logs') return json(route, { logs: [{
      log_id: '66666666-6666-4666-8666-666666666666', tier: 'global', key: 'max_booking_radius_km',
      old_value: 25, new_value: 35, reason: 'Expand metro coverage', actor: 'Platform Administrator',
      request_id: 'req-settings-001', risk_level: 'medium', action_type: 'setting_updated',
      tenant_id: null, created_at: '2026-08-18T06:30:00Z',
    }], has_next: false, next_cursor: null });
    if (pathname.endsWith('/history')) return json(route, { key: pathname.split('/').at(-2), history: [{
      log_id: '77777777-7777-4777-8777-777777777777', tier: 'global', old_value: 25,
      new_value: 35, changed_by: '99999999-9999-4999-8999-999999999999',
      reason: 'Expand metro coverage', request_id: 'req-settings-001', action_type: 'setting_updated',
      rollback_available: true, created_at: '2026-08-18T06:30:00Z',
    }] });
    if (pathname.endsWith('/rollback')) return json(route, { key: pathname.split('/').at(-2), rolled_back_to: 25, reason: 'E2E rollback verification' });
    if (pathname.startsWith('/v1/admin/settings/') && method === 'PUT') return json(route, { key: pathname.split('/').at(-1), value: 40, tier: 'global' });
    if (pathname.startsWith('/v1/admin/settings/') && method === 'POST') return json(route, { key: pathname.split('/').at(-2), status: 'active' });
    return json(route, {});
  });
}

test.describe('Platform Settings enterprise workspace', () => {
  test('all seven tabs render and their primary workflows respond', async ({ page }) => {
    test.setTimeout(120_000);
    const consoleErrors: string[] = [];
    const failedResponses: string[] = [];
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('response', response => { if (response.url().includes('/v1/') && response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`); });

    await mkdir(CAPTURE_DIR, { recursive: true });
    await mockPlatformApis(page);
    await page.setViewportSize({ width: 1478, height: 900 });
    await page.goto('/admin/settings', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: 'Platform Settings', exact: true })).toBeVisible();
    const skipTour = page.getByText('Skip tour', { exact: true });
    if (await skipTour.isVisible().catch(() => false)) await skipTour.click();
    await expect(page.getByRole('heading', { name: 'Runtime defaults' })).toBeVisible();
    await expect(page.getByRole('table').getByText('Maximum booking radius', { exact: true })).toBeVisible();
    await expect(page.getByRole('table').getByText('35', { exact: true })).toBeVisible();
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '01-global-settings.png'), fullPage: true });

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export CSV' }).click();
    expect((await download).suggestedFilename()).toBe('serviceos-platform-settings.csv');

    await page.getByRole('table').getByText('Maximum booking radius', { exact: true }).click();
    await page.getByPlaceholder('Tenant ID (optional)').fill('44444444-4444-4444-8444-444444444444');
    await page.getByRole('button', { name: 'Resolve scope' }).click();
    await expect(page.getByText('default → global')).toBeVisible();
    await page.getByRole('button', { name: 'Review change' }).click();
    await page.getByLabel('New value').fill('40');
    await page.getByRole('button', { name: 'Review impact' }).click();
    await expect(page.getByText('Impact review passed')).toBeVisible();
    await page.getByRole('button', { name: 'Apply change' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);

    await page.getByRole('button', { name: /Category Policies/ }).click();
    await expect(page.getByRole('heading', { name: 'Service operating models' })).toBeVisible();
    await expect(page.getByText('Home Cleaning', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Edit policy' }).click();
    await page.getByLabel('Change reason').fill('Policy review completed');
    await page.getByRole('button', { name: 'Save policy' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '02-category-policies.png'), fullPage: true });

    await page.getByRole('button', { name: /Plans & Packages/ }).click();
    await expect(page.getByRole('heading', { name: 'Plans and packages' })).toBeVisible();
    await expect(page.getByText('Enterprise', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Edit package' }).click();
    await page.getByLabel('Change reason').fill('Annual package review');
    await page.getByRole('button', { name: 'Save package' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '03-plans-packages.png'), fullPage: true });

    await page.getByRole('button', { name: /Tenant Overrides/ }).click();
    await expect(page.getByRole('heading', { name: 'Tenant overrides' })).toBeVisible();
    await expect(page.getByText('Metro pilot coverage')).toBeVisible();
    await page.getByRole('button', { name: 'Edit' }).click();
    await page.getByLabel('Business reason').fill('Pilot extended after review');
    await page.getByRole('button', { name: 'Save override' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '04-tenant-overrides.png'), fullPage: true });

    await page.getByRole('button', { name: /Feature Flags/ }).click();
    await expect(page.getByRole('heading', { name: 'Feature flags' })).toBeVisible();
    await expect(page.getByText('Smart matching V2')).toBeVisible();
    await page.getByRole('button', { name: 'Configure' }).click();
    await expect(page.getByRole('dialog')).toContainText('Percentage');
    await page.getByRole('button', { name: 'Save configuration' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '05-feature-flags.png'), fullPage: true });

    await page.getByRole('button', { name: /Audit Log/ }).click();
    await expect(page.getByRole('heading', { name: 'Configuration audit log' })).toBeVisible();
    await expect(page.getByText('Expand metro coverage')).toBeVisible();
    await page.getByLabel('Filter by setting key').fill('radius');
    await expect(page.getByText('max_booking_radius_km')).toBeVisible();
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '06-audit-log.png'), fullPage: true });

    await page.getByRole('button', { name: /Version History/ }).click();
    await expect(page.getByRole('heading', { name: 'Version history and rollback' })).toBeVisible();
    await expect(page.getByText('Expand metro coverage')).toBeVisible();
    await page.getByRole('button', { name: 'Restore this value' }).click();
    await expect(page.getByRole('dialog')).toContainText('A new audited version');
    await page.getByLabel('Rollback reason').fill('E2E rollback verification');
    await page.getByRole('button', { name: 'Restore value' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await prepareCapture(page);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '07-version-history.png'), fullPage: true });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('button', { name: /Global Settings/ }).click();
    await expect(page.getByRole('heading', { name: 'Runtime defaults' })).toBeVisible();
    await prepareCapture(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
    await page.screenshot({ path: path.join(CAPTURE_DIR, '08-mobile-global.png'), fullPage: true });

    expect(failedResponses).toEqual([]);
    expect(consoleErrors).toEqual([]);
  });
});
