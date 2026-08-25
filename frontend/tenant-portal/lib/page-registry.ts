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
  "/tenant/home-services/setup": {
    title: "Home Services Setup",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup" }],
  },
  "/tenant/home-services/setup/overview": {
    title: "Setup Overview",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Overview" }],
  },
  "/tenant/home-services/setup/business-profile": {
    title: "Business Profile",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Business Profile" }],
  },
  "/tenant/home-services/setup/documents": {
    title: "Verification Documents",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Documents" }],
  },
  "/tenant/home-services/setup/services-pricing": {
    title: "Services & Pricing",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Services & Pricing" }],
  },
  "/tenant/home-services/setup/coverage-availability": {
    title: "Coverage & Availability",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Coverage & Availability" }],
  },
  "/tenant/home-services/setup/staff": {
    title: "Staff & Technicians",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Staff & Technicians" }],
  },
  "/tenant/home-services/setup/finance": {
    title: "Finance Readiness",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Finance Readiness" }],
  },
  "/tenant/home-services/setup/review": {
    title: "Review & Submit",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Review & Submit" }],
  },
  "/onboarding/application-status": {
    title: "Application Status",
    section: "onboarding",
    breadcrumbs: [{ label: "Onboarding" }, { label: "Application Status" }],
  },
  "/onboarding/submitted-setup": {
    title: "Submitted Setup",
    section: "onboarding",
    breadcrumbs: [{ label: "Onboarding" }, { label: "Submitted Setup" }],
  },
  "/onboarding/activation-center": {
    title: "Activation Center",
    section: "onboarding",
    breadcrumbs: [{ label: "Onboarding" }, { label: "Activation Center" }],
  },
  "/onboarding/messages": {
    title: "Messages & Requests",
    section: "onboarding",
    breadcrumbs: [{ label: "Onboarding" }, { label: "Messages & Requests" }],
  },
  "/home-services/bookings-jobs": {
    title: "Bookings & Jobs",
    section: "operations",
    breadcrumbs: [{ label: "Operations" }, { label: "Bookings & Jobs" }],
  },
  "/home-services/dispatch": {
    title: "Assignment & Dispatch",
    section: "operations",
    breadcrumbs: [{ label: "Operations" }, { label: "Assignment & Dispatch" }],
  },
  "/home-services/services": {
    title: "Services & Pricing",
    section: "services",
    breadcrumbs: [{ label: "Services & Coverage" }, { label: "Services & Pricing" }],
  },
  "/home-services/coverage": {
    title: "Service Areas",
    section: "services",
    breadcrumbs: [{ label: "Services & Coverage" }, { label: "Service Areas" }],
  },
  "/home-services/team": {
    title: "Team Members",
    section: "team",
    breadcrumbs: [{ label: "Team" }, { label: "Team Members" }],
  },
  "/home-services/finance": {
    title: "Finance & Credits",
    section: "finance",
    breadcrumbs: [{ label: "Finance" }, { label: "Finance & Credits" }],
  },
  "/business/coverage-hours": {
    title: "Coverage & Hours",
    section: "business",
    breadcrumbs: [{ label: "Business" }, { label: "Coverage & Hours" }],
  },
  "/business/verification-documents": {
    title: "Documents",
    section: "business",
    breadcrumbs: [{ label: "Business" }, { label: "Documents" }],
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
