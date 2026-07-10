import { Page, expect } from '@playwright/test';

export async function loginViaUi(page: Page, email: string, password: string) {
  // Suppress onboarding tour overlay before any admin/tenant shell page mounts.
  await page.addInitScript(() => {
    window.localStorage.setItem('serviceos_disable_tour_e2e', 'true');
    window.localStorage.setItem('serviceos-tenant-tour-done', 'true');
  });
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
}
