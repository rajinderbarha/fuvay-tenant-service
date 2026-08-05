/**
 * Regression tests for the reported bug: every restricted-shell sidebar
 * item (Setup Overview, Application Status, Submitted Setup, Activation
 * Center, Messages & Requests) rendered Application Status content
 * regardless of which was clicked.
 *
 * Root cause #1: "Submitted Setup" and "Messages & Requests" hrefs were
 * hash fragments (#submitted-setup / #messages) on the SAME route as
 * "Application Status" (/onboarding/application-status) — a same-route
 * hash link never changes the rendered page.
 *
 * Root cause #2: "Setup Overview" pointed at a page that calls
 * getRouting() on every mount and redirects away for any non-draft tenant
 * — i.e. it *always* bounces to Application Status for the exact lifecycle
 * states this restricted shell is shown in. Fixed by removing it from this
 * nav set rather than editing the shared resolver (out of scope / used
 * elsewhere as the real top-level landing gate).
 */
import { describe, it, expect } from "vitest";
import { RESTRICTED_NAV_ITEMS } from "../OnboardingShell";

describe("OnboardingShell RESTRICTED_NAV_ITEMS", () => {
  it("has a unique href for every item", () => {
    const hrefs = RESTRICTED_NAV_ITEMS.map(i => i.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("never uses a hash fragment as a navigation target", () => {
    for (const item of RESTRICTED_NAV_ITEMS) {
      expect(item.href.includes("#")).toBe(false);
    }
  });

  it("does not link to the self-redirecting Setup Overview route", () => {
    const hrefs = RESTRICTED_NAV_ITEMS.map(i => i.href);
    expect(hrefs).not.toContain("/tenant/home-services/setup/overview");
  });

  it("has a real route for Submitted Setup and Messages & Requests", () => {
    const byId = Object.fromEntries(RESTRICTED_NAV_ITEMS.map(i => [i.id, i.href]));
    expect(byId["submitted-setup"]).toBe("/onboarding/submitted-setup");
    expect(byId["messages"]).toBe("/onboarding/messages");
  });

  it("every item id matches a unique real Next.js route (no two ids share one page)", () => {
    // Application Status, Submitted Setup, Activation Center, Messages
    // must each resolve to a distinct app-router page file.
    const expected: Record<string, string> = {
      "application-status": "/onboarding/application-status",
      "submitted-setup":    "/onboarding/submitted-setup",
      "activation-center":  "/onboarding/activation-center",
      "messages":           "/onboarding/messages",
    };
    for (const item of RESTRICTED_NAV_ITEMS) {
      expect(item.href).toBe(expected[item.id]);
    }
  });
});
