import { test, expect } from '@playwright/test';
import { SUPER_ADMIN } from './helpers/api';

const APP = process.env.E2E_APP || 'admin';

test.describe('admin control-center login', () => {
  test.skip(APP !== 'admin', 'admin-only');

  test('is bounded, admin-specific and responsive on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/login');

    await expect(page.getByRole('heading', { name: 'Administrator sign in' })).toBeVisible();
    await expect(page.getByText('Admin Control Center', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Authorized personnel only')).toBeVisible();
    await expect(page.getByText(/Platform operational|Platform status unavailable/)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/create account/i)).toHaveCount(0);

    const shell = page.locator('.admin-login-shell');
    const box = await shell.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeLessThanOrEqual(1121);
    expect(box!.x).toBeGreaterThan(100);
  });

  test('validates required fields and supports password visibility', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Continue securely' }).click();
    await expect(page.getByText('Enter your administrator email and password.')).toBeVisible();

    const password = page.locator('#admin-password');
    await password.fill('Secret123!');
    await expect(password).toHaveAttribute('type', 'password');
    await page.getByRole('button', { name: 'Show password' }).click();
    await expect(password).toHaveAttribute('type', 'text');
  });

  test('collapses cleanly on a native mobile viewport without horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Administrator sign in' })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
    await expect(page.getByRole('button', { name: 'Continue securely' })).toBeVisible();
  });

  test('real administrator credentials enter the admin dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.locator('#admin-email').fill(SUPER_ADMIN.email);
    await page.locator('#admin-password').fill(SUPER_ADMIN.password);
    await page.getByRole('button', { name: 'Continue securely' }).click();
    await expect(page).toHaveURL(/\/admin\/dashboard/, { timeout: 15_000 });
  });

  test('MFA challenge submits the challenge token with the verification code', async ({ page }) => {
    await page.route('**/v1/auth/login', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { mfa_required: true, mfa_challenge_token: 'challenge-123' } }),
    }));
    let submittedBody: Record<string, unknown> | null = null;
    await page.route('**/v1/auth/mfa/verify', async route => {
      submittedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'test-token', refresh_token: null,
            user: { id: 'admin-1', email: 'admin@serviceos.in', full_name: 'Admin', role: 'super_admin' },
          },
        }),
      });
    });

    await page.goto('/login');
    await page.locator('#admin-email').fill('admin@serviceos.in');
    await page.locator('#admin-password').fill('Password123!');
    await page.getByRole('button', { name: 'Continue securely' }).click();
    await expect(page.getByRole('heading', { name: 'Verify your identity' })).toBeVisible();
    await page.locator('#admin-mfa-code').fill('123456');
    await page.getByRole('button', { name: 'Verify and continue' }).click();
    await expect.poll(() => submittedBody).not.toBeNull();
    expect(submittedBody).toEqual({ mfa_challenge_token: 'challenge-123', code: '123456' });
  });

  test('authenticated tenant accounts are denied and their admin token is cleared', async ({ page }) => {
    await page.route('**/v1/auth/login', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          access_token: 'tenant-token', refresh_token: 'tenant-refresh',
          user: { id: 'tenant-1', email: 'owner@example.com', full_name: 'Owner', role: 'tenant_owner' },
        },
      }),
    }));
    await page.route('**/v1/auth/logout', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }));

    await page.goto('/login');
    await page.locator('#admin-email').fill('owner@example.com');
    await page.locator('#admin-password').fill('Password123!');
    await page.getByRole('button', { name: 'Continue securely' }).click();

    await expect(page.getByText('This account does not have access to the Fuvay Admin Control Center.')).toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem('serviceos_admin_token'))).toBeNull();
    expect(await page.evaluate(() => localStorage.getItem('serviceos_admin_refresh'))).toBeNull();
  });
});
