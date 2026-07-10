import { test, expect } from "@playwright/test";
import { setupMockApi, setAdminAuth } from "../helpers/mock-api";

test.describe("Super Admin — Finance Hub Overview (Enterprise Upgrade)", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/finance");
  });

  test("overview renders enterprise summary cards", async ({ page }) => {
    await expect(page.locator("text=/Finance Hub/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Active Wallets/i").first()).toBeVisible();
    await expect(page.locator("text=/Commission Earned/i").first()).toBeVisible();
    await expect(page.locator("text=/At-Risk Tenants/i").first()).toBeVisible();
    await expect(page.locator("text=/Pending Warranty Claims/i").first()).toBeVisible();
  });

  test("insight panels render with data", async ({ page }) => {
    await expect(page.locator("text=/Wallet Health Distribution/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Top Low-Balance Tenants/i").first()).toBeVisible();
    await expect(page.locator("text=/Deposit Status Breakdown/i").first()).toBeVisible();
    await expect(page.locator("text=/Top Commission Contributors/i").first()).toBeVisible();
    await expect(page.locator("text=/Recent Finance Activity/i").first()).toBeVisible();
    await expect(page.locator("text=/Rahul AC Services/i").first()).toBeVisible();
  });

  test("finance action queue renders pending counts and navigates", async ({ page }) => {
    await expect(page.locator("text=/Finance Action Queue/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Warranty Claim Pending Review/i").first()).toBeVisible();
    await page.locator("text=/Payout Pending Approval/i").first().click();
    await expect(page).toHaveURL(/\/admin\/finance\/payouts/, { timeout: 8_000 });
  });
});
