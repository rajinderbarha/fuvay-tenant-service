import { chromium } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const auditDir = path.dirname(fileURLToPath(import.meta.url));
const requestedName = "Visual Audit Approved 1786474087225";
const result = { requested_name: requestedName, steps: [], failures: [] };
const browser = await chromium.launch({ headless: true });

async function seedSession(page, baseUrl, email, password, admin = false) {
  const response = await page.request.post("http://127.0.0.1:8000/v1/auth/login", { data: { email, password } });
  const body = await response.json();
  const auth = body.data ?? body;
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.evaluate(({ auth, admin }) => {
    localStorage.setItem(admin ? "serviceos_admin_token" : "serviceos_tenant_token", auth.access_token);
    localStorage.setItem(admin ? "serviceos_admin_refresh" : "serviceos_tenant_refresh", auth.refresh_token ?? "");
    if (admin) localStorage.setItem("serviceos-admin-tour-done", "true");
    if (!admin) {
      localStorage.setItem("serviceos_user_id", auth.user.id ?? auth.user.user_id);
      localStorage.setItem("serviceos_tenant_id", auth.user.tenant_id);
      localStorage.setItem("serviceos_user_role", auth.user.role);
      localStorage.setItem("serviceos_tenant_name", auth.tenant?.name ?? auth.user.full_name);
      localStorage.setItem("serviceos_tenant_vertical", auth.tenant?.vertical ?? "home_services");
      localStorage.setItem("serviceos-tenant-tour-done", "true");
    }
  }, { auth, admin });
}

try {
  const admin = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  admin.on("response", response => {
    if (response.status() >= 400 && response.url().includes("/v1/")) result.failures.push({ status: response.status(), url: response.url() });
  });
  await seedSession(admin, "http://localhost:3000", "admin@serviceos.in", "Password123!", true);
  await admin.goto("http://localhost:3000/admin/home-services/providers?tab=changes", { waitUntil: "domcontentloaded", timeout: 90000 });
  await admin.getByText(requestedName, { exact: true }).waitFor({ timeout: 60000 });
  await admin.getByText("Ready for decision", { exact: true }).waitFor();
  await admin.screenshot({ path: path.join(auditDir, "final-05-admin-change-queue.png"), fullPage: true });
  await admin.getByRole("button", { name: "Approve & publish" }).click();
  await admin.getByText("No profile changes are awaiting review.").waitFor({ timeout: 30000 });
  result.steps.push("admin_approved_and_published");
  await admin.screenshot({ path: path.join(auditDir, "final-06-admin-approved.png"), fullPage: true });

  const tenant = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await seedSession(tenant, "http://localhost:3001", "visual.audit.1786461955262@example.com", "VisualAudit!2026");
  await tenant.goto("http://localhost:3001/profile", { waitUntil: "domcontentloaded", timeout: 90000 });
  await tenant.getByRole("heading", { level: 1, name: "Business Profile" }).waitFor({ timeout: 60000 });
  result.published_name = await tenant.getByLabel("Business name").inputValue();
  result.pending_notice_cleared = await tenant.getByText(/awaiting review/i).count() === 0;
  await tenant.screenshot({ path: path.join(auditDir, "final-07-tenant-published.png"), fullPage: true });
  result.success = result.published_name === requestedName && result.pending_notice_cleared && result.failures.length === 0;
} catch (error) {
  result.error = error instanceof Error ? `${error.message}\n${error.stack}` : String(error);
} finally {
  result.finished_at = new Date().toISOString();
  await writeFile(path.join(auditDir, "resume-results.json"), JSON.stringify(result, null, 2));
  await browser.close();
}
