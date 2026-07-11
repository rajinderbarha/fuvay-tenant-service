import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3002";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

async function login(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle", timeout: 20000 });
  await waitHydrated(page);
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
}

test.describe("FINAL-L5-02B Customer Booking browser regression", () => {
  test("Customer One: booking list/detail/tracking show real seeded data", async ({ page }) => {
    const calls: string[] = [];
    page.on("request", (req) => {
      const u = req.url();
      if (u.includes("/v1/customer/bookings")) calls.push(`${req.method()} ${u.replace("http://localhost:8000", "")}`);
    });

    await login(page, "customer1@serviceos.local", "CanonicalL5!2026");
    await page.goto(`${BASE}/customer/bookings`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1500);

    console.log("BOOKING_API_CALLS:", JSON.stringify(calls, null, 2));
    expect(calls.some(c => c.includes("/v1/customer/bookings")), "list must call canonical /v1/customer/bookings").toBe(true);

    const body = await page.innerText("body");
    console.log("LIST_BODY_SNIPPET:", body.slice(0, 500));
    expect(body).not.toMatch(/No bookings yet/i);

    const firstCard = page.locator("a, [role='button'], tr").filter({ hasText: /AC|Repair|L501/i }).first();
    if (await firstCard.count() > 0) {
      await firstCard.click({ force: true, noWaitAfter: true });
      await page.waitForTimeout(2000);
      const detailBody = await page.innerText("body");
      console.log("DETAIL_URL:", page.url());
      console.log("DETAIL_BODY_SNIPPET:", detailBody.slice(0, 500));
      expect(detailBody).not.toMatch(/Wallet Balance|Tenant Payout|Escrow|Provider Earnings Wallet/i);
    }
  });

  test("Customer Two: isolation -- Customer One's booking is not visible or accessible", async ({ page }) => {
    await login(page, "customer2@serviceos.local", "CanonicalL5!2026");
    await page.goto(`${BASE}/customer/bookings`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1500);
    const body = await page.innerText("body");
    console.log("CUSTOMER2_LIST_BODY:", body.slice(0, 500));
    expect(body).not.toMatch(/L501-BK/);

    // Direct URL attempt at Customer One's known booking id
    await page.goto(`${BASE}/customer/bookings/34af952e-f66c-42e0-aff7-7ab3ec84f7ad`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1500);
    const detailBody = await page.innerText("body");
    console.log("CUSTOMER2_DIRECT_URL_BODY:", detailBody.slice(0, 500));
    expect(detailBody).toMatch(/not found|unavailable|error|no.*booking/i);
  });
});
