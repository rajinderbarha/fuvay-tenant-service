import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
await mkdir(auditDir, { recursive: true });

const result = {
  started_at: new Date().toISOString(),
  pages: [],
  nav_clicks: [],
  failed_responses: [],
  console_errors: [],
};

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await context.addInitScript(() => localStorage.setItem("serviceos-tenant-tour-done", "true"));
const page = await context.newPage();

page.on("response", response => {
  if (response.status() >= 400 && response.url().includes("/v1/")) {
    result.failed_responses.push({ status: response.status(), url: response.url() });
  }
});
page.on("console", message => {
  if (message.type() === "error") result.console_errors.push(message.text());
});

async function settle() {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle", { timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(500);
}

async function dismissDashboardAlert() {
  const dismiss = page.getByRole("button", { name: "Dismiss", exact: true });
  if (await dismiss.isVisible().catch(() => false)) await dismiss.click();
}

async function capture(number, slug, url) {
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await settle();
  const mainHeading = await page.locator("h1").first().textContent().catch(() => null);
  const body = await page.locator("body").innerText();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  await page.screenshot({ path: path.join(auditDir, `${String(number).padStart(2, "0")}-${slug}.png`), fullPage: true });
  result.pages.push({
    slug,
    requested_url: url,
    final_url: page.url(),
    heading: mainHeading?.trim() ?? null,
    has_error_copy: /something went wrong|couldn.t load|failed to load|not found/i.test(body),
    horizontal_overflow: overflow,
    axe_serious_or_critical: axe.violations
      .filter(v => v.impact === "serious" || v.impact === "critical")
      .map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })),
  });
}

try {
  await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
  await page.getByPlaceholder("Enter your email or mobile number").fill("provider@serviceos.in");
  await page.getByPlaceholder("Enter your password").fill("Password123!");
  await page.getByRole("button", { name: /Sign in/ }).click();
  await page.waitForURL(url => url.pathname !== "/login", { timeout: 30000 });

  await capture(1, "business-profile", "http://localhost:3001/profile");
  const edit = page.getByRole("button", { name: /Edit profile/i }).first();
  if (await edit.count()) {
    await edit.click();
    await page.waitForTimeout(300);
    result.nav_clicks.push({ label: "Edit profile", destination: page.url(), selected_tab_text: await page.locator("button").filter({ hasText: "Legal & Verification" }).getAttribute("style") });
    await page.screenshot({ path: path.join(auditDir, "02-business-profile-edit.png"), fullPage: true });
  }

  await page.goto("http://localhost:3001/dashboard", { waitUntil: "domcontentloaded" });
  await settle();
  await dismissDashboardAlert();
  for (const [label, slug, number] of [["Coverage & Hours", "coverage-hours-nav", 3], ["Documents", "documents-nav", 4]]) {
    const link = page.getByRole("link", { name: label, exact: true });
    await link.click();
    await settle();
    result.nav_clicks.push({ label, destination: page.url() });
    await page.screenshot({ path: path.join(auditDir, `${String(number).padStart(2, "0")}-${slug}.png`), fullPage: true });
    await page.goto("http://localhost:3001/dashboard", { waitUntil: "domcontentloaded" });
    await settle();
    await dismissDashboardAlert();
  }

  const routes = [
    [5, "bookings-jobs", "/home-services/bookings-jobs"],
    [6, "assignment-dispatch", "/home-services/dispatch"],
    [7, "appointments", "/appointments"],
    [8, "availability", "/home-services/availability"],
    [9, "services-pricing", "/home-services/services"],
    [10, "service-areas", "/home-services/coverage"],
    [11, "inventory", "/inventory"],
    [12, "team-members", "/home-services/team"],
  ];
  for (const [number, slug, route] of routes) {
    await capture(number, slug, `http://localhost:3001${route}`);
  }
} catch (error) {
  result.error = error instanceof Error ? `${error.message}\n${error.stack}` : String(error);
} finally {
  result.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "current-results.json"), JSON.stringify(result, null, 2));
  await browser.close();
}

if (result.error) throw new Error(result.error);
