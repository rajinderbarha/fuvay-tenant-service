/**
 * URL-to-navigation identity resolver for the Tenant Portal.
 *
 * The rendered destinations live in TenantLayout; this module only maps
 * canonical and compatibility URLs to their active destination identity.
 */

export const TENANT_PATH_TO_NAV_ID: Record<string, string> = {
  dashboard:           "dashboard",
  profile:             "profile",
  settings:            "settings",
  jobs:                "jobs",
  "service-jobs":      "jobs",
  bookings:            "jobs",
  appointments:        "appointments",
  dispatch:            "dispatch",
  "operations/exceptions": "operational-exceptions",
  "service-areas":     "business-hours",
  staff:               "provider-staff",
  catalog:             "provider-services",
  inventory:           "inventory",
  documents:           "documents",
  finance:             "finance-package",
  customers:           "customers",
  reviews:             "reviews",
  marketing:           "marketing",
  notifications:       "notifications",
  chat:                "chat",
  analytics:           "analytics",
  reports:             "reports",
  insights:            "analytics",
  media:               "provider-services",
  "onboarding-status": "provider-status",
  account:             "profile",
  activity:            "activity",
};

export const TENANT_PROVIDER_PATH_TO_NAV_ID: Record<string, string> = {
  status:               "provider-status",
  marketing:            "marketing",
  offerings:              "provider-services",
  "service-areas":        "business-hours",
  "service-coverage":     "provider-service-coverage",
  "team-members":       "provider-staff",
  availability:         "provider-availability",
  services:             "provider-services",
  staff:                "provider-staff",
  wallet:               "finance-credit-ledger",
  "service-invoices":   "finance-package",
  complaints:           "reviews",
  "rework-requests":    "reviews",
  "refund-requests":    "hs-remedies",
  compliance:           "provider-compliance",
  notifications:        "notifications",
  chat:                 "chat",
};

export function resolveTenantNavId(pathname: string): string {
  const segs = pathname.split("/").filter(Boolean);
  const section = segs[0] ?? "dashboard";

  // Home Services workspaces are two-segment routes whose nav ids are
  // "hs-<sub>" (see TenantLayout NAV_GROUPS).
  if (section === "home-services") {
    const sub = segs[1] ?? "";
    if (sub === "coverage") return "business-hours";
    if (sub === "direct-payments") return "hs-finance";
    return sub ? `hs-${sub}` : "hs-bookings-jobs";
  }
  if (section === "business" && segs[1] === "coverage-hours") return "business-hours";

  // The onboarding wizard lives at /tenant/home-services/setup/* and is a
  // single nav entry ("Business Setup"), so every step highlights it.
  if (section === "tenant" && segs[1] === "home-services" && segs[2] === "setup") {
    return "hs-setup";
  }
  if (section === "help-support") return "help-support";

  if (section === "provider") {
    const sub = segs[1] ?? "";
    return TENANT_PROVIDER_PATH_TO_NAV_ID[sub] ?? sub;
  }
  if (section === "analytics") return "analytics";

  return TENANT_PATH_TO_NAV_ID[section] ?? section;
}
