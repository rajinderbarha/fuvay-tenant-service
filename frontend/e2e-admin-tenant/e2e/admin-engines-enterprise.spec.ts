import { expect, test, type Page, type Route } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const CAPTURE_DIR = path.resolve(process.cwd(), '..', '..', 'test-results', 'engines-audit');

const engines = [
  ['booking', 'Booking Orchestrator', 'orchestration', 'enabled', true, true, 'healthy', 18, 4, 2],
  ['payments', 'Payments', 'finance', 'enabled', true, true, 'healthy', 12, 5, 1],
  ['matching', 'Provider Matching', 'intelligence', 'enabled', true, false, 'degraded', 16, 4, 3],
  ['notifications', 'Notifications', 'communication', 'enabled', false, false, 'healthy', 20, 5, 0],
  ['trust_quality', 'Trust & Quality', 'governance', 'enabled', false, false, 'healthy', 14, 3, 2],
  ['pricing', 'Pricing', 'commerce', 'enabled', true, true, 'healthy', 22, 5, 1],
  ['ai_settlement', 'AI Settlement', 'intelligence', 'disabled', false, false, 'unknown', 3, 1, 1],
  ['warranty', 'Warranty', 'finance', 'enabled', false, false, 'down', 8, 3, 0],
].map(([engine_key, display_name, engine_type, global_status, is_core, is_locked, health_status, category_usage_count, package_usage_count, active_overrides], index) => ({
  id: `engine-${index + 1}`, engine_key, display_name,
  description: `${display_name} runtime capability for ServiceOS operations.`, engine_type,
  lifecycle_status: index === 6 ? 'beta' : 'stable', global_status, is_core, is_locked,
  is_customer_visible: false, is_tenant_visible: true, version: index === 2 ? '2.4.1' : '1.8.0',
  owner_team: index < 2 ? 'Core Platform' : index < 5 ? 'Service Intelligence' : 'Commerce Platform',
  dependencies: index === 2 ? [{ id: 'dep-1', engine_key: 'matching', depends_on_engine_key: 'booking', dependency_type: 'required', status: 'active' }] : [],
  category_usage_count, package_usage_count, active_overrides,
  latest_health: { id: `health-${index}`, engine_key, health_status, check_type: 'runtime', result: {}, response_ms: 84 + index * 9, checked_at: '2026-08-18T08:30:00Z' },
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-08-18T08:30:00Z',
}));

const summary = { total_engines: 8, enabled_globally: 7, disabled: 1, core_locked: 3, beta_engines: 1, category_mapped: 7, package_entitled: 7, tenant_overrides_active: 10, degraded_or_down: 2 };

function envelope(data: unknown) { return { success: true, data, request_id: 'engines-e2e', engine_id: 'engines' }; }
async function json(route: Route, data: unknown) { await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(envelope(data)) }); }

async function mockEngineApis(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('serviceos_admin_token', 'engines-e2e-token');
    localStorage.setItem('serviceos-admin-theme', 'dark');
  });
  await page.route('**/v1/**', async route => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === '/v1/auth/me') return json(route, { id: 'admin-1', email: 'admin@serviceos.test', full_name: 'Platform Administrator', role: 'super_admin', permissions: ['*'], is_active: true });
    if (pathname === '/v1/admin/catalog/navigation/effective-menu') return json(route, { verticals: [] });
    if (pathname === '/v1/admin/notifications/unread-count') return json(route, { unread_count: 0 });
    if (pathname === '/v1/admin/engines/summary') return json(route, summary);
    if (pathname === '/v1/admin/engines' && method === 'GET') return json(route, { engines, meta: { total: engines.length, page: 1, limit: 50, total_pages: 1 } });
    if (pathname === '/v1/admin/catalog/categories/options') return json(route, [{ id: 'category-1', name: 'Home Cleaning', slug: 'home-cleaning', vertical_type: 'home_services', status: 'active' }]);
    if (pathname === '/v1/admin/engines/dependencies') return json(route, { dependencies: [
      { id: 'dep-1', engine_key: 'matching', depends_on_engine_key: 'booking', dependency_type: 'required', status: 'active' },
      { id: 'dep-2', engine_key: 'payments', depends_on_engine_key: 'pricing', dependency_type: 'required', status: 'active' },
      { id: 'dep-3', engine_key: 'ai_settlement', depends_on_engine_key: 'trust_quality', dependency_type: 'required', status: 'active' },
    ], total: 3 });
    if (pathname === '/v1/admin/engines/dependencies/graph') return json(route, { nodes: [], edges: [], blocked_enables: [{ engine_key: 'ai_settlement', blocked_by: 'trust_quality policy approval' }] });
    if (pathname === '/v1/admin/engines/package-entitlements') return json(route, { entitlements: [
      { id: 'pe-1', package_id: 'enterprise', engine_key: 'booking', is_included: true, status: 'active', limits: {}, feature_flags: {} },
      { id: 'pe-2', package_id: 'enterprise', engine_key: 'matching', is_included: true, status: 'active', limits: { monthly_runs: 100000 }, feature_flags: {} },
      { id: 'pe-3', package_id: 'growth', engine_key: 'booking', is_included: true, status: 'active', limits: {}, feature_flags: {} },
      { id: 'pe-4', package_id: 'growth', engine_key: 'ai_settlement', is_included: false, status: 'inactive', limits: {}, feature_flags: {} },
    ], meta: { total: 4 } });
    if (pathname === '/v1/admin/engines/tenant-overrides' && method === 'GET') return json(route, { overrides: [
      { id: 'override-1', tenant_id: '44444444-4444-4444-8444-444444444444', engine_key: 'matching', override_type: 'force_enable', effective_status: 'enabled', reason: 'Controlled metro pilot', expires_at: '2026-09-01T00:00:00Z', status: 'active', created_at: '2026-08-10T00:00:00Z' },
      { id: 'override-2', tenant_id: '55555555-5555-4555-8555-555555555555', engine_key: 'warranty', override_type: 'force_disable', effective_status: 'disabled', reason: 'Incident containment', expires_at: '2026-08-25T00:00:00Z', status: 'active', created_at: '2026-08-18T00:00:00Z' },
    ], meta: { total: 2, page: 1, limit: 50 } });
    if (pathname === '/v1/admin/engines/health') return json(route, { engines: engines.map((engine, index) => ({ ...engine, health_status: engine.latest_health.health_status, last_check: engine.latest_health.checked_at, last_error: index === 7 ? 'Provider timeout threshold exceeded' : index === 2 ? 'Queue latency above SLO' : null })), summary: { healthy: 5, degraded: 1, down: 1, unknown: 1, total: 8 } });
    if (pathname === '/v1/admin/engines/permissions') return json(route, { permissions: [
      { id: 'perm-1', engine_key: 'payments', permission_key: 'payments.refunds.approve', label: 'Approve refunds', description: 'Approve payment refunds above the configured threshold.', scope: 'admin', is_sensitive: true, requires_mfa: true, status: 'active' },
      { id: 'perm-2', engine_key: 'matching', permission_key: 'matching.rules.manage', label: 'Manage matching rules', description: 'Change production provider ranking policy.', scope: 'admin', is_sensitive: true, requires_mfa: false, status: 'active' },
      { id: 'perm-3', engine_key: 'booking', permission_key: 'booking.jobs.read', label: 'Read jobs', description: 'View booking and job runtime state.', scope: 'tenant', is_sensitive: false, requires_mfa: false, status: 'active' },
    ], meta: { total: 3 } });
    if (pathname === '/v1/admin/engines/audit-logs') return json(route, { logs: [
      { id: 'log-1', engine_key: 'matching', action_type: 'enable', scope_type: 'tenant', actor_user_id: 'admin-1', actor_role: 'super_admin', reason: 'Controlled metro pilot', created_at: '2026-08-18T08:30:00Z' },
      { id: 'log-2', engine_key: 'warranty', action_type: 'health_check', scope_type: 'global', actor_role: 'system', reason: 'Scheduled runtime probe', created_at: '2026-08-18T08:15:00Z' },
    ], meta: { total: 2, page: 1, limit: 50, total_pages: 1 } });
    if (pathname.endsWith('/impact-preview')) return json(route, { engine_key: 'ai_settlement', engine_name: 'AI Settlement', action: 'enable', current_status: 'disabled', is_locked: false, is_core: false, categories_affected: 3, packages_affected: 1, active_tenant_overrides: 1, blockers: [], warnings: ['Beta engine: stage rollout before full enablement.'], risk_level: 'medium', can_proceed: true, recommendation: 'Enable for a pilot tenant first.' });
    if (pathname === '/v1/admin/engines/health/check-all') return json(route, { results: [], total: 8 });
    if (pathname.includes('/revoke') || pathname.endsWith('/enable') || pathname.endsWith('/disable')) return json(route, {});
    return json(route, {});
  });
}

async function prepareCapture(page: Page) {
  await page.locator('.admin-main').evaluate(element => element.scrollTo({ top: 0, behavior: 'instant' }));
  await page.evaluate(() => document.querySelectorAll('nextjs-portal').forEach(element => element.remove()));
}

test.describe('Engine management audit', () => {
  test('capture current eight-workspace baseline', async ({ page }) => {
    test.setTimeout(120_000);
    await mkdir(CAPTURE_DIR, { recursive: true });
    await mockEngineApis(page);
    await page.setViewportSize({ width: 1478, height: 900 });
    await page.goto('/admin/engines', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: 'Engine Management' })).toBeVisible();
    const tabs = ['All Engines', 'Category Matrix', 'Dependencies', 'Package Entitlements', 'Tenant Overrides', 'Health', 'Permissions', 'Audit Logs'];
    for (let index = 0; index < tabs.length; index += 1) {
      if (index > 0) await page.getByRole('button', { name: tabs[index], exact: true }).click();
      await prepareCapture(page);
      await page.screenshot({ path: path.join(CAPTURE_DIR, `source-${String(index + 1).padStart(2, '0')}-${tabs[index].toLowerCase().replaceAll(' ', '-')}.png`), fullPage: true });
    }
  });
});
