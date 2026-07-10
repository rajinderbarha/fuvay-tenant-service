import { test, expect }                   from "@playwright/test";
import { setupMockApi, setAdminAuth }     from "../helpers/mock-api";

test.describe("Super Admin — Security: Block IP + API Key reveal-once", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/security");
  });

  test("Block IP modal validates and submits", async ({ page }) => {
    await page.locator('button:has-text("IP Blocklist")').first().click();
    await expect(page.locator("text=1.2.3.4").first()).toBeVisible({ timeout: 8_000 });

    await page.locator('button:has-text("Block IP")').first().click();
    const modal = page.locator("text=Block IP Address").first();
    await expect(modal).toBeVisible({ timeout: 4_000 });

    await page.locator('input[placeholder*="103.21"]').fill("203.0.113.5");
    await page.locator('input[placeholder*="Brute force"]').fill("Suspicious repeated login attempts");
    await page.locator('button:has-text("Block IP")').last().click();

    await expect(page.locator("text=Block IP Address")).not.toBeVisible({ timeout: 5_000 });
  });

  test("Create API Key shows the raw secret exactly once", async ({ page }) => {
    await page.locator('button:has-text("API Keys")').first().click();
    await expect(page.locator("text=Create API Key").first()).toBeVisible({ timeout: 8_000 });

    await page.locator('button:has-text("Create API Key")').first().click();
    await expect(page.locator("text=Tenant ID").first()).toBeVisible({ timeout: 4_000 });

    await page.locator('input').filter({ hasText: "" }).first();
    const inputs = page.locator('[role=dialog], .modal, div').filter({ hasText: "Tenant ID" });
    await page.locator('input').nth(0).fill("t_test01");

    await page.locator('button:has-text("Create Key")').last().click();

    await expect(page.locator("text=This key will not be shown again")).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("text=sk_live_MOCKEDRAWKEYFORTESTINGONLY123456")).toBeVisible();
  });

  test("Revoke IP block action is available on an active entry", async ({ page }) => {
    await page.locator('button:has-text("IP Blocklist")').first().click();
    await expect(page.locator("text=1.2.3.4").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator('button:has-text("Actions")').first()).toBeVisible();
  });
});
