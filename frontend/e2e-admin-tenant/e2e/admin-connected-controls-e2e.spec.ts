import { expect, test } from '@playwright/test';
import { loginAsSuperAdmin } from './helpers/admin-auth';
import { apiGet, login, SUPER_ADMIN } from './helpers/api';

test.describe('Admin connected controls', () => {
  test('delivery provider panel uses the real channel-status engine', async ({ page }) => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const status = await apiGet('/v1/admin/notification-outbox/channel-status', token);
    expect(status.status).toBe(200);
    const channels = status.body.data.items as Array<Record<string, unknown>>;
    expect(channels).toHaveLength(5);
    expect(channels.find(row => row.channel === 'in_app')).toMatchObject({
      state: 'Available',
      configured: true,
      webhook_status: 'Not required',
    });

    await loginAsSuperAdmin(page);
    await page.goto('/admin/notifications');
    await page.getByRole('button', { name: 'Delivery Providers' }).click();
    await expect(page.getByRole('cell', { name: 'In-App', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Available', exact: true })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Not required', exact: true })).toBeVisible();
    await expect(page.locator('body')).not.toContainText('Not implemented');
  });

  test('legacy booking endpoint keeps its unwrapped list/detail contract', async ({ page }) => {
    const token = await login(SUPER_ADMIN.email, SUPER_ADMIN.password);
    const response = await apiGet('/v1/admin/bookings?page=1&page_size=1', token);
    expect(response.status).toBe(200);
    const bookings = response.body.data.bookings as Array<{ id: string; booking_number: string }>;
    expect(bookings).toEqual(expect.any(Array));
    const booking = bookings[0];
    if (!booking) return; // Live PostgreSQL currently has no legacy booking-engine rows.

    await loginAsSuperAdmin(page);
    await page.goto(`/admin/bookings/${booking.id}`);
    await expect(page.getByText(booking.booking_number, { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Booking not found')).toHaveCount(0);
    await expect(page.getByText('Booking Details', { exact: true })).toBeVisible();
  });
});
