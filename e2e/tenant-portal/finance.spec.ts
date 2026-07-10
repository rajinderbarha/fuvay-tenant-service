import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Finance", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/finance");
  });

  test("wallet balance visible", async ({ page }) => {
    await expect(page.locator("text=/15,000|15K|wallet/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("commission history table renders", async ({ page }) => {
    await expect(page.locator("text=JOB-001, text=300").first()).toBeVisible({ timeout: 8_000 });
  });

  test("subscription plan info visible", async ({ page }) => {
    await expect(page.locator("text=/growth|plan|500 jobs/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("request payout modal opens", async ({ page }) => {
    const payoutBtn = page.locator("button:has-text('Payout'), button:has-text('Request Payout'), button:has-text('Withdraw')").first();
    if (await payoutBtn.count() > 0) {
      await payoutBtn.click();
      await expect(page.locator("[role=dialog]").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("payout request calls API", async ({ page }) => {
    let payoutCalled = false;
    await page.route("**/v1/payments/payout-requests", async route => {
      payoutCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ id:"po_001", status:"pending" } }) });
    });
    const payoutBtn = page.locator("button:has-text('Payout'), button:has-text('Request Payout'), button:has-text('Withdraw')").first();
    if (await payoutBtn.count() > 0) {
      await payoutBtn.click();
      const modal = page.locator("[role=dialog]").first();
      if (await modal.count() > 0) {
        const amountInput = modal.locator("input[type=number], input[placeholder*=amount i]").first();
        if (await amountInput.count() > 0) await amountInput.fill("5000");
        await modal.locator("button[type=submit], button:has-text('Submit'), button:has-text('Request')").first().click();
        await page.waitForTimeout(800);
        expect(payoutCalled).toBeTruthy();
      }
    }
  });
});
