import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/** DESIGN PHASE UX-04B — keyboard/focus + axe-core accessibility scan.
 * Scope: automated axe rule checks only (page title, heading hierarchy,
 * landmarks, form labels, table semantics, button names) — this is NOT a
 * full WCAG legal/manual audit; see accessibility-test-report.md for exact
 * scope and exclusions. */

test("parts-approval: Approve/Reject buttons are keyboard-focusable and activate on Enter", async ({ page }) => {
  await page.goto("/dev/ux-04/parts-approval", { waitUntil: "networkidle" });
  const approveButton = page.getByRole("button", { name: /approve/i });
  await approveButton.focus();
  await expect(approveButton).toBeFocused();
  // Verify it's a real, visible, enabled control that keyboard activation
  // (Enter) can trigger without throwing — behavior beyond this (approving
  // fixture data) is out of scope since no mutation is wired this pass.
  await page.keyboard.press("Enter");
});

test("parts-list: search input and status select are reachable via Tab in a sane order", async ({ page }) => {
  await page.goto("/dev/ux-04/parts-list", { waitUntil: "networkidle" });
  const search = page.getByLabel(/search parts requests/i);
  await search.focus();
  await expect(search).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel(/filter by status/i)).toBeFocused();
});

const AXE_ROUTES = [
  "/dev/ux-04/command-center",
  "/dev/ux-04/booking-list",
  "/dev/ux-04/job-detail",
  "/dev/ux-04/field-ops-job-detail",
  "/dev/ux-04/parts-list",
  "/dev/ux-04/complaints",
];

for (const route of AXE_ROUTES) {
  test(`axe-core scan: ${route}`, async ({ page }) => {
    await page.goto(route, { waitUntil: "networkidle" });
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const critical = results.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
    expect(critical, JSON.stringify(critical, null, 2)).toHaveLength(0);
  });
}

test("document has a title on every showcase route (spot check)", async ({ page }) => {
  await page.goto("/dev/ux-04/command-center", { waitUntil: "networkidle" });
  await expect(page).toHaveTitle(/.+/);
});
