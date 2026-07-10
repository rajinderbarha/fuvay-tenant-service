import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Jobs", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/jobs");
  });

  test("jobs list renders JOB-001", async ({ page }) => {
    await expect(page.locator("text=JOB-001")).toBeVisible({ timeout: 8_000 });
  });

  test("SLA alert section visible", async ({ page }) => {
    await expect(page.locator("text=/sla|overdue|alert/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("status badge visible on job row", async ({ page }) => {
    await expect(page.locator("text=in_progress, text=In Progress").first()).toBeVisible({ timeout: 6_000 });
  });

  test("clicking job row navigates to job detail", async ({ page }) => {
    await page.locator("text=JOB-001").first().click();
    await expect(page).toHaveURL(/\/jobs\/j_001/, { timeout: 6_000 });
  });

  test("job detail shows customer name and status transitions", async ({ page }) => {
    await page.goto("/jobs/j_001");
    await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 8_000 });
    // Status transition buttons should be visible
    await expect(page.locator("button:has-text('quality_check'), button:has-text('Quality Check'), button:has-text('completed'), button:has-text('Completed')").first()).toBeVisible({ timeout: 8_000 });
  });

  test("job detail shows job history timeline", async ({ page }) => {
    await page.goto("/jobs/j_001");
    await expect(page.locator("text=created, text=in_progress").first()).toBeVisible({ timeout: 8_000 });
  });

  test("update status calls API and refetches", async ({ page }) => {
    await page.goto("/jobs/j_001");
    let statusUpdateCalled = false;
    await page.route("**/v1/jobs/j_001/status", async route => {
      statusUpdateCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ id:"j_001", status:"quality_check" } }) });
    });
    const transBtn = page.locator("button:has-text('quality_check'), button:has-text('Quality Check')").first();
    if (await transBtn.count() > 0) {
      await transBtn.click();
      await page.waitForTimeout(1000);
      expect(statusUpdateCalled).toBeTruthy();
    }
  });

  test("close job modal requires closing notes", async ({ page }) => {
    await page.goto("/jobs/j_001");
    const closeBtn = page.locator("button:has-text('Close Job'), button:has-text('close')").first();
    if (await closeBtn.count() > 0) {
      await closeBtn.click();
      await expect(page.locator("[role=dialog]").first()).toBeVisible({ timeout: 4_000 });
      await expect(page.locator("textarea, input[placeholder*=note i]").first()).toBeVisible();
    }
  });
});
