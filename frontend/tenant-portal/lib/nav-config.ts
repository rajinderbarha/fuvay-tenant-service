/**
 * Sprint 34K — Centralized navigation config for the Tenant Portal.
 *
 * Single source of truth for provider/tenant sidebar groups and URL-to-nav-id mapping.
 */

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon?: string;
  group: string;
  permission?: string;
}

export interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

export const TENANT_NAV_GROUPS: NavGroup[] = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard", group: "overview" },
    ],
  },
  {
    id: "setup",
    label: "Setup",
    items: [
      { id: "profile",                  label: "Business Profile", href: "/profile",                  icon: "Building2",   group: "setup" },
      { id: "provider-service-areas",   label: "Service Areas",   href: "/provider/service-areas",   icon: "MapPin",      group: "setup" },
      { id: "provider-services",        label: "Service Setup",    href: "/tenant/setup/services",    icon: "Wrench",      group: "setup" },
      { id: "provider-service-coverage",label: "Service Coverage", href: "/provider/service-coverage",icon: "Shield",      group: "setup" },
      { id: "provider-availability",    label: "Availability",     href: "/provider/availability",    icon: "Clock",       group: "setup" },
    ],
  },
  {
    id: "team",
    label: "Team",
    items: [
      { id: "provider-staff", label: "Staff & Technicians", href: "/provider/staff", icon: "Users", group: "team" },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      { id: "finance-package",       label: "Package & Credits",     href: "/finance/package",              icon: "Package", group: "finance" },
      { id: "finance-credit-ledger", label: "Usage Credit Ledger",   href: "/finance/usage-credit-ledger",  icon: "Receipt", group: "finance" },
      { id: "finance-deposit",       label: "Security Deposit",      href: "/finance/security-deposit",     icon: "Shield",  group: "finance" },
    ],
  },
  {
    id: "more",
    label: "More",
    items: [
      { id: "documents",     label: "Documents",     href: "/documents",     icon: "FileText", group: "more" },
      { id: "provider-compliance", label: "Compliance",   href: "/provider/compliance", icon: "Shield", group: "more" },
      { id: "privacy",       label: "Privacy & Data", href: "/account/privacy", icon: "Shield", group: "more" },
      { id: "notifications", label: "Notifications", href: "/notifications", icon: "Bell",     group: "more" },
      { id: "activity",      label: "Activity",      href: "/activity",      icon: "Activity", group: "more" },
      { id: "settings",      label: "Settings",      href: "/settings",      icon: "Settings", group: "more" },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      { id: "jobs",         label: "Jobs",         href: "/jobs",         icon: "Wrench",       group: "operations" },
      { id: "bookings",     label: "Bookings",     href: "/bookings",     icon: "CalendarDays", group: "operations" },
      { id: "appointments", label: "Appointments", href: "/appointments", icon: "Calendar",     group: "operations" },
      { id: "dispatch",     label: "Dispatch",     href: "/dispatch",     icon: "Truck",        group: "operations" },
      { id: "operational-exceptions", label: "Operational Exceptions", href: "/operations/exceptions", icon: "AlertTriangle", group: "operations" },
    ],
  },
  {
    id: "engagement",
    label: "Engagement",
    items: [
      { id: "customers",  label: "Customers",  href: "/customers",  icon: "User",      group: "engagement" },
      { id: "reviews",    label: "Reviews",    href: "/reviews",    icon: "Star",      group: "engagement" },
      { id: "marketing",  label: "Marketing",  href: "/marketing",  icon: "Megaphone", group: "engagement" },
      { id: "chat",       label: "Chat",       href: "/chat",       icon: "MessageCircle", group: "engagement" },
    ],
  },
  {
    id: "insights",
    label: "Insights",
    items: [
      { id: "analytics", label: "Analytics", href: "/analytics", icon: "BarChart2", group: "insights" },
      { id: "reports",   label: "Reports",   href: "/reports",   icon: "PieChart",  group: "insights" },
    ],
  },
];

export const TENANT_NAV_BY_ID: Record<string, NavItem> = Object.fromEntries(
  TENANT_NAV_GROUPS.flatMap(g => g.items).map(item => [item.id, item])
);

export const TENANT_PATH_TO_NAV_ID: Record<string, string> = {
  dashboard:           "dashboard",
  profile:             "profile",
  settings:            "settings",
  privacy:             "profile",
  jobs:                "jobs",
  "service-jobs":      "jobs",
  bookings:            "bookings",
  appointments:        "appointments",
  dispatch:            "dispatch",
  "operations/exceptions": "operational-exceptions",
  "service-areas":     "provider-service-areas",
  staff:               "provider-staff",
  catalog:             "provider-services",
  inventory:           "provider-services",
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
  packages:            "finance-package",
  "onboarding-status": "provider-status",
  account:             "profile",
  activity:            "activity",
};

export const TENANT_PROVIDER_PATH_TO_NAV_ID: Record<string, string> = {
  status:               "provider-status",
  marketing:            "marketing",
  offerings:              "provider-services",
  "service-areas":        "provider-service-areas",
  "service-coverage":     "provider-service-coverage",
  "team-members":       "provider-staff",
  availability:         "provider-availability",
  services:             "provider-services",
  staff:                "provider-staff",
  wallet:               "finance-credit-ledger",
  "service-invoices":   "finance-package",
  complaints:           "reviews",
  "rework-requests":    "reviews",
  "refund-requests":    "reviews",
  compliance:           "provider-compliance",
  notifications:        "notifications",
  chat:                 "chat",
  "subscription-status": "finance-package",
};

export function resolveTenantNavId(pathname: string): string {
  const segs = pathname.split("/").filter(Boolean);
  const section = segs[0] ?? "dashboard";

  if (section === "provider") {
    const sub = segs[1] ?? "";
    return TENANT_PROVIDER_PATH_TO_NAV_ID[sub] ?? sub;
  }
  if (section === "analytics") return "analytics";
  if (section === "account" && segs[1] === "privacy") return "privacy";

  return TENANT_PATH_TO_NAV_ID[section] ?? section;
}
