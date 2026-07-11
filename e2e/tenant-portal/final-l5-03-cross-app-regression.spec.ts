import { test, expect } from "@playwright/test";

async function waitHydrated(page: import("@playwright/test").Page, selector = 'input[type="email"]') {
  await page.waitForFunction((sel) => {
    const el = document.querySelector(sel) as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, selector, { timeout: 15000 });
}

function collectConsoleErrors(page: import("@playwright/test").Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));
  return errors;
}

const FORBIDDEN = /Wallet Balance|Tenant Payout|Escrow|Provider Earnings Wallet|Manual Bargain Setup|Bargain Rule Builder/i;

test.describe("FINAL-L5-03 cross-app real browser regression", () => {
  test("Super Admin: login, dashboard, modified pages load with real data", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "admin@serviceos.local");
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname.includes("/admin/dashboard"), { timeout: 10000 });
    await page.waitForTimeout(1000);
    let body = await page.innerText("body");
    expect(body).not.toMatch(FORBIDDEN);
    expect(body).not.toMatch(/undefined|NaN/);

    // Modified page 1: usage-credits (Suspense fix)
    await page.goto("http://localhost:3000/admin/finance/usage-credits", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    body = await page.innerText("body");
    expect(body).toMatch(/Usage Credits/);
    expect(body).not.toMatch(/\{"success"/); // no raw JSON dump

    // Modified page 2: audit-logs (apiFetchPaginatedRaw migration)
    await page.goto("http://localhost:3000/admin/audit-logs", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    body = await page.innerText("body");
    expect(body).toMatch(/Audit Logs/);

    const realErrors = errors.filter(e => !/favicon|DevTools|Fast Refresh/i.test(e));
    console.log("SUPER_ADMIN_CONSOLE_ERRORS:", JSON.stringify(realErrors));
  });

  test("Tenant Portal: login, dashboard, jobs, offerings load with real data", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("http://localhost:3001/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "owner@demo-ac-services.local");
    await page.fill('input[type="password"]', "CanonicalL5!2026");
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 10000 });
    await page.waitForTimeout(1200);
    let body = await page.innerText("body");
    expect(body).not.toMatch(FORBIDDEN);

    await page.goto("http://localhost:3001/jobs", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    body = await page.innerText("body");
    expect(body).not.toMatch(/No jobs match your filters/);

    // Modified page: provider/offerings (isTenantOwnerRole dedup)
    await page.goto("http://localhost:3001/provider/offerings", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    body = await page.innerText("body");
    expect(body.length).toBeGreaterThan(0);

    const realErrors = errors.filter(e => !/favicon|DevTools|Fast Refresh/i.test(e));
    console.log("TENANT_PORTAL_CONSOLE_ERRORS:", JSON.stringify(realErrors));
  });

  test("Customer App: login and bookings load with real data", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("http://localhost:3002/login", { waitUntil: "networkidle", timeout: 20000 });
    await waitHydrated(page);
    await page.fill('input[type="email"]', "customer1@serviceos.local");
    await page.fill('input[type="password"]', "CanonicalL5!2026");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    await page.goto("http://localhost:3002/customer/bookings", { waitUntil: "networkidle", timeout: 20000 });
    await page.waitForTimeout(1200);
    const body = await page.innerText("body");
    expect(body).not.toMatch(FORBIDDEN);
    expect(body).not.toMatch(/No bookings yet/i);

    const realErrors = errors.filter(e => !/favicon|DevTools|Fast Refresh/i.test(e));
    console.log("CUSTOMER_APP_CONSOLE_ERRORS:", JSON.stringify(realErrors));
  });
});
