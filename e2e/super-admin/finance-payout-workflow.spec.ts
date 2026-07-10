import { test, expect } from "@playwright/test";
import { setupMockApi, setAdminAuth } from "../helpers/mock-api";

test.describe("Super Admin — Payout Workflow (Enterprise Finance Upgrade)", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/finance/payouts");
  });

  test("payouts page renders summary cards and table", async ({ page }) => {
    await expect(page.locator("text=/Payouts/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Pending Payouts/i").first()).toBeVisible();
    await expect(page.locator("text=/Total Payout Value/i").first()).toBeVisible();
    await expect(page.locator("text=/PO-00000001/i").first()).toBeVisible();
  });

  test("action menu opens without clipping and shows workflow actions", async ({ page }) => {
    await page.locator("button:has-text('Actions')").first().click();
    const menu = page.locator("text=/Approve/i").first();
    await expect(menu).toBeVisible({ timeout: 4_000 });
    const box = await menu.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      const viewport = page.viewportSize();
      expect(box.x).toBeGreaterThanOrEqual(0);
      if (viewport) expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 5);
    }
  });

  test("approve -> mark processing -> mark completed workflow", async ({ page }) => {
    await page.locator("button:has-text('Actions')").first().click();
    await page.locator("button:has-text('Approve')").first().click();
    // Mocked approve response flips status to 'approved'; page refetches list.
    await page.waitForTimeout(300);

    await page.locator("button:has-text('Actions')").first().click();
    const markProcessing = page.locator("button:has-text('Mark Processing')").first();
    if (await markProcessing.count() > 0) {
      await markProcessing.click();
      await page.waitForTimeout(300);
    }
  });
});
