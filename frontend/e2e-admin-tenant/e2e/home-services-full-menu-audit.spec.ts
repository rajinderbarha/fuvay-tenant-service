import { test, expect, type Browser, type Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const ROOT = path.resolve(__dirname, "../../..");
const AUDIT_DIR = path.join(ROOT, "artifacts", "home-services-menu-audit");
const SCREENSHOT_DIR = path.join(AUDIT_DIR, "screenshots");

const PASSWORD = "Password123!";

type AuditResult = {
  role: string;
  label: string;
  requestedUrl: string;
  finalUrl: string;
  status: number | null;
  bodyLength: number;
  consoleErrors: string[];
  failedResponses: string[];
  screenshot: string;
};

const ADMIN_ROUTES = [
  ["Categories", "/admin/categories"],
  ["Service Groups", "/admin/service-groups"],
  ["Master Services", "/admin/master-services"],
  ["Types & Brands", "/admin/types-brands"],
  ["Checklists", "/admin/checklists"],
  ["Service Catalog", "/admin/catalog-workspace"],
  ["Overview", "/admin/home-services/dashboard"],
  ["Home Services Settings", "/admin/home-services/settings"],
  ["Provider Bookability", "/admin/bookability/providers"],
  ["Providers", "/admin/home-services/providers"],
  ["Bookings & Jobs", "/admin/home-services/bookings-jobs"],
  ["Home Services Finance", "/admin/home-services/finance"],
] as const;

const TENANT_ROUTES = [
  ["Dashboard", "/dashboard"],
  ["Bookings & Jobs", "/home-services/bookings-jobs"],
  ["Dispatch", "/home-services/dispatch"],
  ["Availability", "/home-services/availability"],
  ["Customers", "/customers"],
  ["Services & Pricing", "/home-services/services"],
  ["Team Members", "/home-services/team"],
  ["Finance & Credits", "/home-services/finance"],
  ["Business Profile", "/profile"],
  ["Coverage & Hours", "/business/coverage-hours"],
  ["Parts & Inventory", "/inventory"],
  ["Reviews", "/home-services/reviews"],
  ["Complaints", "/home-services/complaints"],
  ["Refunds & Warranty", "/provider/refund-requests"],
  ["Direct Payments", "/home-services/direct-payments"],
  ["Media", "/media"],
  ["Reports", "/reports"],
  ["Activity & Audit", "/activity"],
  ["Settings", "/settings"],
  ["Help & Support", "/help-support"],
] as const;

const STAFF_ROUTES = [
  ["Dashboard", "/staff/dashboard"],
  ["My Profile", "/staff/profile"],
  ["Skills & Services", "/staff/skills"],
  ["Service Areas", "/staff/service-areas"],
  ["Availability", "/staff/availability"],
  ["Assigned Work", "/staff/jobs"],
  ["Notifications", "/staff/notifications"],
  ["Security / Sessions", "/staff/security/sessions"],
] as const;

function safeName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function writeResults(role: string, results: AuditResult[]) {
  fs.mkdirSync(AUDIT_DIR, { recursive: true });
  fs.writeFileSync(
    path.join(AUDIT_DIR, `${role}-results.json`),
    JSON.stringify(results, null, 2),
    "utf8",
  );
}

async function verifyVisibleMenu(
  page: Page,
  role: string,
  routes: readonly (readonly [string, string])[],
) {
  const inventory: Array<{ label: string; href: string; visible: boolean }> = [];
  for (const [label, href] of routes) {
    const link = page.locator(`a[href="${href}"]`).filter({ visible: true }).first();
    await expect(link, `${role} menu must expose ${label}`).toBeVisible({ timeout: 20_000 });
    inventory.push({ label, href, visible: true });
  }
  fs.mkdirSync(AUDIT_DIR, { recursive: true });
  fs.writeFileSync(
    path.join(AUDIT_DIR, `${role}-menu-inventory.json`),
    JSON.stringify(inventory, null, 2),
    "utf8",
  );
}

async function signIn(page: Page, baseUrl: string, loginPath: string, email: string) {
  await page.goto(`${baseUrl}${loginPath}`, { waitUntil: "domcontentloaded" });
  // Admin login replaces its initial form state after the platform-health
  // probe. Filling during that probe races the replacement and can clear the
  // password before submit, so wait for the settled status first.
  if (loginPath === "/login" && baseUrl.endsWith(":3000")) {
    await expect(page.getByText(/Platform operational|Platform status unavailable/)).toBeVisible({
      timeout: 20_000,
    });
  }
  const emailInput = page.locator('input[type="email"]');
  const passwordInput = page.locator('input[type="password"]');
  await emailInput.fill(email);
  await passwordInput.fill(PASSWORD);
  await expect(emailInput).toHaveValue(email);
  await expect(passwordInput).toHaveValue(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(
    url => !url.pathname.includes("/login") && !url.pathname.includes("/change-password"),
    { timeout: 30_000 },
  );
  await page.waitForLoadState("domcontentloaded");

  // The provider test fixture may encounter the updated-terms gate after a
  // policy release. Accepting it is part of the real provider journey and
  // keeps the remaining menu audit on the authenticated workspace.
  const acceptance = page.getByText("Review our updated provider terms");
  if (await acceptance.isVisible().catch(() => false)) {
    await page.locator('input[type="checkbox"]').check();
    await page.getByRole("button", { name: /accept/i }).click();
    await expect(acceptance).toBeHidden({ timeout: 20_000 });
  }
}

async function establishTenantSession(
  page: Page,
  baseUrl: string,
  email: string,
  destination: string,
  acceptProviderTerms = false,
) {
  const loginResponse = await page.request.post("http://localhost:8000/v1/auth/login", {
    data: { email, password: PASSWORD },
  });
  expect(loginResponse.ok(), `${email} API login must succeed`).toBeTruthy();
  const envelope = await loginResponse.json();
  const data = envelope.data ?? envelope;
  const user = data.user ?? {};
  const tenant = data.tenant ?? {};

  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate(({ data, user, tenant }) => {
    window.localStorage.setItem("serviceos_tenant_token", data.access_token);
    if (data.refresh_token) window.localStorage.setItem("serviceos_tenant_refresh", data.refresh_token);
    window.localStorage.setItem("serviceos_user_id", user.id ?? user.user_id ?? "");
    window.localStorage.setItem("serviceos_tenant_id", user.tenant_id ?? "");
    window.localStorage.setItem("serviceos_user_role", user.role ?? "");
    window.localStorage.setItem("serviceos_tenant_name", tenant.name ?? user.full_name ?? "");
    window.localStorage.setItem("serviceos_tenant_vertical", tenant.vertical ?? "");
    window.localStorage.setItem("serviceos_tenant_health", String(tenant.health_score ?? 0));
  }, { data, user, tenant });
  await page.goto(`${baseUrl}${destination}`, { waitUntil: "domcontentloaded" });
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });

  const acceptance = page.getByText("Review our updated provider terms");
  if (acceptProviderTerms) {
    const termsVisible = await acceptance.isVisible({ timeout: 3_000 }).catch(() => false);
    if (termsVisible) {
      await page.locator('input[type="checkbox"]').check();
      const acceptButton = page.getByRole("button", { name: "Accept and continue" });
      await expect(acceptButton).toBeVisible();
      await expect(acceptButton).toBeEnabled();
      await acceptButton.click();
      await expect(acceptance).toBeHidden({ timeout: 20_000 });
    }
  }
}

async function captureRoutes(
  page: Page,
  role: string,
  baseUrl: string,
  routes: readonly (readonly [string, string])[],
) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const results: AuditResult[] = [];

  for (let index = 0; index < routes.length; index += 1) {
    const [label, route] = routes[index];
    const routePage = await page.context().newPage();
    const consoleErrors: string[] = [];
    const failedResponses: string[] = [];
    routePage.on("console", msg => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    routePage.on("response", response => {
      if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.request().method()} ${response.url()}`);
    });
    routePage.on("requestfailed", request => {
      failedResponses.push(`FAILED ${request.method()} ${request.url()} ${request.failure()?.errorText ?? ""}`);
    });

    const response = await routePage.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded" });
    await routePage.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => undefined);
    await routePage.waitForTimeout(1_000);
    await expect(routePage.locator(".ds-skeleton")).toHaveCount(0, { timeout: 30_000 });

    const bodyText = await routePage.locator("body").innerText();
    const currentConsoleErrors = [...consoleErrors];
    const currentFailures = [...failedResponses];
    const screenshotName = `${role}-${String(index + 1).padStart(2, "0")}-${safeName(label)}.png`;
    const screenshotPath = path.join(SCREENSHOT_DIR, screenshotName);

    await routePage.screenshot({ path: screenshotPath, fullPage: true });

    results.push({
      role,
      label,
      requestedUrl: `${baseUrl}${route}`,
      finalUrl: routePage.url(),
      status: response?.status() ?? null,
      bodyLength: bodyText.trim().length,
      consoleErrors: currentConsoleErrors,
      failedResponses: currentFailures,
      screenshot: path.relative(ROOT, screenshotPath).replaceAll("\\", "/"),
    });

    const meaningfulFailures = currentFailures.filter(
      item => /^(5\d\d|FAILED)/.test(item)
        && !/net::ERR_ABORTED/i.test(item)
        && !/_next\/static\/.*hot-update/i.test(item),
    );
    expect.soft(response?.status(), `${role} ${label} HTTP status`).toBeLessThan(400);
    expect.soft(routePage.url(), `${role} ${label} must not redirect to login`).not.toContain("/login");
    expect.soft(bodyText.trim().length, `${role} ${label} must render meaningful content`).toBeGreaterThan(80);
    expect.soft(bodyText, `${role} ${label} must not render an application failure`).not.toMatch(
      /Application error|Internal Server Error|This page could not be found/i,
    );
    expect.soft(
      meaningfulFailures,
      `${role} ${label} must not produce server/network failures`,
    ).toEqual([]);
    expect.soft(bodyText, `${role} ${label} must not expose an unfinished placeholder`).not.toMatch(
      /not yet available in this app|has not been built yet/i,
    );
    await routePage.close();
  }

  writeResults(role, results);
}

async function newAuditPage(browser: Browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript(() => {
    window.localStorage.setItem("serviceos_disable_tour_e2e", "true");
    window.localStorage.setItem("serviceos-tenant-tour-done", "true");
  });
  const page = await context.newPage();
  return { context, page };
}

test.describe.serial("Home Services full menu audit", () => {
  test("super-admin menu pages", async ({ browser }) => {
    test.setTimeout(6 * 60_000);
    const { context, page } = await newAuditPage(browser);
    await signIn(page, "http://localhost:3000", "/login", "admin@serviceos.in");
    const homeServicesButton = page.locator("button.admin-vertical-item").filter({ hasText: "Home Services" }).first();
    await expect(homeServicesButton).toBeVisible({ timeout: 20_000 });
    await homeServicesButton.click();
    await verifyVisibleMenu(page, "admin", ADMIN_ROUTES);
    await captureRoutes(page, "admin", "http://localhost:3000", ADMIN_ROUTES);
    await context.close();
  });

  test("tenant owner menu pages", async ({ browser }) => {
    test.setTimeout(12 * 60_000);
    const { context, page } = await newAuditPage(browser);
    await establishTenantSession(
      page, "http://localhost:3001", "provider@serviceos.in", "/dashboard", true,
    );
    await verifyVisibleMenu(page, "tenant-primary", TENANT_ROUTES.slice(0, 8));
    await page.getByRole("button", { name: "Manage business", exact: true }).click();
    await verifyVisibleMenu(page, "tenant-secondary", TENANT_ROUTES.slice(8));
    await captureRoutes(page, "tenant", "http://localhost:3001", TENANT_ROUTES);
    await context.close();
  });

  test("staff technician menu pages", async ({ browser }) => {
    test.setTimeout(8 * 60_000);
    const { context, page } = await newAuditPage(browser);
    await establishTenantSession(page, "http://localhost:3001", "staff@serviceos.in", "/staff/dashboard");
    await verifyVisibleMenu(page, "staff", STAFF_ROUTES);
    await captureRoutes(page, "staff", "http://localhost:3001", STAFF_ROUTES);
    await context.close();
  });
});
