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
  "/admin/tenants": {
    title: "Tenants",
    section: "core",
    breadcrumbs: [{ label: "Tenants" }],
    description: "Provider businesses, onboarding, credits, coverage, and operational health",
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
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Finance" },
    ],
  },
  "/admin/home-services/bookings-jobs": {
    title: "Bookings & Jobs",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Bookings & Jobs" },
    ],
  },
  "/admin/home-services/providers": {
    title: "Providers",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Providers" },
    ],
  },
  "/admin/home-services/complaints": {
    title: "Complaints",
    section: "operations",
    breadcrumbs: [
      { label: "Operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Complaints" },
    ],
  },
  "/admin/home-services/settings": {
    title: "Home Services Settings",
    section: "operations",
    breadcrumbs: [
      { label: "Operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Settings" },
    ],
  },
  "/admin/home-services/customers": {
    title: "Customers",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Customers" },
    ],
  },
  "/admin/home-services/dashboard": {
    title: "Dashboard",
    section: "operations",
    breadcrumbs: [
      { label: "Operations", href: "/admin/operations" },
      { label: "Home Services" },
      { label: "Dashboard" },
    ],
  },
  "/admin/catalog-workspace": {
    title: "Catalog Workspace",
    section: "operations",
    breadcrumbs: [{ label: "Catalog", href: "/admin/categories" }, { label: "Workspace" }],
  },
  "/admin/verticals": {
    title: "Verticals",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog" }, { label: "Verticals" }],
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
  "/admin/bookability/providers": {
    title: "Provider Bookability",
    section: "operations",
    breadcrumbs: [
      { label: "Operations" },
      { label: "Home Services", href: "/admin/home-services/dashboard" },
      { label: "Provider Bookability" },
    ],
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
  "/admin/marketing/home": {
    title: "Customer Home",
    section: "engagement",
    breadcrumbs: [
      { label: "Marketing", href: "/admin/marketing" },
      { label: "Customer Home" },
    ],
  },
  "/admin/notifications": {
    title: "Notifications",
    section: "engagement",
    breadcrumbs: [{ label: "Notifications" }],
  },
  "/admin/messaging-channels": {
    title: "Social Booking",
    section: "engagement",
    breadcrumbs: [{ label: "Social Booking" }],
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
  "/admin/trust-quality": {
    title: "Trust & Quality",
    section: "admin",
    breadcrumbs: [{ label: "Trust & Quality" }],
  },
  "/admin/topup-plans": {
    title: "Top-up Plans",
    section: "finance",
    breadcrumbs: [{ label: "Top-up Plans" }],
    description: "Credit and technician seats a Home Services provider buys to operate",
  },
  "/admin/legal": {
    title: "Legal Documents",
    section: "admin",
    breadcrumbs: [{ label: "Legal Documents" }],
    description: "Author and publish the Terms, Privacy Notice and related policies",
  },
  "/admin/audit-logs": {
    title: "Audit Logs",
    section: "admin",
    breadcrumbs: [{ label: "Audit Logs" }],
  },
  "/admin/roles": {
    title: "Roles",
    section: "admin",
    breadcrumbs: [{ label: "Access Control" }, { label: "Roles" }],
  },
  "/admin/permissions": {
    title: "Permissions",
    section: "admin",
    breadcrumbs: [{ label: "Access Control" }, { label: "Permissions" }],
  },
  "/admin/media": {
    title: "Media Library",
    section: "admin",
    breadcrumbs: [{ label: "Media Library" }],
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

const ROUTE_LABELS: Record<string, string> = {
  ai: "AI Configuration",
  "ai-chat": "AI Chat",
  "audit-logs": "Audit Logs",
  "bookings-jobs": "Bookings & Jobs",
  "bulk-runs": "Bulk Runs",
  "bulk-wizard": "Bulk Wizard",
  "catalog-workspace": "Catalog Workspace",
  "customer-credits": "Customer Credits",
  "customer-flow": "Customer Flow",
  "direct-payments": "Direct Payments",
  "financial-events": "Financial Events",
  "home-services": "Home Services",
  "knowledge-bases": "Knowledge Bases",
  "master-services": "Master Services",
  "notification-outbox": "Delivery Outbox",
  "notification-templates": "Notification Templates",
  "provider-wallets": "Provider Wallets",
  "service-area-requests": "Service Area Requests",
  "service-groups": "Service Groups",
  "service-invoices": "Service Invoices",
  "service-setup": "Service Setup",
  "tenant-assistant": "Tenant Assistant",
  "trust-quality": "Trust & Quality",
  "types-brands": "Types & Brands",
  "workflow-templates": "Workflow Templates",
};

const humanizeRoute = (segment: string) => ROUTE_LABELS[segment]
  ?? segment.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const isOpaqueId = (segment: string) => /^\d+$/.test(segment)
  || /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(segment)
  || segment.length > 28;
const detailTitle = (title: string) => title === "Categories"
  ? "Category details"
  : `${title.replace(/ies$/, "y").replace(/s$/, "")} details`;

function childBreadcrumbs(parent: PageMeta | null, baseParts: string[], remaining: string[]): PageMeta {
  const breadcrumbs = parent ? [...parent.breadcrumbs] : [];
  let lastTitle = parent?.title ?? "Admin";
  remaining.forEach((segment, index) => {
    const isLast = index === remaining.length - 1;
    const label = isOpaqueId(segment) ? detailTitle(lastTitle) : humanizeRoute(segment);
    lastTitle = label.replace(/ details$/, "");
    const candidate = "/" + [...baseParts, ...remaining.slice(0, index + 1)].join("/");
    breadcrumbs.push({
      label,
      href: !isLast && ADMIN_PAGE_REGISTRY[candidate] ? candidate : undefined,
    });
  });
  return { title: lastTitle, section: parent?.section ?? "admin", breadcrumbs };
}

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
      const parent = ADMIN_PAGE_REGISTRY[candidate];
      return childBreadcrumbs(parent, parts.slice(0, len), parts.slice(len));
    }
  }
  const routeParts = parts[0] === "admin" ? parts.slice(1) : parts;
  if (!routeParts.length) return null;
  return childBreadcrumbs(null, ["admin"], routeParts);
}
