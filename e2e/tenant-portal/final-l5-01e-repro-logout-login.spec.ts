import { test, chromium } from "@playwright/test";
import path from "path";

const BASE = "http://localhost:3001";
const EMAIL = "tech1@demo-ac-services.local";
const PASSWORD = "CanonicalL5!2026";
const CYCLES = 10;
const OUT_PATH = path.join(__dirname, "../../docs/final-l5-01e/evidence/logout-login-repro-batch.json");

async function waitHydrated(page: import("@playwright/test").Page) {
  await page.waitForFunction(() => {
    const el = document.querySelector('input[type="email"], button') as HTMLElement | null;
    if (!el) return false;
    return Object.keys(el).some(k => k.startsWith("__reactProps") || k.startsWith("__reactFiber"));
  }, { timeout: 15000 });
}

/** Real logout (via the UI Logout button, which clears localStorage and
 * hard-navigates to /staff/login) followed immediately by a fresh login,
 * repeated CYCLES times in one browser -- exercises that logout leaves no
 * stale principal/query state behind for the next login (mission rule 7). */
test("FINAL-L5-01E logout->login cycle batch", async () => {
  test.setTimeout(10 * 60 * 1000);
  const fs = require("fs");
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  const results: Array<Record<string, unknown>> = [];

  for (let i = 1; i <= CYCLES; i++) {
    const start = Date.now();
    let outcome = "UNKNOWN";
    let finalUrl = "";
    let errorText = "";
    try {
      await page.goto(`${BASE}/staff/login`, { waitUntil: "networkidle", timeout: 20000 });
      await waitHydrated(page);
      await page.fill('input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForFunction(() => window.location.pathname === "/staff/dashboard", { timeout: 10000 });
      await page.waitForTimeout(1000);

      const bodyAfterLogin = await page.innerText("body");
      if (!bodyAfterLogin.includes("My Dashboard")) throw new Error("login did not land on dashboard content");

      await page.click('button:has-text("Logout")');
      await page.waitForFunction(() => window.location.pathname === "/staff/login", { timeout: 10000 });
      await page.waitForTimeout(500);

      const tokenAfterLogout = await page.evaluate(() => localStorage.getItem("serviceos_tenant_token"));
      if (tokenAfterLogout) throw new Error("token still present in localStorage after logout");

      finalUrl = page.url();
      outcome = finalUrl.includes("/staff/login") ? "SUCCESS" : "UNEXPECTED_URL_AFTER_LOGOUT";
    } catch (e) {
      outcome = "EXCEPTION";
      errorText = e instanceof Error ? e.message : String(e);
    }
    const elapsed = Date.now() - start;
    results.push({ cycle: i, outcome, elapsedMs: elapsed, finalUrl, errorText });
    console.log(`cycle ${i}: ${outcome} (${elapsed}ms)`);
    fs.writeFileSync(OUT_PATH, JSON.stringify(results, null, 2));
  }

  await context.close();
  await browser.close();
  const successCount = results.filter(r => r.outcome === "SUCCESS").length;
  console.log(`SUCCESS: ${successCount}/${CYCLES}`);
});
