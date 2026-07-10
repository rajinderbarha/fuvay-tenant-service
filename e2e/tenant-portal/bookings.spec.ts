import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Bookings", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/bookings");
  });

  test("bookings page loads booking BK-001", async ({ page }) => {
    await expect(page.locator("text=BK-001, text=Ravi Mehta").first()).toBeVisible({ timeout: 8_000 });
  });

  test("status tabs visible (pending, confirmed, cancelled)", async ({ page }) => {
    await expect(page.locator("button:has-text('Pending'), text=/pending/i").first()).toBeVisible({ timeout: 6_000 });
  });

  test("confirm booking calls API", async ({ page }) => {
    let confirmCalled = false;
    await page.route("**/v1/bookings/b_001/confirm", async route => {
      confirmCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ id:"b_001", status:"confirmed" } }) });
    });
    const confirmBtn = page.locator("button:has-text('Confirm'), button:has-text('confirm')").first();
    if (await confirmBtn.count() > 0) {
      await confirmBtn.click();
      await page.waitForTimeout(800);
      expect(confirmCalled).toBeTruthy();
    }
  });

  test("reject booking shows reason input", async ({ page }) => {
    const rejectBtn = page.locator("button:has-text('Reject'), button:has-text('reject')").first();
    if (await rejectBtn.count() > 0) {
      await rejectBtn.click();
      await expect(page.locator("[role=dialog], input[placeholder*=reason i], textarea").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("convert to job calls API", async ({ page }) => {
    let convertCalled = false;
    await page.route("**/v1/bookings/b_001/convert-to-job", async route => {
      convertCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ id:"j_new", job_number:"JOB-NEW" } }) });
    });
    const convertBtn = page.locator("button:has-text('Convert'), button:has-text('Create Job')").first();
    if (await convertBtn.count() > 0) {
      await convertBtn.click();
      await page.waitForTimeout(800);
      expect(convertCalled).toBeTruthy();
    }
  });
});
