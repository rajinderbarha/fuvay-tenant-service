import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Compliance", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/compliance");
  });

  test("compliance page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("deletion request summary KPIs visible", async ({ page }) => {
    await expect(page.locator("text=/deletion|pending|overdue/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("deletion request card shows user ID", async ({ page }) => {
    await expect(page.locator("text=u_del_01, text=dr_001").first()).toBeVisible({ timeout: 8_000 });
  });

  test("process deletion button opens confirmation", async ({ page }) => {
    const processBtn = page.locator("button:has-text('Process'), button:has-text('Delete')").first();
    if (await processBtn.count() > 0) {
      await processBtn.click();
      await expect(page.locator("[role=dialog], text=/confirm|process/i").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("retention policies section renders", async ({ page }) => {
    await expect(page.locator("text=/retention|policy/i").first()).toBeVisible({ timeout: 8_000 });
  });
});
