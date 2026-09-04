import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const onboarding = readFileSync(resolve(root, "components/onboarding/OnboardingShell.tsx"), "utf8");
const operational = readFileSync(resolve(root, "components/layout/TenantLayout.tsx"), "utf8");
const registry = readFileSync(resolve(root, "lib/page-registry.ts"), "utf8");
const setupHeaderFiles = [
  "app/(onboarding)/tenant/home-services/setup/overview/page.tsx",
  "app/(onboarding)/tenant/home-services/setup/business-profile/BusinessProfileSetupPage.tsx",
  "app/(onboarding)/tenant/home-services/setup/documents/page.tsx",
  "components/services/ServicesPricingSetupPage.tsx",
  "app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx",
  "app/(onboarding)/tenant/home-services/setup/staff/StaffSetupPage.tsx",
  "app/(onboarding)/tenant/home-services/setup/finance/page.tsx",
  "app/(onboarding)/tenant/home-services/setup/review/page.tsx",
];

describe("provider shell structural parity", () => {
  it("uses the same shell contract in onboarding and operations", () => {
    for (const className of ["provider-app-shell", "provider-sidebar", "provider-topbar", "provider-main", "provider-content"]) {
      expect(onboarding).toContain(className);
      expect(operational).toContain(className);
    }
  });

  it("uses live notifications rather than a decorative unread dot", () => {
    expect(onboarding).toContain("providerNotifApi.unreadCount()");
    expect(onboarding).toContain("/provider/notifications");
    expect(onboarding).toContain("unreadCount > 0");
  });

  it("registers setup and post-submission pages for breadcrumbs", () => {
    for (const path of [
      "/tenant/home-services/setup/business-profile",
      "/tenant/home-services/setup/documents",
      "/tenant/home-services/setup/services-pricing",
      "/tenant/home-services/setup/coverage-availability",
      "/tenant/home-services/setup/staff",
      "/tenant/home-services/setup/finance",
      "/tenant/home-services/setup/review",
      "/onboarding/application-status",
      "/onboarding/activation-center",
    ]) {
      expect(registry).toContain(`"${path}"`);
    }
  });

  it("uses the shared notification-style page header across every setup step", () => {
    for (const file of setupHeaderFiles) {
      const source = readFileSync(resolve(root, file), "utf8");
      expect(source, file).toContain("PageShell");
      expect(source, file).toContain("PageHeader");
    }
  });

  it("keeps the primary provider navigation focused on daily work", () => {
    const primary = operational.match(/const NAV_GROUPS: NavGroup\[\] = \[([\s\S]*?)\n\];/)?.[1] ?? "";
    const itemIds = Array.from(primary.matchAll(/\{ id: "([^"]+)"/g), match => match[1]);

    expect(itemIds).toEqual([
      "dashboard",
      "hs-bookings-jobs",
      "hs-dispatch",
      "hs-availability",
      "customers",
      "hs-services",
      "hs-team",
      "hs-finance",
    ]);
    expect(operational).toContain("Manage business");
    expect(operational).toContain("SECONDARY_NAV_GROUPS");
  });
});
