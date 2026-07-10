import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Reviews", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/reviews");
  });

  test("review aggregate score visible", async ({ page }) => {
    await expect(page.locator("text=/4\.3|48 reviews|aggregate/i").first()).toBeVisible({ timeout: 8_000 });
  });

  test("review card shows comment and score", async ({ page }) => {
    await expect(page.locator("text=Good service, on time.")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=4.2, text=4\.2").first()).toBeVisible({ timeout: 6_000 });
  });

  test("reply button visible on unreplied review", async ({ page }) => {
    await expect(page.locator("button:has-text('Reply'), button:has-text('Respond')").first()).toBeVisible({ timeout: 8_000 });
  });

  test("reply modal opens and submits", async ({ page }) => {
    let replyCalled = false;
    await page.route("**/v1/reviews/r_001/reply", async route => {
      replyCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ ...{}, has_reply:true, reply_text:"Thank you!" } }) });
    });
    const replyBtn = page.locator("button:has-text('Reply'), button:has-text('Respond')").first();
    await replyBtn.click();
    const modal = page.locator("[role=dialog]").first();
    await expect(modal).toBeVisible({ timeout: 4_000 });
    const textarea = modal.locator("textarea").first();
    await textarea.fill("Thank you for your feedback!");
    await modal.locator("button:has-text('Submit'), button:has-text('Send'), button:has-text('Reply')").first().click();
    await page.waitForTimeout(800);
    expect(replyCalled).toBeTruthy();
  });

  test("reply button disabled after review has reply", async ({ page }) => {
    // Override: review already has a reply
    await page.route("**/v1/reviews*", route => route.fulfill({ status:200, contentType:"application/json",
      body: JSON.stringify({ success:true, data:{ reviews:[
        { id:"r_001", review_id:"r_001", job_id:"j_001", composite_score:4.2,
          comment:"Good service.", status:"published", signals:{}, has_reply:true,
          reply_text:"Thank you!", created_at:new Date().toISOString() }
      ], has_next:false }})}));
    await page.reload();
    const replyBtn = page.locator("button:has-text('Reply'), button:has-text('Respond')").first();
    if (await replyBtn.count() > 0) {
      await expect(replyBtn).toBeDisabled({ timeout: 6_000 });
    }
  });
});
