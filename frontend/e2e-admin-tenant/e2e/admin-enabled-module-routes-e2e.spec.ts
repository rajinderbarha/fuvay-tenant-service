import { test, expect } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SUPER_ADMIN } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';

test.describe('enabled vertical admin module routes', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('every enabled module resolves to a real admin workspace', async ({ page }) => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const menu = await apiGet('/v1/admin/catalog/navigation/effective-menu', token);
    expect(menu.status).toBe(200);

    const enabledPaths = new Set<string>();
    for (const vertical of menu.body.data.verticals) {
      if (!vertical.is_enabled) continue;
      for (const module of vertical.modules) {
        if (!module.is_enabled) continue;
        expect(module.admin_path).not.toContain('/catalog-module/');
        enabledPaths.add(module.admin_path);
      }
    }

    await loginAsSuperAdmin(page);
    for (const route of enabledPaths) {
      const response = await page.goto(route);
      expect(response?.status(), route).toBeLessThan(400);
      await expect(page.locator('main')).toBeVisible({ timeout: 15_000 });
      const body = await page.locator('body').innerText();
      expect(body, route).not.toMatch(/Dedicated admin UI .* coming soon/i);
      expect(body, route).not.toMatch(/404: This page could not be found/i);
    }
  });
});
