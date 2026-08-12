import { chromium } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const action = process.env.HANDOFF_ACTION ?? "changes";
const tenantEmail = "visual.audit.1786461955262@example.com";
const tenantPassword = "VisualAudit!2026";
const note = "Please clarify the service coverage notes before resubmitting.";
const expected = action === "approve"
  ? { destination: "activation_center", pathname: "/onboarding/activation-center", text: /Activation Center/i }
  : { destination: "application_status", pathname: "/onboarding/application-status", text: /Changes requested/i };

const result = {
  action,
  started_at: new Date().toISOString(),
  admin: {},
  tenant: {},
  failed_responses: [],
  console_errors: [],
};

const browser = await chromium.launch({ headless: true });

function observe(page, portal) {
  page.on("response", response => {
    if (response.status() >= 400) {
      result.failed_responses.push({ portal, status: response.status(), url: response.url() });
    }
  });
  page.on("console", message => {
    if (message.type() === "error") result.console_errors.push({ portal, text: message.text() });
  });
}

try {
  const adminContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await adminContext.addInitScript(() => localStorage.setItem("serviceos_disable_tour_e2e", "true"));
  const admin = await adminContext.newPage();
  observe(admin, "admin");
  await admin.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  await admin.getByPlaceholder("you@serviceos.in").fill("admin@serviceos.in");
  await admin.getByPlaceholder("••••••••••").fill("Password123!");
  await admin.getByRole("button", { name: "Sign in" }).click();
  await admin.waitForURL(/\/admin\/dashboard/, { timeout: 30_000 });
  const skipTour = admin.getByText("Skip tour", { exact: true });
  if (await skipTour.isVisible()) await skipTour.click();

  await admin.goto("http://localhost:3000/admin/home-services/providers?tab=onboarding", { waitUntil: "networkidle" });
  await admin.getByPlaceholder("Search business, owner or email...").fill(tenantEmail);
  // The query matches owner email, while the compact table intentionally
  // renders only business/owner/status fields.
  const tenantRow = admin.getByRole("row").filter({ hasText: "Visual Audit Home Services" }).first();
  await tenantRow.waitFor({ timeout: 30_000 });
  // Next's development indicator can overlay the table in dev mode. Invoke
  // the row's DOM click directly so the product handler still runs.
  await tenantRow.evaluate(element => element.click());
  await admin.getByText("Review Provider", { exact: true }).waitFor();
  result.admin.queue_visible = true;
  await admin.screenshot({ path: path.join(auditDir, action === "approve" ? "26-admin-approval-review.png" : "23-admin-change-review.png"), fullPage: true });

  if (action === "approve") {
    await admin.getByRole("button", { name: "Approve setup" }).click();
  } else {
    await admin.getByRole("button", { name: "Request Changes" }).click();
    await admin.getByLabel("Changes required").fill(note);
    await admin.screenshot({ path: path.join(auditDir, "24-admin-change-form.png"), fullPage: true });
    await admin.getByRole("button", { name: "Send change request" }).click();
  }
  await admin.getByText("Review Provider", { exact: true }).waitFor({ state: "hidden", timeout: 30_000 });
  result.admin.decision_saved = true;
  await adminContext.close();

  const tenantContext = await browser.newContext({ viewport: { width: 1365, height: 900 } });
  const projectionResponse = await tenantContext.request.post("http://localhost:8000/v1/auth/login", {
    data: { email: tenantEmail, password: tenantPassword },
  });
  const projectionBody = await projectionResponse.json();
  result.tenant.login_destination = projectionBody?.data?.next_destination;
  result.tenant.reason_code = projectionBody?.data?.reason_code;
  const tenant = await tenantContext.newPage();
  observe(tenant, "tenant");
  await tenant.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
  await tenant.getByPlaceholder("Enter your email or mobile number").fill(tenantEmail);
  await tenant.getByPlaceholder("Enter your password").fill(tenantPassword);
  await tenant.getByRole("button", { name: /Sign in/ }).click();
  await tenant.waitForURL(url => url.pathname === expected.pathname, { timeout: 30_000 });
  await tenant.getByText(expected.text).first().waitFor({ timeout: 30_000 });
  result.tenant.pathname = new URL(tenant.url()).pathname;
  result.tenant.expected_destination = expected.destination;
  result.tenant.expected_pathname = expected.pathname;
  if (action === "changes") {
    result.tenant.note_visible = await tenant.getByText(note, { exact: true }).isVisible();
  }
  await tenant.screenshot({ path: path.join(auditDir, action === "approve" ? "27-tenant-activation-handoff.png" : "25-tenant-changes-handoff.png"), fullPage: true });
  await tenantContext.close();

  if (result.tenant.login_destination !== expected.destination || result.tenant.pathname !== expected.pathname) {
    throw new Error(`Handoff mismatch: ${JSON.stringify(result.tenant)}`);
  }
  if (result.failed_responses.length || result.console_errors.length) {
    throw new Error(`Browser errors: ${JSON.stringify({ failed_responses: result.failed_responses, console_errors: result.console_errors })}`);
  }
  result.passed = true;
} catch (error) {
  result.passed = false;
  result.error = error instanceof Error ? error.stack : String(error);
  throw error;
} finally {
  result.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, `handoff-${action}-results.json`), JSON.stringify(result, null, 2));
  await browser.close();
}
