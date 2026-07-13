/**
 * Sprint 34K — Centralized navigation config for the Super-Admin portal.
 *
 * Single source of truth for sidebar groups, nav items, and URL-to-nav-id mapping.
 * Import this in layout.tsx instead of hardcoding navigation inline.
 */

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon?: string;
  group: string;
  permission?: string;  // future: permission key for visibility control
}

export interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

/** All admin sidebar navigation groups in display order. */
export const ADMIN_NAV_GROUPS: NavGroup[] = [
  {
    id: "core",
    label: "Core",
    items: [
      { id: "dashboard",   label: "Dashboard",   href: "/admin/dashboard",   icon: "🏠", group: "core" },
      { id: "tenants",     label: "Tenants",     href: "/admin/tenants",     icon: "🏢", group: "core" },
      { id: "users",       label: "Users",       href: "/admin/users",       icon: "👤", group: "core" },
      { id: "customers",   label: "Customers",   href: "/admin/customers",   icon: "🧑", group: "core" },
      { id: "staff",       label: "Staff",       href: "/admin/staff",       icon: "👷", group: "core" },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      { id: "bookings",       label: "Bookings",       href: "/admin/bookings",       icon: "📅", group: "operations" },
      { id: "operations",     label: "Operations",     href: "/admin/operations",     icon: "⚙️", group: "operations" },
      { id: "real-estate",    label: "Real Estate",    href: "/admin/real-estate/lead-drafts",                  icon: "🏘️", group: "operations" },
      { id: "coaching",       label: "Coaching",       href: "/admin/coaching/appointment-drafts",              icon: "📚", group: "operations" },
      { id: "bookability",    label: "Bookability",    href: "/admin/bookability/providers",                    icon: "✅", group: "operations" },
      { id: "onboarding",     label: "Onboarding",     href: "/admin/onboarding/providers",                     icon: "🚀", group: "operations" },
    ],
  },
  {
    id: "home-services",
    label: "Home Services",
    items: [
      { id: "hs-bookings",         label: "Bookings",                  href: "/admin/home-services/booking-drafts",             icon: "🏠", group: "home-services" },
      { id: "hs-service-catalog",  label: "Service Catalog",           href: "/admin/home-services/service-catalog",            icon: "🗂️", group: "home-services" },
      { id: "hs-pricing-rules",    label: "Pricing Rules",             href: "/admin/home-services/pricing-rules",              icon: "💲", group: "home-services" },
      { id: "hs-price-experience", label: "Customer Price Experience", href: "/admin/home-services/price-experience",           icon: "🧾", group: "home-services" },
      { id: "hs-provider-matching",label: "Provider Matching",         href: "/admin/home-services/provider-matching",          icon: "🔗", group: "home-services" },
      { id: "hs-matching-diagnostics", label: "Matching Diagnostics",  href: "/admin/home-services/matching-diagnostics",       icon: "🩺", group: "home-services" },
      { id: "hs-service-areas",    label: "Service Areas / Zones",     href: "/admin/home-services/service-areas",              icon: "📍", group: "home-services" },
      { id: "hs-job-deduction",    label: "Completed Job Deduction",   href: "/admin/home-services/completed-job-deduction",    icon: "✅", group: "home-services" },
      { id: "hs-settings",         label: "Home Services Settings",    href: "/admin/home-services/settings",                   icon: "⚙️", group: "home-services" },
    ],
  },
  {
    id: "catalog",
    label: "Catalog",
    items: [
      { id: "catalog",            label: "Services",          href: "/admin/catalog",              icon: "🗂️", group: "catalog" },
      { id: "categories",         label: "Categories",        href: "/admin/categories",           icon: "📦", group: "catalog" },
      { id: "service-options",    label: "Service Options",   href: "/admin/service-options",      icon: "🔧", group: "catalog" },
      { id: "issue-types",        label: "Issue Types",       href: "/admin/issue-types",          icon: "🐛", group: "catalog" },
      { id: "checklist-templates",label: "Checklists",        href: "/admin/checklists",           icon: "📋", group: "catalog" },
      { id: "workflow-templates",  label: "Workflows",        href: "/admin/workflow-templates",   icon: "🔀", group: "catalog" },
      { id: "service-setup",      label: "Service Setup",     href: "/admin/service-setup/brands", icon: "🛠️", group: "catalog" },
      { id: "customer-flow",      label: "Customer Flow",     href: "/admin/customer-flow",        icon: "🌊", group: "catalog" },
    ],
  },
  {
    id: "packages",
    label: "Packages & Plans",
    items: [
      { id: "packages", label: "Package & Plans", href: "/admin/packages", icon: "🎁", group: "packages" },
    ],
  },
  {
    id: "pricing",
    label: "Pricing",
    items: [
      { id: "pricing", label: "Pricing Rules", href: "/admin/pricing", icon: "💲", group: "pricing" },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      { id: "finance",            label: "Finance Hub",     href: "/admin/finance",             icon: "💰", group: "finance" },
      { id: "service-invoices",   label: "Invoices",        href: "/admin/service-invoices",    icon: "🧾", group: "finance" },
      { id: "provider-wallets",   label: "Wallets",         href: "/admin/provider-wallets",    icon: "👛", group: "finance" },
      { id: "commission-records", label: "Commissions",     href: "/admin/commission-records",  icon: "💹", group: "finance" },
      { id: "payments",           label: "Payments",        href: "/admin/payments",            icon: "💳", group: "finance" },
      { id: "financial-events",   label: "Financial Events",href: "/admin/financial-events",    icon: "📊", group: "finance" },
    ],
  },
  {
    id: "intelligence",
    label: "Intelligence",
    items: [
      { id: "intelligence", label: "AI Intelligence",  href: "/admin/intelligence",  icon: "🧠", group: "intelligence" },
      { id: "analytics",    label: "Analytics",        href: "/admin/analytics",     icon: "📈", group: "intelligence" },
      { id: "reports",      label: "Reports",          href: "/admin/reports",       icon: "📄", group: "intelligence" },
      { id: "exports",      label: "Export Jobs",      href: "/admin/exports",       icon: "📤", group: "intelligence" },
      { id: "ai",           label: "AI Config",        href: "/admin/ai/sessions",   icon: "🤖", group: "intelligence" },
      { id: "ai-chat",      label: "AI Chat",          href: "/admin/ai-chat",       icon: "💬", group: "intelligence" },
    ],
  },
  {
    id: "engagement",
    label: "Engagement",
    items: [
      { id: "marketing",     label: "Marketing",      href: "/admin/marketing",     icon: "📣", group: "engagement" },
      { id: "notifications", label: "Notifications",  href: "/admin/notifications", icon: "🔔", group: "engagement" },
      { id: "reviews",       label: "Reviews",        href: "/admin/reviews",       icon: "⭐", group: "engagement" },
      { id: "complaints",    label: "Complaints",     href: "/admin/complaints",    icon: "⚠️", group: "engagement" },
    ],
  },
  {
    id: "automation",
    label: "Automation",
    items: [
      { id: "automation", label: "Automation",     href: "/admin/automation/recommendation-rules", icon: "⚡", group: "automation" },
      { id: "engines",    label: "Engines",        href: "/admin/engines",        icon: "🔩", group: "automation" },
    ],
  },
  {
    id: "admin",
    label: "Admin",
    items: [
      { id: "security",    label: "Security",    href: "/admin/security",    icon: "🔒", group: "admin" },
      { id: "compliance",  label: "Compliance",  href: "/admin/compliance",  icon: "📜", group: "admin" },
      { id: "audit-logs",  label: "Audit Logs",  href: "/admin/audit-logs",  icon: "📝", group: "admin" },
      { id: "media",       label: "Media",       href: "/admin/media",       icon: "🖼️", group: "admin" },
      { id: "settings",    label: "Settings",    href: "/admin/settings",    icon: "⚙️", group: "admin" },
      { id: "profile",     label: "Profile",     href: "/admin/account",     icon: "👤", group: "admin" },
    ],
  },
];

/** Flat map of all nav items by id for quick lookup. */
export const ADMIN_NAV_BY_ID: Record<string, NavItem> = Object.fromEntries(
  ADMIN_NAV_GROUPS.flatMap(g => g.items).map(item => [item.id, item])
);

/**
 * Maps URL path segment → nav item id.
 * Replaces the inline `pathToActiveNav` map in layout.tsx.
 */
export const ADMIN_PATH_TO_NAV_ID: Record<string, string> = {
  dashboard:              "dashboard",
  tenants:                "tenants",
  users:                  "users",
  customers:              "customers",
  staff:                  "staff",
  bookings:               "bookings",
  operations:             "operations",
  "home-services":        "hs-bookings",
  "real-estate":          "real-estate",
  coaching:               "coaching",
  bookability:            "bookability",
  onboarding:             "onboarding",
  catalog:                "catalog",
  categories:             "categories",
  packages:               "packages",
  pricing:                "pricing",
  "service-options":      "service-options",
  "issue-types":          "issue-types",
  "checklist-templates":  "checklist-templates",
  "checklists":           "checklist-templates",
  "workflow-templates":   "workflow-templates",
  "service-setup":        "service-setup",
  "customer-flow":        "customer-flow",
  finance:                "finance",
  "service-invoices":     "service-invoices",
  "provider-wallets":     "provider-wallets",
  "commission-records":   "commission-records",
  payments:               "payments",
  "financial-events":     "financial-events",
  intelligence:           "intelligence",
  analytics:              "analytics",
  reports:                "analytics",
  exports:                "exports",
  ai:                     "ai",
  "ai-chat":              "ai-chat",
  marketing:              "marketing",
  notifications:          "notifications",
  "notification-templates": "notifications",
  "notification-outbox":    "notifications",
  "notification-events":    "notifications",
  reviews:                "reviews",
  "review-flags":         "reviews",
  "review-policies":      "reviews",
  "review-replies":       "reviews",
  "rating-summaries":     "reviews",
  complaints:             "reviews",
  "complaint-policies":   "reviews",
  "rework-requests":      "reviews",
  "refund-requests":      "reviews",
  automation:             "automation",
  engines:                "engines",
  security:               "security",
  compliance:             "compliance",
  "audit-logs":           "audit-logs",
  "media":                "media",
  settings:               "settings",
  profile:                "profile",
  account:                "profile",
  chat:                   "notifications",
  "dispatch":             "operations",
};

/** Resolve a pathname to a nav item id. */
const HOME_SERVICES_SUBPAGE_TO_NAV_ID: Record<string, string> = {
  "booking-drafts":          "hs-bookings",
  "service-jobs":            "hs-bookings",
  "service-catalog":         "hs-service-catalog",
  "pricing-rules":           "hs-pricing-rules",
  "price-experience":        "hs-price-experience",
  "provider-matching":       "hs-provider-matching",
  "matching-diagnostics":    "hs-matching-diagnostics",
  "service-areas":           "hs-service-areas",
  "completed-job-deduction": "hs-job-deduction",
  "settings":                "hs-settings",
};

export function resolveAdminNavId(pathname: string): string {
  const segs = pathname.split("/").filter(Boolean);
  const section = segs[1] ?? "dashboard";  // segs[0] = "admin"
  if (section === "home-services") {
    const sub = segs[2] ?? "";
    return HOME_SERVICES_SUBPAGE_TO_NAV_ID[sub] ?? "hs-bookings";
  }
  return ADMIN_PATH_TO_NAV_ID[section] ?? section;
}
