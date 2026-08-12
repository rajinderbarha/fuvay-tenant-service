import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const result = { failures: [], console_errors: [], routes: [] };
const browser = await chromium.launch({ headless: true });

try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  page.on("response", response => {
    if (response.status() >= 400 && response.url().includes("/v1/")) result.failures.push({ status: response.status(), url: response.url() });
  });
  page.on("console", message => {
    if (message.type() === "error") result.console_errors.push(message.text());
  });
  const login = await page.request.post("http://127.0.0.1:8000/v1/auth/login", {
    data: { email: "provider@serviceos.in", password: "Password123!" },
  });
  const body = await login.json();
  const auth = body.data ?? body;
  await page.goto("http://localhost:3001", { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.evaluate(data => {
    localStorage.setItem("serviceos_tenant_token", data.access_token);
    localStorage.setItem("serviceos_tenant_refresh", data.refresh_token ?? "");
    localStorage.setItem("serviceos_user_id", data.user.id ?? data.user.user_id);
    localStorage.setItem("serviceos_tenant_id", data.user.tenant_id);
    localStorage.setItem("serviceos_user_role", data.user.role);
    localStorage.setItem("serviceos_tenant_name", data.tenant?.name ?? data.user.full_name);
    localStorage.setItem("serviceos_tenant_vertical", data.tenant?.vertical ?? "home_services");
    localStorage.setItem("serviceos-tenant-tour-done", "true");
  }, auth);

  const checks = [
    ["coverage", "/home-services/coverage", "Coverage & Service Areas"],
    ["bookings", "/home-services/bookings-jobs", "Bookings & jobs"],
    ["availability", "/home-services/availability", "Availability & Capacity"],
    ["team", "/home-services/team", "Staff & Technicians"],
    ["services", "/home-services/services", "Services & Pricing"],
  ];
  for (const [key, route, heading] of checks) {
    await page.goto(`http://localhost:3001${route}`, { waitUntil: "domcontentloaded", timeout: 90000 });
    await page.getByRole("heading", { level: 1, name: heading }).waitFor({ timeout: 60000 });
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
    const axe = await new AxeBuilder({ page }).withRules(["select-name"]).analyze();
    result.routes.push({ key, route, final_path: new URL(page.url()).pathname, select_name_violations: axe.violations.length });
  }

  await page.goto("http://localhost:3001/home-services/coverage", { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.getByRole("heading", { level: 1, name: "Coverage & Service Areas" }).waitFor({ timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  result.coverage_service_options = await page.locator("#coverage-test-service option").allTextContents();
  await page.screenshot({ path: path.join(auditDir, "final-09-data-rich-coverage.png"), fullPage: true });

  await page.goto("http://localhost:3001/home-services/services", { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.getByRole("heading", { level: 1, name: "Services & Pricing" }).waitFor({ timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  result.services_page_text = (await page.locator("main").innerText()).split("\n").filter(Boolean).slice(0, 40);
  await page.screenshot({ path: path.join(auditDir, "final-10-data-rich-services.png"), fullPage: true });
  result.success = result.failures.length === 0 && result.console_errors.length === 0 &&
    result.routes.every(route => route.final_path === route.route && route.select_name_violations === 0) &&
    result.coverage_service_options.length > 0 && !result.coverage_service_options.includes("No published services");
} catch (error) {
  result.error = error instanceof Error ? `${error.message}\n${error.stack}` : String(error);
} finally {
  result.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "route-results.json"), JSON.stringify(result, null, 2));
  await browser.close();
}
