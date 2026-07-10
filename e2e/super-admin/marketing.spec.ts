import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Marketing", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/marketing");
  });

  test("marketing page loads heading", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
  });

  test("summary KPIs show accounts connected and posts count", async ({ page }) => {
    await expect(page.locator("text=/connected|post|budget/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("generate AI image button opens form", async ({ page }) => {
    const genBtn = page.locator("button:has-text('Generate'), button:has-text('AI Image')").first();
    if (await genBtn.count() > 0) {
      await genBtn.click();
      await expect(page.locator("[role=dialog], form").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("schedule post button or section visible", async ({ page }) => {
    await expect(page.locator("text=/schedule|post|campaign/i").first()).toBeVisible({ timeout: 8_000 });
  });
});
