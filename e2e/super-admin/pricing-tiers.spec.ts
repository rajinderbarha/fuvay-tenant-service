import { test, expect } from "@playwright/test";
import { setupMockApi, setAdminAuth } from "../helpers/mock-api";

test.describe("Super Admin — Pricing Tiers (Enterprise Upgrade)", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/pricing-tiers");
  });

  test("pricing tiers page loads with summary cards", async ({ page }) => {
    await expect(page.locator("text=/Pricing Tiers/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Total Tiers/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Mapped Cities/i").first()).toBeVisible();
  });

  test("tier row shows mapped locations and pricing rules counts", async ({ page }) => {
    await expect(page.locator("text=/Cities: 1 \\/ Zipcodes: 1/").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Rules: 1 \\/ Active: 1/").first()).toBeVisible();
  });

  test("view details action navigates to tier detail page", async ({ page }) => {
    await page.locator("button:has-text('Actions')").first().click();
    await page.locator("button:has-text('View Details')").first().click();
    await expect(page).toHaveURL(/\/admin\/pricing\/tiers\/tier_001/, { timeout: 8_000 });
    await expect(page.locator("text=/Overview/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Mapped Cities/i").first()).toBeVisible();
    await expect(page.locator("text=/Audit Logs/i").first()).toBeVisible();
  });
});
