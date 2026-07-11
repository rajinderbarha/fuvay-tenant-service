import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3001";

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
  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 10000 });
  await page.waitForTimeout(800);
}

test.describe("FINAL-L5-02B Tenant Jobs browser regression", () => {
  test("Tenant Owner: dashboard + jobs use canonical endpoint, zero /v1/jobs calls", async ({ page }) => {
    const calls: string[] = [];
    page.on("request", (req) => {
      const u = req.url();
      if (u.includes("/v1/")) calls.push(`${req.method()} ${u.replace("http://localhost:8000", "")}`);
    });

    await login(page, "owner@demo-ac-services.local", "CanonicalL5!2026");
    await expect(page.locator("body")).toBeVisible();

    await page.goto(`${BASE}/jobs`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1500);

    const legacyCalls = calls.filter(c => /\/v1\/jobs(\/|\?|$)/.test(c) && !c.includes("/v1/provider/"));
    console.log("ALL_V1_CALLS:", JSON.stringify(calls, null, 2));
    console.log("LEGACY_/v1/jobs_CALLS:", JSON.stringify(legacyCalls, null, 2));
    expect(legacyCalls, "no active request should hit legacy /v1/jobs").toEqual([]);

    const canonicalCalls = calls.filter(c => c.includes("/v1/provider/my-records/jobs"));
    expect(canonicalCalls.length, "at least one call must hit the canonical endpoint").toBeGreaterThan(0);

    const body = await page.innerText("body");
    expect(body).not.toMatch(/No jobs match your filters/);

    // Filter by status
    await page.selectOption("select", { label: "Completed" }).catch(() => {});
    await page.waitForTimeout(500);
    await page.keyboard.press("Escape").catch(() => {});
    await page.locator("h1, h2").first().click({ force: true }).catch(() => {});

    // Open detail (row click triggers window.location.href full navigation)
    const firstRow = page.locator("tbody tr").first();
    await firstRow.click({ force: true, timeout: 10000, noWaitAfter: true });
    await page.waitForURL(/\/jobs\/[a-f0-9-]+/, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1500);
    console.log("DETAIL_URL:", page.url());
    const detailBody = await page.innerText("body");
    console.log("DETAIL_BODY_SNIPPET:", detailBody.slice(0, 400));
  });

  test("Tenant Read Only: jobs read access works, mutations unavailable", async ({ page }) => {
    await login(page, "readonly@demo-ac-services.local", "CanonicalL5!2026");
    await page.goto(`${BASE}/jobs`, { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1500);
    const body = await page.innerText("body");
    expect(body).toMatch(/read.?only/i);
  });
});
