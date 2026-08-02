/**
 * Sprint 34K — Tenant Portal Page Registry.
 *
 * Maps routes to page metadata for breadcrumbs and page titles.
 */

export interface PageMeta {
  title: string;
  section: string;
  breadcrumbs: { label: string; href?: string }[];
  description?: string;
}

export const TENANT_PAGE_REGISTRY: Record<string, PageMeta> = {
  "/dashboard": {
    title: "Dashboard",
    section: "core",
    breadcrumbs: [{ label: "Dashboard" }],
  },
  "/profile": {
    title: "Profile",
    section: "core",
    breadcrumbs: [{ label: "Profile" }],
  },
  "/settings": {
    title: "Settings",
    section: "core",
    breadcrumbs: [{ label: "Settings" }],
  },
  "/jobs": {
    title: "Bookings & Jobs",
    section: "operations",
    breadcrumbs: [{ label: "Bookings & Jobs" }],
  },
  "/service-jobs": {
    title: "Service Jobs",
    section: "operations",
    breadcrumbs: [{ label: "Bookings & Jobs", href: "/jobs" }, { label: "Service Jobs" }],
  },
  "/appointments": {
    title: "Appointments",
    section: "operations",
    breadcrumbs: [{ label: "Appointments" }],
  },
  "/dispatch": {
    title: "Dispatch",
    section: "operations",
    breadcrumbs: [{ label: "Dispatch" }],
  },
  "/service-areas": {
    title: "Service Areas",
    section: "operations",
    breadcrumbs: [{ label: "Service Areas" }],
  },
  "/staff": {
    title: "Staff",
    section: "staff",
    breadcrumbs: [{ label: "Staff" }],
  },
  "/provider/offerings": {
    title: "Offerings",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Offerings" }],
  },
  "/provider/service-areas": {
    title: "Service Areas",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Service Areas" }],
  },
  "/provider/team-members": {
    title: "Team Members",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Team" }],
  },
  "/provider/availability": {
    title: "Availability",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Availability" }],
  },
  "/provider/marketing": {
    title: "Provider Marketing",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Marketing" }],
  },
  "/catalog": {
    title: "Catalog",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog" }],
  },
  "/inventory": {
    title: "Inventory",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog", href: "/catalog" }, { label: "Inventory" }],
  },
  "/documents": {
    title: "Documents",
    section: "catalog",
    breadcrumbs: [{ label: "Documents" }],
  },
  "/finance": {
    title: "Finance",
    section: "finance",
    breadcrumbs: [{ label: "Finance" }],
  },
  "/customers": {
    title: "Customers",
    section: "engagement",
    breadcrumbs: [{ label: "Customers" }],
  },
  "/reviews": {
    title: "Reviews",
    section: "engagement",
    breadcrumbs: [{ label: "Reviews" }],
  },
  "/marketing": {
    title: "Marketing",
    section: "engagement",
    breadcrumbs: [{ label: "Marketing" }],
  },
  "/notifications": {
    title: "Notifications",
    section: "engagement",
    breadcrumbs: [{ label: "Notifications" }],
  },
  "/chat": {
    title: "Chat",
    section: "engagement",
    breadcrumbs: [{ label: "Chat" }],
  },
  "/analytics": {
    title: "Analytics",
    section: "insights",
    breadcrumbs: [{ label: "Analytics" }],
  },
  "/reports": {
    title: "Reports",
    section: "insights",
    breadcrumbs: [{ label: "Reports" }],
  },
  "/insights": {
    title: "Insights",
    section: "insights",
    breadcrumbs: [{ label: "Insights" }],
  },
  "/onboarding-status": {
    title: "Onboarding Status",
    section: "provider",
    breadcrumbs: [{ label: "Onboarding Status" }],
  },
  "/media": {
    title: "Media",
    section: "catalog",
    breadcrumbs: [{ label: "Catalog", href: "/catalog" }, { label: "Media" }],
  },
};

export function resolveTenantPageMeta(pathname: string): PageMeta | null {
  if (TENANT_PAGE_REGISTRY[pathname]) {
    return TENANT_PAGE_REGISTRY[pathname];
  }
  const parts = pathname.split("/").filter(Boolean);
  for (let len = parts.length - 1; len >= 1; len--) {
    const candidate = "/" + parts.slice(0, len).join("/");
    if (TENANT_PAGE_REGISTRY[candidate]) {
      return TENANT_PAGE_REGISTRY[candidate];
    }
  }
  return null;
}
