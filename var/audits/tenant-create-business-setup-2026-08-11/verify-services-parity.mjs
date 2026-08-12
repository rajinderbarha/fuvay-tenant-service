import { chromium } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
// Seeded local E2E owner attached to the data-rich Guramrit tenant.  This
// script only reads its catalog; it deliberately does not add or edit rows.
const email = "provider@serviceos.in";
const password = "Password123!";
const results = { started_at: new Date().toISOString(), failed_responses: [], console_errors: [] };
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await context.addInitScript(() => localStorage.setItem("serviceos-tenant-tour-done", "true"));
const page = await context.newPage();

page.on("response", response => {
  if (response.status() >= 400 && response.url().includes("/v1/")) {
    results.failed_responses.push({ status: response.status(), url: response.url() });
  }
});
page.on("console", message => {
  if (message.type() === "error") results.console_errors.push(message.text());
});

function data(body) {
  return body?.data ?? body;
}
async function responseJson(promise) {
  const response = await promise;
  return data(await response.json());
}
function sorted(values) {
  return [...values].sort();
}

try {
  await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
  await page.getByPlaceholder("Enter your email or mobile number").fill(email);
  await page.getByPlaceholder("Enter your password").fill(password);
  await page.getByRole("button", { name: /Sign in/ }).click();
  await page.waitForURL(url => url.pathname !== "/login", { timeout: 30_000 });

  let workspacePromise = page.waitForResponse(response =>
    response.url().endsWith("/v1/tenant/home-services/services") && response.request().method() === "GET");
  await page.goto("http://localhost:3001/home-services/services", { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { level: 1, name: "Services & Pricing" }).waitFor();
  let workspace = await responseJson(workspacePromise);

  results.initial_enabled_count = workspace.summary.enabled_services;
  if (workspace.summary.enabled_services === 0) throw new Error("The data-rich parity fixture unexpectedly has no enabled services.");

  await page.getByRole("button", { name: "Add services" }).click();
  await page.getByRole("heading", { level: 2, name: "Add services" }).waitFor();
  await page.waitForTimeout(750);
  results.add_dialog_works = true;
  results.add_candidates = await page.getByRole("button", { name: "Add", exact: true }).count();
  results.add_catalog_complete = await page.getByText("Every available service is already in your catalog.", { exact: true }).isVisible().catch(() => false);
  if (results.add_candidates === 0 && !results.add_catalog_complete) {
    throw new Error("Add Services loaded neither available catalog rows nor the complete-catalog state.");
  }
  await page.getByRole("button", { name: "Close", exact: true }).click();

  workspacePromise = page.waitForResponse(response =>
    response.url().endsWith("/v1/tenant/home-services/services") && response.request().method() === "GET");
  await page.goto("http://localhost:3001/home-services/services", { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { level: 1, name: "Services & Pricing" }).waitFor();
  workspace = await responseJson(workspacePromise);
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.screenshot({ path: path.join(auditDir, "services-parity-01-dashboard.png"), fullPage: true });

  await page.getByRole("button", { name: "Preview customer view" }).click();
  await page.getByRole("heading", { level: 2, name: "Customer catalog preview" }).waitFor();
  results.preview_works = true;
  await page.screenshot({ path: path.join(auditDir, "services-parity-02-customer-preview.png"), fullPage: true });
  await page.getByRole("button", { name: "Close", exact: true }).click();

  const detailsById = {};
  for (const service of workspace.catalog_tree.flatMap(group => group.services)) {
    const detailPromise = page.waitForResponse(response =>
      response.url().endsWith(`/v1/tenant/home-services/services/${service.tenant_service_id}`) && response.request().method() === "GET");
    await page.goto(`http://localhost:3001/home-services/services/${service.tenant_service_id}`, { waitUntil: "domcontentloaded" });
    detailsById[service.tenant_service_id] = await responseJson(detailPromise);
  }

  const enabledPromise = page.waitForResponse(response =>
    response.url().includes("/v1/tenant/catalog/home-services/enabled-services") && response.request().method() === "GET");
  const availablePromise = page.waitForResponse(response =>
    response.url().includes("/v1/tenant/catalog/home-services/available-services") && response.request().method() === "GET");
  await page.goto("http://localhost:3001/tenant/home-services/setup/services-pricing?return_to=/home-services/services", { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { level: 1, name: "Services & pricing" }).waitFor();
  const enabled = await responseJson(enabledPromise);
  const available = await responseJson(availablePromise);
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.screenshot({ path: path.join(auditDir, "services-parity-03-setup.png"), fullPage: true });

  const workspaceServices = workspace.catalog_tree.flatMap(group => group.services);
  const workspaceById = Object.fromEntries(workspaceServices.map(service => [service.tenant_service_id, service]));
  const setupById = Object.fromEntries(enabled.services.map(service => [service.tenant_service_id, service]));
  const availableByMasterId = Object.fromEntries(available.services.map(service => [service.service_id, service]));
  const workspaceIds = sorted(Object.keys(workspaceById));
  const setupIds = sorted(Object.keys(setupById));

  results.workspace_summary = workspace.summary;
  results.workspace_ids = workspaceIds;
  results.setup_ids = setupIds;
  results.same_service_ids = JSON.stringify(workspaceIds) === JSON.stringify(setupIds);
  results.same_master_service_ids = JSON.stringify(sorted(workspaceServices.map(service => service.master_service_id))) ===
    JSON.stringify(sorted(enabled.services.map(service => service.master_service_id)));
  results.same_statuses = workspaceIds.every(id => workspaceById[id].setup_status === setupById[id].setup_status);
  const blueprintFields = ["requires_issue_type", "requires_checklist", "requires_estimate_approval", "requires_technician", "requires_schedule"];
  results.same_blueprints = workspaceIds.every(id => {
    const master = availableByMasterId[workspaceById[id].master_service_id];
    const detail = detailsById[id];
    return master && detail &&
      detail.blueprint.type_mode === (master.is_type_required ? "required" : "optional") &&
      detail.blueprint.brand_mode === (master.is_brand_required ? "required" : "optional") &&
      blueprintFields.every(field => detail.blueprint[field] === master[field]) &&
      detail.blueprint.workflow_version === master.workflow_version &&
      detail.blueprint.source === master.blueprint_source;
  });
  const rawPriceFields = ["tenant_min_price", "tenant_max_price", "tenant_visit_fee", "tenant_emergency_surcharge"];
  results.same_tenant_prices = workspaceIds.every(id =>
    rawPriceFields.every(field => detailsById[id].tenant_service[field] === setupById[id][field]));
  results.counts_match = workspace.summary.enabled_services === enabled.services.length &&
    workspace.summary.published + workspace.summary.draft === enabled.services.length;
  results.no_horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
  results.passed = results.same_service_ids && results.same_master_service_ids && results.same_statuses &&
    results.same_blueprints && results.same_tenant_prices &&
    results.counts_match && results.preview_works && results.add_dialog_works && results.no_horizontal_overflow &&
    results.failed_responses.length === 0 && results.console_errors.length === 0;
  if (!results.passed) throw new Error(`Services parity failed: ${JSON.stringify(results)}`);
} catch (error) {
  results.passed = false;
  results.error = error instanceof Error ? error.stack : String(error);
  throw error;
} finally {
  results.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "services-parity-results.json"), JSON.stringify(results, null, 2));
  await browser.close();
}
