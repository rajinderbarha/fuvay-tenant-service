import { test, expect } from "@playwright/test";

/** DESIGN PHASE UX-04B — first real headless-browser smoke pass for the
 * UX-04/04A/04B showcase routes. Runs across 3 Playwright projects
 * (desktop-light, desktop-dark, mobile — see playwright.config.ts), so
 * every route is exercised in light+dark and desktop+mobile viewports. */

const ROUTES = [
  "/dev/ux-04",
  "/dev/ux-04/command-center",
  "/dev/ux-04/booking-list",
  "/dev/ux-04/booking-detail",
  "/dev/ux-04/job-detail",
  "/dev/ux-04/field-ops-job-detail",
  "/dev/ux-04/inspection",
  "/dev/ux-04/status-transition",
  "/dev/ux-04/assignment-workspace",
  "/dev/ux-04/parts-approval",
  "/dev/ux-04/parts-list",
  "/dev/ux-04/checklist-execution",
  "/dev/ux-04/complaints",
  "/dev/ux-04/media",
  "/dev/ux-04/sla-risk",
  "/dev/ux-04/operational-exceptions",
  "/dev/ux-04/staff-home",
  "/dev/ux-04/read-only",
];

for (const route of ROUTES) {
  test(`route loads with no console/page errors: ${route}`, async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(String(err)));

    const response = await page.goto(route, { waitUntil: "networkidle" });
    expect(response?.status(), `${route} should return 200`).toBe(200);
    await expect(page.locator("body")).toBeVisible();

    const hydrationErrors = [...consoleErrors, ...pageErrors].filter((e) =>
      /hydrat|Minified React error #(418|419|421|422|425)/i.test(e)
    );
    expect(hydrationErrors, `${route} hydration errors: ${hydrationErrors.join("\n")}`).toHaveLength(0);
    expect(pageErrors, `${route} page errors: ${pageErrors.join("\n")}`).toHaveLength(0);
    expect(consoleErrors, `${route} console errors: ${consoleErrors.join("\n")}`).toHaveLength(0);
  });
}

test("pipeline labels stay distinct on booking-list", async ({ page }) => {
  await page.goto("/dev/ux-04/booking-list", { waitUntil: "networkidle" });
  await expect(page.getByText("field_ops.Job", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("ServiceJob", { exact: false }).first()).toBeVisible();
});

test("field_ops.Job detail never renders ServiceJob-only section headings", async ({ page }) => {
  await page.goto("/dev/ux-04/field-ops-job-detail", { waitUntil: "networkidle" });
  const headings = await page.locator("h2").allTextContents();
  for (const forbidden of ["Quote", "Checklist", "Parts requests", "Credit"]) {
    expect(headings.some((h) => h.toLowerCase() === forbidden.toLowerCase())).toBe(false);
  }
});
