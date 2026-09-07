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
  "/appointments": {
    title: "Appointments",
    section: "operations",
    breadcrumbs: [{ label: "Appointments" }],
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
  "/provider/marketing": {
    title: "Provider Marketing",
    section: "provider",
    breadcrumbs: [{ label: "Business Profile", href: "/profile" }, { label: "Marketing" }],
  },
  "/inventory": {
    title: "Inventory",
    section: "services",
    breadcrumbs: [{ label: "Services & Coverage" }, { label: "Parts & Inventory" }],
  },
  "/documents": {
    title: "Documents",
    section: "catalog",
    breadcrumbs: [{ label: "Documents" }],
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
  "/provider/notifications": {
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
  "/tenant/home-services/setup/plan": {
    title: "Technician Seat Plan",
    section: "onboarding",
    breadcrumbs: [{ label: "Setup", href: "/tenant/home-services/setup/overview" }, { label: "Technician Seat Plan" }],
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
  "/home-services/availability": {
    title: "Availability & Capacity",
    section: "operations",
    breadcrumbs: [{ label: "Operations" }, { label: "Availability & Capacity" }],
  },
  "/home-services/services": {
    title: "Services & Pricing",
    section: "services",
    breadcrumbs: [{ label: "Services & Coverage" }, { label: "Services & Pricing" }],
  },
  "/home-services/team": {
    title: "Team Members",
    section: "team",
    breadcrumbs: [{ label: "Team" }, { label: "Team Members" }],
  },
  "/home-services/reviews": {
    title: "Reviews",
    section: "customers",
    breadcrumbs: [{ label: "Customers" }, { label: "Reviews" }],
  },
  "/home-services/complaints": {
    title: "Complaints",
    section: "customers",
    breadcrumbs: [{ label: "Customers" }, { label: "Complaints" }],
  },
  "/provider/refund-requests": {
    title: "Refunds & Warranty",
    section: "customers",
    breadcrumbs: [{ label: "Customers" }, { label: "Refunds & Warranty" }],
  },
  "/home-services/finance": {
    title: "Finance & Credits",
    section: "finance",
    breadcrumbs: [{ label: "Finance" }, { label: "Finance & Credits" }],
  },
  "/home-services/direct-payments": {
    title: "Direct Payments",
    section: "finance",
    breadcrumbs: [{ label: "Finance" }, { label: "Direct Payments" }],
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
  "/provider/compliance": {
    title: "Compliance",
    section: "business",
    breadcrumbs: [{ label: "Business" }, { label: "Compliance" }],
  },
  "/operations/exceptions": {
    title: "Operational Exceptions",
    section: "operations",
    breadcrumbs: [{ label: "Operations" }, { label: "Operational Exceptions" }],
  },
  "/activity": {
    title: "Activity",
    section: "more",
    breadcrumbs: [{ label: "More" }, { label: "Activity" }],
  },
  "/help-support": {
    title: "Help & Support",
    section: "more",
    breadcrumbs: [{ label: "More" }, { label: "Help & Support" }],
  },
  "/media": {
    title: "Media",
    section: "catalog",
    breadcrumbs: [{ label: "Services & Pricing", href: "/home-services/services" }, { label: "Media" }],
  },
};

const ROUTE_LABELS: Record<string, string> = {
  "bookings-jobs": "Bookings & Jobs",
  "coverage-hours": "Coverage & Hours",
  "direct-payments": "Direct Payments",
  "help-support": "Help & Support",
  "home-services": "Home Services",
  "refund-requests": "Refunds & Warranty",
  "rework-requests": "Rework Requests",
  "service-areas": "Service Areas",
  "service-invoices": "Service Invoices",
  "service-jobs": "Service Jobs",
  "team-members": "Team Members",
  "usage-credit-ledger": "Usage Credit Ledger",
  "verification-documents": "Verification Documents",
};

const humanizeRoute = (segment: string) => ROUTE_LABELS[segment]
  ?? segment.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const isOpaqueId = (segment: string) => /^\d+$/.test(segment)
  || /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(segment)
  || segment.length > 28;
const detailTitle = (title: string) => `${title.replace(/ies$/, "y").replace(/s$/, "")} details`;

function childBreadcrumbs(parent: PageMeta | null, baseParts: string[], remaining: string[]): PageMeta {
  const breadcrumbs = parent ? [...parent.breadcrumbs] : [];
  let lastTitle = parent?.title ?? "Workspace";
  remaining.forEach((segment, index) => {
    const isLast = index === remaining.length - 1;
    const label = isOpaqueId(segment) ? detailTitle(lastTitle) : humanizeRoute(segment);
    lastTitle = label.replace(/ details$/, "");
    const candidate = "/" + [...baseParts, ...remaining.slice(0, index + 1)].join("/");
    breadcrumbs.push({
      label,
      href: !isLast && TENANT_PAGE_REGISTRY[candidate] ? candidate : undefined,
    });
  });
  return { title: lastTitle, section: parent?.section ?? "workspace", breadcrumbs };
}

export function resolveTenantPageMeta(pathname: string): PageMeta | null {
  if (TENANT_PAGE_REGISTRY[pathname]) {
    return TENANT_PAGE_REGISTRY[pathname];
  }
  const parts = pathname.split("/").filter(Boolean);
  for (let len = parts.length - 1; len >= 1; len--) {
    const candidate = "/" + parts.slice(0, len).join("/");
    if (TENANT_PAGE_REGISTRY[candidate]) {
      const parent = TENANT_PAGE_REGISTRY[candidate];
      return childBreadcrumbs(parent, parts.slice(0, len), parts.slice(len));
    }
  }
  if (!parts.length) return null;
  return childBreadcrumbs(null, [], parts);
}
