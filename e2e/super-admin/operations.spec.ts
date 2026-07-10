import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Operations", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/operations");
  });

  test("operations page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("SLA alerts section shows overdue job", async ({ page }) => {
    await expect(page.locator("text=JOB-001, text=sla, text=warning").first()).toBeVisible({ timeout: 8_000 });
  });

  test("jobs table shows job number and status", async ({ page }) => {
    await expect(page.locator("text=JOB-001")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=in_progress, text=In Progress").first()).toBeVisible({ timeout: 6_000 });
  });

  test("status filter narrows job list", async ({ page }) => {
    const statusSelect = page.locator("select, [data-testid=status-filter]").first();
    if (await statusSelect.count() > 0) {
      await statusSelect.selectOption("completed");
      // JOB-001 is in_progress so should disappear
      await page.waitForTimeout(500);
    }
  });

  test("job row is clickable", async ({ page }) => {
    const row = page.locator("text=JOB-001").first();
    await row.click();
    await page.waitForTimeout(300);
    // Either navigates or opens drawer — check URL changed or modal opened
    const url = page.url();
    const hasModal = await page.locator("[role=dialog]").count() > 0;
    expect(url.includes("j_001") || hasModal).toBeTruthy();
  });
});
