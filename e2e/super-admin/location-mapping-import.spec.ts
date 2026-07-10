import { test, expect } from "@playwright/test";
import { setupMockApi, setAdminAuth } from "../helpers/mock-api";

test.describe("Super Admin — Location Mapping CSV Import Wizard", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setAdminAuth(page);
    await page.goto("/admin/location-mapping");
  });

  test("location mapping page loads with summary cards and conflict badge", async ({ page }) => {
    await expect(page.locator("text=/City \\/ Zipcode/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Total Mappings/i").first()).toBeVisible();
    await expect(page.locator("text=/Duplicate Conflicts/i").first()).toBeVisible();
    await expect(page.locator("text=/Duplicate Zipcode/i").first()).toBeVisible();
  });

  test("import wizard: upload preview shows conflict, confirm produces report", async ({ page }) => {
    await page.locator("button:has-text('Import CSV')").click();
    await expect(page.locator("[role=dialog], text=/Import CSV/i").first()).toBeVisible({ timeout: 4_000 });

    const csv = "country,state,district,city,zipcode,tier_code\n"
      + "India,Punjab,Fatehgarh Sahib,Bassi Pathana,140412,tier_3\n"
      + "India,Maharashtra,Mumbai,Mumbai,400002,tier_1\n";
    await page.setInputFiles('input[type="file"]', {
      name: "import.csv", mimeType: "text/csv", buffer: Buffer.from(csv),
    });

    await expect(page.locator("text=/Conflicts: 1/i").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=/Duplicate Zipcode/i").first()).toBeVisible();

    await page.locator("button:has-text('Confirm Import')").click();
    await expect(page.locator("text=/Created: 1/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("resolve test tool shows resolution path", async ({ page }) => {
    await page.locator('input[placeholder*="Zipcode"]').first().fill("140412");
    await page.locator("button:has-text('Resolve')").click();
    await expect(page.locator("text=/Resolution Path/i").first()).toBeVisible({ timeout: 8_000 });
  });
});
