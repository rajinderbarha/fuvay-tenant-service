import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const onboarding = readFileSync(resolve(root, "components/onboarding/OnboardingShell.tsx"), "utf8");
const operational = readFileSync(resolve(root, "components/layout/TenantLayout.tsx"), "utf8");
const registry = readFileSync(resolve(root, "lib/page-registry.ts"), "utf8");

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
});
