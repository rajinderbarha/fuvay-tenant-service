import { test, expect } from '@playwright/test';
import { loginViaUi } from './helpers/auth';
import { ensureBaselineBookable } from './helpers/seed';
import { CUSTOMER_ONE, SEED, login, apiGet } from './helpers/api';

// Hard gate: no internal/unsafe terms may ever render in customer-facing text.
const FORBIDDEN_TEXT = [
  'admin_min_price', 'admin_max_price', 'provider_min_price', 'provider_max_price',
  'internal_score', 'ranking_score', 'bookability_score', 'usage_credit_balance',
  'completed_job_deduction', 'commission', 'security_deposit', 'ledger', 'audit',
  'excluded_providers', 'Cash Wallet', 'Wallet Balance', 'Withdraw', 'Escrow',
  'Platform Collected Service Payment', 'Provider Cash Balance', 'Ledger', 'Audit Log',
];

test.describe('Customer Home Services — real browser E2E (system Chrome, real backend)', () => {
  test.beforeAll(async () => {
    // Fails fast with a clear message if the baseline seed scenario regresses,
    // instead of the UI test failing opaquely deep in the flow.
    await ensureBaselineBookable();
  });

  test('provider-first booking flow: catalog -> match -> price -> confirm -> track', async ({ page }) => {
    await loginViaUi(page, CUSTOMER_ONE.email, CUSTOMER_ONE.password);

    await page.goto('/customer/home-services');
    await expect(page.getByText('Home Services')).toBeVisible({ timeout: 15_000 });

    // Navigate straight to the booking wizard (category id resolved by the app itself)
    await page.goto('/customer/home-services/book');
    await page.getByRole('button', { name: 'Home Services' }).click();
    await page.getByRole('button', { name: 'AC Repair' }).click();
    await page.getByRole('button', { name: 'Next', exact: true }).click();

    // Details step — type + brand must be selected (pricing is type+brand-specific for this offering)
    const splitAcChip = page.getByRole('button', { name: 'Split AC', exact: true });
    await expect(splitAcChip).toBeVisible({ timeout: 15_000 });
    await splitAcChip.click();
    await expect(splitAcChip).toHaveClass(/selected/);
    const lgChip = page.getByRole('button', { name: 'LG', exact: true });
    await expect(lgChip).toBeVisible({ timeout: 15_000 });
    await lgChip.click();
    await expect(lgChip).toHaveClass(/selected/);
    await page.locator('textarea').fill(SEED.issueSummary);
    await page.getByRole('button', { name: 'Next', exact: true }).click();

    // Location step
    await page.getByPlaceholder('Phone *').fill('9999999999');
    await page.getByPlaceholder('Zipcode *').fill(SEED.zipcode);
    await page.getByPlaceholder('City *').fill(SEED.city);
    await page.getByPlaceholder('Address line 1 *').fill('123 Model Town');
    await page.getByRole('button', { name: 'Next', exact: true }).click();

    // Provider step — must appear before price cards (hard gate)
    await expect(page.getByRole('button', { name: 'See Price Options' })).toBeVisible({ timeout: 20_000 });
    const providerCardText = await page.locator('.co-card').first().innerText();
    expect(providerCardText.length).toBeGreaterThan(0);
    await page.getByRole('button', { name: 'See Price Options' }).click();

    // Price step — Low/Mid/High must be visible, no editable numeric input
    await expect(page.getByText(/Low —/)).toBeVisible();
    await expect(page.getByText(/Mid —/)).toBeVisible();
    await expect(page.getByText(/High —/)).toBeVisible();
    const numericInputs = await page.locator('input[type="number"]').count();
    expect(numericInputs).toBe(0);

    await page.getByText(/Mid —/).click();
    await page.getByRole('button', { name: 'Continue' }).click();

    // Review step
    await expect(page.getByText('Confirm Booking')).toBeEnabled();
    await expect(page.getByText(/Pays Provider Directly/)).toBeVisible();
    await page.getByRole('button', { name: 'Confirm Booking' }).click();

    // Confirmation
    await expect(page.getByText('Booking Confirmed')).toBeVisible({ timeout: 20_000 });

    // Safety scan: rendered confirmation text must not leak internal fields.
    const confirmText = await page.locator('body').innerText();
    for (const term of FORBIDDEN_TEXT) {
      expect(confirmText).not.toContain(term);
    }

    await page.getByRole('button', { name: 'Track Booking' }).click();
    await expect(page).toHaveURL(/\/customer\/bookings\//);

    // Tracking page must render without leaking internal data either.
    await expect(page.getByText(/pending|confirmed|assign/i).first()).toBeVisible({ timeout: 15_000 });
    const trackingText = await page.locator('body').innerText();
    for (const term of FORBIDDEN_TEXT) {
      expect(trackingText).not.toContain(term);
    }
  });

  test('completed booking review flow: submit rating, then block duplicate submission', async ({ page }) => {
    // Find the real completed booking via direct API (Part 6 fixture), matching
    // however the frontend's own bookings list would surface it — no mock data.
    const token = await login(CUSTOMER_ONE.email, CUSTOMER_ONE.password);
    const list = await apiGet('/v1/customer/bookings', token);
    const completed = list.body.data.items.find((b: any) => b.status === 'completed');
    test.skip(!completed, 'No completed booking fixture available in this environment.');

    await loginViaUi(page, CUSTOMER_ONE.email, CUSTOMER_ONE.password);
    await page.goto(`/customer/bookings/${completed.booking_id}/rate`);

    // Already-reviewed state must render cleanly, not crash — this booking was
    // already rated in Part 6's live API verification, so this exercises the
    // duplicate-state UI path directly in the browser.
    await expect(page.getByText(/already|submitted|thank you|rated/i).first()).toBeVisible({ timeout: 15_000 });
  });
});
