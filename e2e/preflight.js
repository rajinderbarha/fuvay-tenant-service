#!/usr/bin/env node
/**
 * FINAL-L5-05AG — Browser execution environment preflight.
 *
 * Every prior FINAL-L5-05 sprint since FINAL-L5-05S concluded "no browser
 * tool available" based solely on `ToolSearch` finding no dedicated
 * browser-agent tool -- none of them actually tried installing/launching
 * Chromium via the shell. This sprint found Playwright + a downloaded
 * Chromium binary already present in this repo/environment
 * (e2e/node_modules, chromium-1169 in the default Playwright browser
 * cache), and confirmed real Chromium can reach the real frontend, real
 * backend and real PostgreSQL here.
 *
 * This script is the reproducible check that should be run FIRST in any
 * future sprint before concluding Chromium is unavailable -- codifying
 * that determination instead of re-discovering it (or wrongly assuming
 * the opposite) each time.
 *
 * Run: node e2e/preflight.js
 * Exit code 0 = BROWSER_PREFLIGHT_PASSED. Non-zero = see printed reason.
 */
const { chromium } = require("playwright");

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const FRONTEND_URL = process.env.SUPER_ADMIN_URL ?? "http://localhost:3000";

const RESULTS = {
  BROWSER_PREFLIGHT_PASSED: "BROWSER_PREFLIGHT_PASSED",
  BROWSER_BINARY_MISSING: "BROWSER_BINARY_MISSING",
  BROWSER_LAUNCH_FAILED: "BROWSER_LAUNCH_FAILED",
  FRONTEND_UNREACHABLE: "FRONTEND_UNREACHABLE",
  BACKEND_UNREACHABLE: "BACKEND_UNREACHABLE",
  DATABASE_UNREACHABLE: "DATABASE_UNREACHABLE",
  AUTH_UNREACHABLE: "AUTH_UNREACHABLE",
  CONFIGURATION_INVALID: "CONFIGURATION_INVALID",
};

async function main() {
  const report = {
    backend_url: BACKEND_URL,
    frontend_url: FRONTEND_URL,
    checks: {},
    result: null,
  };

  // 1. Browser binary + launch.
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    report.checks.browser_launch = "ok";
  } catch (e) {
    report.checks.browser_launch = `failed: ${e.message}`;
    report.result = /Executable doesn't exist/i.test(e.message)
      ? RESULTS.BROWSER_BINARY_MISSING
      : RESULTS.BROWSER_LAUNCH_FAILED;
    console.log(JSON.stringify(report, null, 2));
    process.exit(1);
  }
  report.checks.browser_version = browser.version();

  const page = await browser.newPage();

  // 2. Backend health (also proves PostgreSQL, since /health reports it).
  try {
    const resp = await page.goto(`${BACKEND_URL}/health`, { timeout: 10000 });
    const body = JSON.parse(await page.textContent("body"));
    report.checks.backend_health = body.status;
    const pg = (body.services || []).find((s) => s.service === "postgresql");
    report.checks.database_status = pg ? pg.status : "unknown";
    if (body.status !== "ok") {
      report.result = pg && pg.status !== "ok" ? RESULTS.DATABASE_UNREACHABLE : RESULTS.BACKEND_UNREACHABLE;
      console.log(JSON.stringify(report, null, 2));
      await browser.close();
      process.exit(1);
    }
  } catch (e) {
    report.checks.backend_health = `unreachable: ${e.message}`;
    report.result = RESULTS.BACKEND_UNREACHABLE;
    console.log(JSON.stringify(report, null, 2));
    await browser.close();
    process.exit(1);
  }

  // 3. Frontend reachability + real page render.
  try {
    const resp = await page.goto(`${FRONTEND_URL}/login`, { waitUntil: "domcontentloaded", timeout: 30000 });
    report.checks.frontend_status = resp.status();
    report.checks.frontend_title = await page.title();
    const emailFieldCount = await page.locator('input[type="email"], input[name="email"]').count();
    report.checks.login_form_present = emailFieldCount > 0;
    if (resp.status() >= 400 || emailFieldCount === 0) {
      report.result = RESULTS.FRONTEND_UNREACHABLE;
      console.log(JSON.stringify(report, null, 2));
      await browser.close();
      process.exit(1);
    }
  } catch (e) {
    report.checks.frontend_status = `unreachable: ${e.message}`;
    report.result = RESULTS.FRONTEND_UNREACHABLE;
    console.log(JSON.stringify(report, null, 2));
    await browser.close();
    process.exit(1);
  }

  // 4. Authentication endpoint reachability (not a real login -- just
  //    confirms the route exists and returns a structured, non-5xx
  //    response for a deliberately invalid credential pair).
  try {
    const authResp = await page.request.post(`${BACKEND_URL}/v1/auth/login`, {
      data: { email: "preflight-check@invalid.example", password: "not-a-real-password" },
      timeout: 10000,
    });
    report.checks.auth_endpoint_status = authResp.status();
    if (authResp.status() >= 500) {
      report.result = RESULTS.AUTH_UNREACHABLE;
      console.log(JSON.stringify(report, null, 2));
      await browser.close();
      process.exit(1);
    }
  } catch (e) {
    report.checks.auth_endpoint_status = `unreachable: ${e.message}`;
    report.result = RESULTS.AUTH_UNREACHABLE;
    console.log(JSON.stringify(report, null, 2));
    await browser.close();
    process.exit(1);
  }

  // 5. Screenshot capability + clean close.
  try {
    await page.screenshot({ path: "e2e/test-results/preflight-screenshot.png" });
    report.checks.screenshot_capture = "ok";
  } catch (e) {
    report.checks.screenshot_capture = `failed: ${e.message}`;
  }

  await browser.close();
  report.checks.browser_closed = "ok";
  report.result = RESULTS.BROWSER_PREFLIGHT_PASSED;
  console.log(JSON.stringify(report, null, 2));
  process.exit(0);
}

main().catch((e) => {
  console.log(JSON.stringify({ result: RESULTS.CONFIGURATION_INVALID, error: e.message }, null, 2));
  process.exit(1);
});
