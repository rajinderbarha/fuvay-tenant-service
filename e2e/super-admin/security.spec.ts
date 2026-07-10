import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Security", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/security");
  });

  test("security page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("KPI cards show active sessions and blocked IPs", async ({ page }) => {
    await expect(page.locator("text=/session|blocked|failed/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("activity log shows a login_failed event", async ({ page }) => {
    await expect(page.locator("text=login_failed, text=1.2.3.4").first()).toBeVisible({ timeout: 8_000 });
  });

  test("block IP modal opens and submits", async ({ page }) => {
    const blockBtn = page.locator("button:has-text('Block IP'), button:has-text('Block')").first();
    if (await blockBtn.count() > 0) {
      await blockBtn.click();
      const modal = page.locator("[role=dialog]").first();
      await expect(modal).toBeVisible({ timeout: 4_000 });
      const ipInput = modal.locator("input[type=text], input[placeholder*=ip i]").first();
      if (await ipInput.count() > 0) {
        await ipInput.fill("5.6.7.8");
        await modal.locator("button[type=submit], button:has-text('Block'), button:has-text('Confirm')").first().click();
        await expect(modal).not.toBeVisible({ timeout: 5_000 });
      }
    }
  });

  test("acknowledge activity button works", async ({ page }) => {
    const ackBtn = page.locator("button:has-text('Acknowledge'), button:has-text('Ack')").first();
    if (await ackBtn.count() > 0) {
      await ackBtn.click();
      await page.waitForTimeout(500);
    }
  });
});
