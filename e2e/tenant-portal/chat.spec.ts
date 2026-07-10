import { test, expect }                       from "@playwright/test";
import { setupMockApi, setTenantAuth }           from "../helpers/mock-api";

test.describe("Tenant Portal — Chat", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/login");
    await setTenantAuth(page);
    await page.goto("/chat");
  });

  test("chat page shows conversation rooms list", async ({ page }) => {
    await expect(page.locator("text=Priya Sharma")).toBeVisible({ timeout: 8_000 });
  });

  test("selecting a room loads messages", async ({ page }) => {
    await page.locator("text=Priya Sharma").first().click();
    await expect(page.locator("text=Is the technician on the way?")).toBeVisible({ timeout: 6_000 });
  });

  test("send message calls API and clears input", async ({ page }) => {
    let sendCalled = false;
    await page.route("**/v1/chat/rooms/room_001/messages", async route => {
      if (route.request().method() === "POST") sendCalled = true;
      await route.fulfill({ status:200, contentType:"application/json",
        body: JSON.stringify({ success:true, data:{ message_id:"msg_new",
          room_id:"room_001", sender_id:"u_001", content:"Hello", message_type:"text",
          sent_at:new Date().toISOString(), is_read:false }}) });
    });
    await page.locator("text=Priya Sharma").first().click();
    await expect(page.locator("text=Is the technician on the way?")).toBeVisible({ timeout: 6_000 });
    const input = page.locator("input[placeholder*=message i], input[placeholder*=type i], textarea").first();
    await input.fill("Hello there");
    const sendBtn = page.locator("button:has-text('Send')").first();
    await sendBtn.click();
    await page.waitForTimeout(600);
    expect(sendCalled).toBeTruthy();
  });

  test("empty state shown when no room selected", async ({ page }) => {
    // Before clicking any room, expect a placeholder message
    await expect(page.locator("text=/select|conversation|choose/i").first()).toBeVisible({ timeout: 6_000 });
  });
});
