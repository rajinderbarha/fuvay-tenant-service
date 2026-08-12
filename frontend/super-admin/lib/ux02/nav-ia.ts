/**
 * DESIGN PHASE UX-02 — Super Admin information architecture.
 *
 * This EXTENDS the existing `lib/nav-config.ts` (ADMIN_NAV_GROUPS) rather
 * than replacing it — see docs/design/ux-02-super-admin/
 * ux01-source-compatibility-report.md for why nav-config.ts was judged
 * reusable-with-extension. UX02_NAV_GROUPS is a redesigned grouping
 * proposal layered on top of the same NavItem/NavGroup shape; it is not
 * wired into production layout.tsx by this phase (that swap is a product
 * decision — see product-decisions-required.md).
 *
 * IMPORTANT: nav visibility (`permission` field below) is a UX convenience
 * only. It is NEVER an authorization boundary — the backend enforces real
 * access control independent of whether a link is shown. See
 * design-governance-rules.md.
 */
import type { NavGroup, NavItem } from "../nav-config";
import type { CanonicalAdminRole, ReadinessState } from "./types";

export interface Ux02NavItem extends NavItem {
  description: string;
  canonicalRoles: CanonicalAdminRole[];
  backendCapability: string; // free-text pointer to the engine/capability, not a contract guarantee
  readiness: ReadinessState;
  readOnlyBehavior: "hidden" | "visible_disabled" | "visible_read_only_view";
  badge?: "new" | "attention" | "none";
  mobileBehavior: "full" | "collapsed_summary" | "hidden_on_mobile";
}

export interface Ux02NavGroup extends Omit<NavGroup, "items"> {
  description: string;
  items: Ux02NavItem[];
}

const ALL_ROLES: CanonicalAdminRole[] = ["super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"];

export const UX02_NAV_GROUPS: Ux02NavGroup[] = [
  {
    id: "overview", label: "Overview", description: "Cross-role landing surfaces.",
    items: [
      { id: "ux02-dashboard", label: "Dashboard", href: "/admin/dashboard", group: "overview", description: "Role-configured platform snapshot, action center, activity.", canonicalRoles: ALL_ROLES, backendCapability: "analytics/intelligence + per-domain dashboards", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
      { id: "ux02-search", label: "Global Search", href: "#", group: "overview", description: "Command palette across tenants, cases, audit entries.", canonicalRoles: ALL_ROLES, backendCapability: "none yet (no unified search endpoint)", readiness: "API_CONTRACT_REQUIRED", readOnlyBehavior: "visible_disabled", mobileBehavior: "hidden_on_mobile" },
    ],
  },
  {
    id: "tenants", label: "Tenants", description: "Tenant lifecycle, 360 view, onboarding.",
    items: [
      { id: "ux02-tenant-list", label: "Tenant List", href: "/admin/tenants", group: "tenants", description: "Enterprise list of all tenants with filters/bulk actions.", canonicalRoles: ["super_admin", "admin_operations", "admin_readonly"], backendCapability: "admin_catalog/tenant_service", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
      { id: "ux02-tenant-360", label: "Tenant 360", href: "/admin/tenants/[id]", group: "tenants", description: "Full tenant detail across 15 sections.", canonicalRoles: ["super_admin", "admin_operations", "admin_readonly"], backendCapability: "admin_catalog/tenant_service + several engines", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
      { id: "ux02-verification", label: "Verification Review", href: "/admin/home-services/providers?tab=onboarding", group: "tenants", description: "Applicant checklist, documents, approve/reject.", canonicalRoles: ["super_admin", "admin_operations"], backendCapability: "onboarding engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "hidden", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "operations", label: "Operations", description: "Bookings, dispatch, field ops, real estate, coaching.",
    items: [
      { id: "ux02-ops-bookings", label: "Bookings", href: "/admin/bookings", group: "operations", description: "Cross-vertical bookings.", canonicalRoles: ["super_admin", "admin_operations", "admin_readonly"], backendCapability: "booking engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
  {
    id: "catalog", label: "Catalog & Serviceability", description: "Services, categories, pricing, zones.",
    items: [
      { id: "ux02-catalog", label: "Catalog", href: "/admin/catalog", group: "catalog", description: "Service catalog administration.", canonicalRoles: ["super_admin", "admin_operations", "admin_readonly"], backendCapability: "catalog engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
  {
    id: "commerce", label: "Commerce & Finance", description: "Packages, credits, commission, invoices — never job payments or payouts.",
    items: [
      { id: "ux02-finance", label: "Finance Summary", href: "/admin/finance", group: "commerce", description: "Package credit / commission / deposit presentation only.", canonicalRoles: ["super_admin", "admin_finance", "admin_readonly"], backendCapability: "finance_hub + invoice_payment", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "trust", label: "Trust & Compliance", description: "Complaints, disputes, compliance cases.",
    items: [
      { id: "ux02-compliance-list", label: "Compliance Cases", href: "/admin/compliance", group: "trust", description: "Case list with severity/category filters.", canonicalRoles: ["super_admin", "admin_operations", "admin_security", "admin_readonly"], backendCapability: "compliance/enterprise_service", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
      { id: "ux02-compliance-detail", label: "Compliance Case Detail", href: "/admin/compliance/[id]", group: "trust", description: "Case detail with resolution workflow.", canonicalRoles: ["super_admin", "admin_operations", "admin_security"], backendCapability: "compliance/enterprise_service", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "security", label: "Security", description: "Auth events, observations, access reviews.",
    items: [
      { id: "ux02-security-list", label: "Security Observations", href: "/admin/security", group: "security", description: "Careful status language, never overstated.", canonicalRoles: ["super_admin", "admin_security", "admin_readonly"], backendCapability: "security/audit engines (partial)", readiness: "SECURITY_CONTRACT_PENDING", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
  {
    id: "platform", label: "Platform Configuration", description: "Tenant-independent platform settings.",
    items: [
      { id: "ux02-platform-settings", label: "Platform Settings", href: "/admin/settings", group: "platform", description: "Section cards, change history, validation.", canonicalRoles: ["super_admin"], backendCapability: "varies per section", readiness: "PRODUCT_DECISION_REQUIRED", readOnlyBehavior: "visible_disabled", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "audit", label: "Audit & Monitoring", description: "Audit explorer, engine health, activity feed.",
    items: [
      { id: "ux02-audit-explorer", label: "Audit Explorer", href: "/admin/audit-logs", group: "audit", description: "Full audit trail with redacted JSON viewer.", canonicalRoles: ["super_admin", "admin_security", "admin_readonly"], backendCapability: "audit logging (partial coverage)", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "support", label: "Support", description: "Refunds, rework, review flags, escalations.",
    items: [
      { id: "ux02-support", label: "Refund Requests", href: "/admin/refund-requests", group: "support", description: "Existing production route.", canonicalRoles: ["super_admin", "admin_operations", "admin_finance"], backendCapability: "complaints/refund_service", readiness: "PRODUCTION_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
];
