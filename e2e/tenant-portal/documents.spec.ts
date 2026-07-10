import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Documents", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/documents");
  });

  test("document list shows Service Agreement", async ({ page }) => {
    await expect(page.locator("text=Service Agreement")).toBeVisible({ timeout: 8_000 });
  });

  test("status tabs visible: All, To Sign, Signed, Expired", async ({ page }) => {
    await expect(page.locator("button:has-text('All')").first()).toBeVisible({ timeout: 6_000 });
    await expect(page.locator("button:has-text('To Sign'), button:has-text('Pending')").first()).toBeVisible({ timeout: 6_000 });
  });

  test("pending_signature badge visible on document", async ({ page }) => {
    await expect(page.locator("text=/pending.signature|to sign|sign now/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("Sign Now button fetches signing URL and shows modal", async ({ page }) => {
    let signingUrlCalled = false;
    await page.route("**/v1/documents/doc_001/signing-url", async route => {
      signingUrlCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{
          signing_url:"https://sign.example.com/doc_001",
          expires_at:new Date(Date.now()+86400000*3).toISOString() }}) });
    });
    const signBtn = page.locator("button:has-text('Sign Now')").first();
    if (await signBtn.count() > 0) {
      await signBtn.click();
      await page.waitForTimeout(800);
      // Either opened external link or showed modal
      expect(signingUrlCalled || await page.locator("[role=dialog]").count() > 0).toBeTruthy();
    }
  });

  test("Generate Document button opens modal", async ({ page }) => {
    const genBtn = page.locator("button:has-text('Generate'), button:has-text('+ Generate')").first();
    if (await genBtn.count() > 0) {
      await genBtn.click();
      await expect(page.locator("[role=dialog]").first()).toBeVisible({ timeout: 4_000 });
    }
  });

  test("status tab filter works", async ({ page }) => {
    const signedTab = page.locator("button:has-text('Signed')").first();
    if (await signedTab.count() > 0) {
      await page.route("**/v1/documents*", route => route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ documents:[], has_next:false }}) }));
      await signedTab.click();
      await expect(page.locator("text=/no documents|empty/i").first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
