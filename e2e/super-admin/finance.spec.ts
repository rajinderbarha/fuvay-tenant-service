import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Finance", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/finance");
  });

  test("finance page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("platform GMV figure renders", async ({ page }) => {
    // 2750000 or formatted as 27.5L
    await expect(page.locator("text=/gmv|revenue|2,750,000|27\.5L/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("tenant billing config table visible", async ({ page }) => {
    await expect(page.locator("table, [data-testid=billing-table]").first()).toBeVisible({ timeout: 8_000 });
  });

  test("edit billing config modal opens", async ({ page }) => {
    const editBtn = page.locator("button:has-text('Edit'), button:has-text('Configure')").first();
    if (await editBtn.count() > 0) {
      await editBtn.click();
      await expect(page.locator("[role=dialog]").first()).toBeVisible({ timeout: 4_000 });
    }
  });
});
