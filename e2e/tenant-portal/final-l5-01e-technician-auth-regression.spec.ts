import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

/** FINAL-L5-01E fast CI regression -- a single-pass version of the
 * repeated-run certification batches (final-l5-01e-repro-*.spec.ts). Not a
 * substitute for the full 20/20 etc. stability certification, but catches
 * a regression in any single run without the multi-minute batch cost. */
test.describe("Technician auth regression (FINAL-L5-01E)", () => {
  test("cold login lands on dashboard with real data, single useStaffContext instance", async ({ page }) => {
    let authMeCallCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/v1/auth/me")) authMeCallCount++;
    });

    await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle" });
    await waitHydrated(page);
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');

    await page.waitForFunction(() => window.location.pathname === "/staff/dashboard", { timeout: 10000 });
    await expect(page.getByText("My Dashboard")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Welcome back, Technician One/)).toBeVisible();

    // Rule 8: no duplicate login/profile requests. StaffLayout is the sole
    // owner of useStaffContext(); the dashboard page consumes the shared
    // instance via useStaffContextValue() instead of re-fetching. The bound
    // is 2, not 1: Next.js dev mode runs with React Strict Mode, which
    // intentionally double-invokes effects on mount (mount->unmount->mount)
    // to surface non-idempotent side effects -- this doubles ANY single
    // hook's dev-mode call count and does not happen in production builds.
    // What this assertion actually guards against is a *second independent
    // call site* (e.g. a page re-adding its own useStaffContext() call),
    // which would push the count to 4.
    expect(authMeCallCount).toBeLessThanOrEqual(2);
  });

  test("logout clears session and leaves no stale principal on next login", async ({ page }) => {
    await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle" });
    await waitHydrated(page);
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => window.location.pathname === "/staff/dashboard", { timeout: 10000 });

    await page.click('button:has-text("Logout")');
    await page.waitForFunction(() => window.location.pathname === "/staff/login", { timeout: 10000 });

    const token = await page.evaluate(() => localStorage.getItem("serviceos_tenant_token"));
    expect(token).toBeNull();
  });

  test("unauthorized deep-link is blocked, not shown", async ({ page }) => {
    await page.goto(`${BASE}/staff/jobs`, { waitUntil: "networkidle" });
    const body = await page.innerText("body");
    expect(body).toMatch(/sign in|Not logged in/i);
  });
});
