import { test, chromium } from "@playwright/test";
import path from "path";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";
const RUNS = 5;
const OUT_PATH = path.join(__dirname, "../../docs/final-l5-01e/evidence/expired-session-repro-batch.json");

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"]') as HTMLInputElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

/** Simulates an expired/invalid access token (corrupted JWT string, no
 * matching refresh token) already present in localStorage before the
 * technician ever visits the app -- confirms the app recovers to a clean
 * sign-in prompt rather than hanging or crashing. */
test("FINAL-L5-01E expired-session recovery batch", async () => {
  test.setTimeout(5 * 60 * 1000);
  const fs = require("fs");
  const results: Array<Record<string, unknown>> = [];

  for (let i = 1; i <= RUNS; i++) {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    let outcome = "UNKNOWN", finalUrl = "", errorText = "";
    const start = Date.now();
    try {
      // Seed an invalid/expired-looking token before first navigation.
      await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle", timeout: 20000 });
      await page.evaluate(() => {
        localStorage.setItem("serviceos_tenant_token", "expired.invalid.token");
        localStorage.setItem("serviceos_tenant_refresh", "");
        localStorage.setItem("serviceos_user_id", "stale-user-id");
        localStorage.setItem("serviceos_tenant_id", "stale-tenant-id");
      });

      // Now navigate straight to the protected dashboard with the stale token present.
      await page.goto(`${BASE}/staff/dashboard`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1500);
      const bodyAfterStale = await page.innerText("body");
      const recoveredToSignIn = bodyAfterStale.includes("Please sign in") || bodyAfterStale.includes("session")
        || bodyAfterStale.toLowerCase().includes("sign in");

      // Then recover: perform a real login and confirm it succeeds cleanly.
      await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle", timeout: 20000 });
      await waitHydrated(page);
      await page.fill('input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForFunction(() => window.location.pathname === "/staff/dashboard", { timeout: 10000 });
      await page.waitForTimeout(1200);
      finalUrl = page.url();
      const bodyText = await page.innerText("body");
      const loggedInOk = finalUrl.includes("/staff/dashboard") && bodyText.includes("My Dashboard");

      outcome = (recoveredToSignIn && loggedInOk) ? "SUCCESS" : (loggedInOk ? "RECOVERED_BUT_STALE_STATE_UNCLEAR" : "FAILED_TO_RECOVER");
    } catch (e) {
      outcome = "EXCEPTION"; errorText = e instanceof Error ? e.message : String(e);
    }
    const elapsed = Date.now() - start;
    results.push({ run: i, outcome, elapsedMs: elapsed, finalUrl, errorText });
    console.log(`expired-session run ${i}: ${outcome} (${elapsed}ms)`);
    await context.close(); await browser.close();
    fs.writeFileSync(OUT_PATH, JSON.stringify(results, null, 2));
  }
  console.log(`EXPIRED_SESSION SUCCESS: ${results.filter(r => r.outcome === "SUCCESS").length}/${RUNS}`);
});
