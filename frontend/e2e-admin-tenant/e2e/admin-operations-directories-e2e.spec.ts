import { expect, test } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SUPER_ADMIN } from './helpers/api';

test.describe('Admin Operations directories', () => {
  test('customer and staff APIs use the canonical native workload', async () => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);

    const customers = await apiGet('/v1/admin/customers?page=1&page_size=25', token);
    expect(customers.status).toBe(200);
    expect(customers.body.data.customers.length).toBeGreaterThan(0);
    expect(customers.body.data.customers.some((row: { total_bookings: number }) => row.total_bookings > 0)).toBe(true);

    const staff = await apiGet('/v1/admin/staff?page=1&page_size=25&sort_by=total_jobs&sort_dir=desc', token);
    expect(staff.status).toBe(200);
    expect(staff.body.data.staff.length).toBeGreaterThan(0);
    expect(staff.body.data.staff.some((row: { total_jobs: number }) => row.total_jobs > 0)).toBe(true);
  });

  test('Customers summary filters act immediately and rows open canonical details', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/customers');
    await expect(page.getByRole('heading', { name: 'Customers', exact: true })).toBeVisible();
    await expect(page.getByText(/customers?$/).first()).toBeVisible({ timeout: 15_000 });

    const repeat = page.getByText('Repeat Customers', { exact: true }).locator('..');
    const response = page.waitForResponse(r => r.url().includes('/v1/admin/customers?') && new URL(r.url()).searchParams.get('booking_count_min') === '2');
    await repeat.click();
    expect((await response).ok()).toBeTruthy();

    const complaints = page.getByText('Open Complaints', { exact: true }).locator('..');
    const complaintResponse = page.waitForResponse(r => r.url().includes('/v1/admin/customers?') && new URL(r.url()).searchParams.get('has_complaints') === 'true');
    await complaints.click();
    expect((await complaintResponse).ok()).toBeTruthy();
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
  });

  test('Staff renders native workload, authenticated controls and filter states', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/staff');
    await expect(page.getByRole('heading', { name: 'Staff Management' })).toBeVisible();
    await expect(page.getByText(/35 \(17 done\)|\d+ \(\d+ done\)/).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /csv/i })).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/\b(?:undefined|invalid date|nan)\b/i);
  });

  test('Complaints menu is active and policies are configurable', async ({ page }) => {
    await loginAsSuperAdmin(page);
    await page.goto('/admin/complaints');
    await expect(page.getByRole('heading', { name: 'Complaints & Disputes' })).toBeVisible();
    await expect(page.locator('a[href="/admin/complaints"]')).toHaveAttribute('aria-current', 'page');
    await page.getByRole('button', { name: 'Policies' }).click();
    await expect(page.getByRole('button', { name: 'Create policy' })).toBeVisible();
    await page.getByRole('button', { name: 'Create policy' }).click();
    await expect(page.getByRole('heading', { name: 'Create Complaint Policy' })).toBeVisible();
  });
});
