/**
 * Sprint 34K — Super-Admin Page Registry.
 *
 * Maps routes to page metadata: title, breadcrumbs, section, description.
 * Used by the Breadcrumbs component and page title system.
 */

export interface PageMeta {
  title: string;
  section: string;
  breadcrumbs: { label: string; href?: string }[];
  description?: string;
}

/** Page metadata keyed by the route path (first two segments after leading slash). */
export const ADMIN_PAGE_REGISTRY: Record<string, PageMeta> = {
  "/admin/dashboard": {
    title: "Dashboard",
    section: "core",
    breadcrumbs: [{ label: "Dashboard" }],
    description: "Platform overview and key metrics",
  },
  "/admin/users": {
    title: "Users",
    section: "core",
    breadcrumbs: [{ label: "Users" }],
  },
  "/admin/customers": {
    title: "Customers",
    section: "core",
    breadcrumbs: [{ label: "Customers" }],
  },
  "/admin/staff": {
    title: "Staff",
    section: "core",
    breadcrumbs: [{ label: "Staff" }],
  },
  "/admin/operations": {
    title: "Operations",
    section: "operations",
    breadcrumbs: [{ label: "Operations" }],
  },
  "/admin/home-services": {
    title: "Home Services",
    section: "operations",
    breadcrumbs: [{ label: "Operations", href: "/admin/operations" }, { label: "Home Services" }],
  },
  "/admin/home-services/finance": {
    title: "Home Services Finance",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services" },
      { label: "Finance" },
    ],
  },
  "/admin/home-services/bookings-jobs": {
    title: "Bookings & Jobs",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services" },
      { label: "Bookings & Jobs" },
    ],
  },
  "/admin/home-services/providers": {
    title: "Providers",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services" },
      { label: "Providers" },
    ],
  },
  "/admin/home-services/customers": {
    title: "Customers",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services" },
      { label: "Customers" },
    ],
  },
  "/admin/home-services/dashboard": {
    title: "Dashboard",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services" },
      { label: "Dashboard" },
    ],
  },
  "/admin/catalog-workspace": {
    title: "Catalog Workspace",
    section: "operations",
    breadcrumbs: [{ label: "Catalog", href: "/admin/categories" }, { label: "Workspace" }],
  },
  "/admin/real-estate": {
    title: "Real Estate",
    section: "operations",
    breadcrumbs: [{ label: "Operations", href: "/admin/operations" }, { label: "Real Estate" }],
  },
  "/admin/coaching": {
    title: "Coaching",
    section: "operations",
    breadcrumbs: [{ label: "Operations", href: "/admin/operations" }, { label: "Coaching" }],
  },
  "/admin/bookability": {
    title: "Bookability",
    section: "operations",
    breadcrumbs: [{ label: "Bookability" }],
  },
  "/admin/onboarding": {
    title: "Onboarding",
    section: "operations",
    breadcrumbs: [{ label: "Onboarding" }],
  },
  "/admin/catalog": {
    title: "Service Catalog",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog" }],
    description: "Manage master services and categories",
  },
  "/admin/categories": {
    title: "Categories",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog", href: "/admin/catalog" }, { label: "Categories" }],
  },
  "/admin/packages": {
    title: "Packages",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog", href: "/admin/catalog" }, { label: "Packages" }],
  },
  "/admin/checklists": {
    title: "Checklist Library",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog", href: "/admin/catalog" }, { label: "Checklist Library" }],
  },
  "/admin/service-setup": {
    title: "Service Setup",
    section: "catalog",
    breadcrumbs: [{ label: "Service Setup" }],
    description: "Bulk service configuration templates",
  },
  "/admin/service-setup/bulk-wizard": {
    title: "Bulk Wizard",
    section: "catalog",
    breadcrumbs: [{ label: "Service Setup", href: "/admin/service-setup" }, { label: "Bulk Wizard" }],
  },
  "/admin/service-setup/bulk-runs": {
    title: "Bulk Runs",
    section: "catalog",
    breadcrumbs: [
      { label: "Service Setup", href: "/admin/service-setup" },
      { label: "Bulk Wizard", href: "/admin/service-setup/bulk-wizard" },
      { label: "Runs" },
    ],
  },
  "/admin/customer-flow": {
    title: "Customer Flow",
    section: "catalog",
    breadcrumbs: [{ label: "Customer Flow" }],
    description: "Manage customer booking flow configs",
  },
  "/admin/customer-flow/drafts": {
    title: "Booking Drafts",
    section: "catalog",
    breadcrumbs: [{ label: "Customer Flow", href: "/admin/customer-flow" }, { label: "Drafts" }],
  },
  "/admin/finance": {
    title: "Finance",
    section: "finance",
    breadcrumbs: [{ label: "Finance" }],
  },
  "/admin/service-invoices": {
    title: "Invoices",
    section: "finance",
    breadcrumbs: [{ label: "Finance", href: "/admin/finance" }, { label: "Invoices" }],
  },
  "/admin/commission-records": {
    title: "Commissions",
    section: "finance",
    breadcrumbs: [{ label: "Finance", href: "/admin/finance" }, { label: "Commissions" }],
  },
  "/admin/payments": {
    title: "Payments",
    section: "finance",
    breadcrumbs: [{ label: "Finance", href: "/admin/finance" }, { label: "Payments" }],
  },
  "/admin/financial-events": {
    title: "Financial Events",
    section: "finance",
    breadcrumbs: [{ label: "Finance", href: "/admin/finance" }, { label: "Financial Events" }],
  },
  "/admin/intelligence": {
    title: "AI Intelligence",
    section: "intelligence",
    breadcrumbs: [{ label: "Intelligence" }],
  },
  "/admin/analytics": {
    title: "Analytics",
    section: "intelligence",
    breadcrumbs: [{ label: "Analytics" }],
  },
  "/admin/reports": {
    title: "Reports",
    section: "intelligence",
    breadcrumbs: [{ label: "Reports" }],
  },
  "/admin/ai": {
    title: "AI Configuration",
    section: "intelligence",
    breadcrumbs: [{ label: "Intelligence", href: "/admin/intelligence" }, { label: "AI Config" }],
  },
  "/admin/ai-chat": {
    title: "AI Chat",
    section: "intelligence",
    breadcrumbs: [{ label: "Intelligence", href: "/admin/intelligence" }, { label: "AI Chat" }],
  },
  "/admin/marketing": {
    title: "Marketing",
    section: "engagement",
    breadcrumbs: [{ label: "Marketing" }],
  },
  "/admin/notifications": {
    title: "Notifications",
    section: "engagement",
    breadcrumbs: [{ label: "Notifications" }],
  },
  "/admin/reviews": {
    title: "Reviews",
    section: "engagement",
    breadcrumbs: [{ label: "Reviews" }],
  },
  "/admin/complaints": {
    title: "Complaints",
    section: "engagement",
    breadcrumbs: [{ label: "Complaints" }],
  },
  "/admin/automation": {
    title: "Automation",
    section: "automation",
    breadcrumbs: [{ label: "Automation" }],
  },
  "/admin/automation/recommendation-rules": {
    title: "Recommendation Rules",
    section: "automation",
    breadcrumbs: [{ label: "Automation", href: "/admin/automation" }, { label: "Recommendation Rules" }],
  },
  "/admin/automation/recommendation-results": {
    title: "Recommendation Results",
    section: "automation",
    breadcrumbs: [{ label: "Automation", href: "/admin/automation" }, { label: "Results" }],
  },
  "/admin/engines": {
    title: "Engine Management",
    section: "automation",
    breadcrumbs: [{ label: "Engines" }],
  },
  "/admin/security": {
    title: "Security",
    section: "admin",
    breadcrumbs: [{ label: "Security" }],
  },
  "/admin/compliance": {
    title: "Compliance",
    section: "admin",
    breadcrumbs: [{ label: "Compliance" }],
  },
  "/admin/audit-logs": {
    title: "Audit Logs",
    section: "admin",
    breadcrumbs: [{ label: "Audit Logs" }],
  },
  "/admin/settings": {
    title: "Settings",
    section: "admin",
    breadcrumbs: [{ label: "Settings" }],
  },
  "/admin/profile": {
    title: "Profile",
    section: "admin",
    breadcrumbs: [{ label: "Profile" }],
  },
};

/**
 * Resolve page metadata for a pathname.
 * Matches the longest registered prefix.
 */
export function resolvePageMeta(pathname: string): PageMeta | null {
  // Try exact match first
  if (ADMIN_PAGE_REGISTRY[pathname]) {
    return ADMIN_PAGE_REGISTRY[pathname];
  }
  // Try parent paths (strip last segment)
  const parts = pathname.split("/").filter(Boolean);
  for (let len = parts.length - 1; len >= 2; len--) {
    const candidate = "/" + parts.slice(0, len).join("/");
    if (ADMIN_PAGE_REGISTRY[candidate]) {
      return ADMIN_PAGE_REGISTRY[candidate];
    }
  }
  return null;
}
