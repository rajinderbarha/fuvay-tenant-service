import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const uploadFile = path.join(auditDir, "01-business-profile.png");
const requestedName = `Visual Audit Approved ${Date.now()}`;
const result = { requested_name: requestedName, failures: [], console_errors: [], steps: [] };
const browser = await chromium.launch({ headless: true });

function watch(page, surface) {
  page.on("response", response => {
    if (response.status() >= 400 && response.url().includes("/v1/")) {
      result.failures.push({ surface, status: response.status(), url: response.url() });
    }
  });
  page.on("console", message => {
    if (message.type() === "error") result.console_errors.push({ surface, text: message.text() });
  });
}

async function settle(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);
}

async function loginTenant(page) {
  const response = await page.request.post("http://127.0.0.1:8000/v1/auth/login", { data: {
    email: "visual.audit.1786461955262@example.com", password: "VisualAudit!2026",
  }});
  const body = await response.json();
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
  }, auth);
}

async function loginAdmin(page) {
  const response = await page.request.post("http://127.0.0.1:8000/v1/auth/login", { data: {
    email: "admin@serviceos.in", password: "Password123!",
  }});
  const body = await response.json();
  const auth = body.data ?? body;
  await page.goto("http://localhost:3000", { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.evaluate(data => {
    localStorage.setItem("serviceos_admin_token", data.access_token);
    localStorage.setItem("serviceos_admin_refresh", data.refresh_token ?? "");
    localStorage.setItem("serviceos-admin-tour-done", "true");
  }, auth);
}

try {
  const tenantContext = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await tenantContext.addInitScript(() => localStorage.setItem("serviceos-tenant-tour-done", "true"));
  const tenant = await tenantContext.newPage();
  watch(tenant, "tenant");
  await loginTenant(tenant);

  await tenant.goto("http://localhost:3001/profile", { waitUntil: "domcontentloaded", timeout: 90000 });
  await tenant.getByRole("heading", { level: 1, name: "Business Profile" }).waitFor({ timeout: 60000 });
  await settle(tenant);
  result.current_name = await tenant.getByLabel("Business name").inputValue();
  await tenant.screenshot({ path: path.join(auditDir, "final-01-profile-workspace.png"), fullPage: true });

  await tenant.getByLabel("Business name").fill(requestedName);
  await tenant.getByRole("button", { name: "Save profile changes" }).click();
  await tenant.getByText(/sent to ServiceOS for review/i).waitFor({ timeout: 30000 });
  result.steps.push("tenant_change_request_submitted");
  result.live_name_while_pending = await tenant.getByLabel("Business name").inputValue();
  await tenant.screenshot({ path: path.join(auditDir, "final-02-profile-change-pending.png"), fullPage: true });

  await tenant.goto("http://localhost:3001/business/verification-documents", { waitUntil: "domcontentloaded", timeout: 90000 });
  await tenant.getByRole("heading", { level: 1, name: "Documents & Verification" }).waitFor({ timeout: 60000 });
  await settle(tenant);
  await tenant.getByText("Fresh documents required for your profile change").waitFor();
  await tenant.screenshot({ path: path.join(auditDir, "final-03-documents-required.png"), fullPage: true });

  const uploadButton = tenant.getByRole("button", { name: /Upload|Replace/, exact: true }).first();
  await uploadButton.click();
  const fileInput = tenant.locator('input[type="file"]').last();
  await fileInput.setInputFiles(uploadFile);
  await tenant.getByText("Under admin review", { exact: true }).waitFor({ timeout: 30000 });
  result.steps.push("fresh_business_document_uploaded");
  await tenant.screenshot({ path: path.join(auditDir, "final-04-documents-submitted.png"), fullPage: true });

  const adminContext = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const admin = await adminContext.newPage();
  watch(admin, "admin");
  await loginAdmin(admin);
  await admin.goto("http://localhost:3000/admin/home-services/providers?tab=changes", { waitUntil: "domcontentloaded", timeout: 90000 });
  await admin.getByRole("button", { name: "Profile Change Requests" }).waitFor({ timeout: 60000 });
  await settle(admin);
  await admin.getByText(requestedName, { exact: true }).waitFor();
  await admin.getByText("Ready for decision", { exact: true }).waitFor();
  await admin.screenshot({ path: path.join(auditDir, "final-05-admin-change-queue.png"), fullPage: true });
  await admin.getByRole("button", { name: "Approve & publish" }).click();
  await admin.getByText("No profile changes are awaiting review.").waitFor({ timeout: 30000 });
  result.steps.push("admin_approved_and_published");
  await admin.screenshot({ path: path.join(auditDir, "final-06-admin-approved.png"), fullPage: true });

  await tenant.goto("http://localhost:3001/profile", { waitUntil: "domcontentloaded", timeout: 90000 });
  await tenant.getByRole("heading", { level: 1, name: "Business Profile" }).waitFor({ timeout: 60000 });
  await settle(tenant);
  result.published_name = await tenant.getByLabel("Business name").inputValue();
  result.pending_notice_cleared = await tenant.getByText(/awaiting review/i).count() === 0;
  await tenant.screenshot({ path: path.join(auditDir, "final-07-tenant-published.png"), fullPage: true });

  const routeChecks = [
    ["coverage_hours", "/business/coverage-hours", "Coverage & Hours"],
    ["coverage_workspace", "/home-services/coverage", "Coverage & Service Areas"],
    ["bookings_jobs", "/home-services/bookings-jobs", "Bookings & jobs"],
    ["dispatch", "/home-services/dispatch", "Dispatch board"],
    ["availability", "/home-services/availability", "Availability & Capacity"],
    ["services", "/home-services/services", "Services & Pricing"],
    ["inventory", "/inventory", "Inventory"],
    ["team", "/home-services/team", "Staff & Technicians"],
  ];
  result.routes = [];
  for (const [key, route, heading] of routeChecks) {
    await tenant.goto(`http://localhost:3001${route}`, { waitUntil: "domcontentloaded", timeout: 90000 });
    await tenant.getByRole("heading", { level: 1, name: heading }).waitFor({ timeout: 60000 });
    await settle(tenant);
    const axe = await new AxeBuilder({ page: tenant }).withTags(["wcag2a", "wcag2aa"]).analyze();
    result.routes.push({ key, route, final_path: new URL(tenant.url()).pathname, heading, serious_or_critical: axe.violations.filter(v => ["serious", "critical"].includes(v.impact ?? "")).map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })) });
  }
  await tenant.goto("http://localhost:3001/home-services/coverage", { waitUntil: "domcontentloaded", timeout: 90000 });
  await settle(tenant);
  result.coverage_service_options = await tenant.locator("select option").allTextContents();
  await tenant.screenshot({ path: path.join(auditDir, "final-08-coverage-workspace.png"), fullPage: true });

  result.success = result.published_name === requestedName && result.steps.length === 3;
  await tenantContext.close();
  await adminContext.close();
} catch (error) {
  result.error = error instanceof Error ? `${error.message}\n${error.stack}` : String(error);
} finally {
  result.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "handoff-results.json"), JSON.stringify(result, null, 2));
  await browser.close();
}

if (result.error || !result.success) throw new Error(result.error ?? "Handoff assertions failed");
