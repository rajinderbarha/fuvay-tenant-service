/**
 * DESIGN PHASE UX-03 — Tenant Portal information architecture.
 *
 * EXTENDS the existing `lib/nav-config.ts` (TENANT_NAV_GROUPS) rather than
 * replacing it — see design-foundation-compatibility-report.md. Not wired
 * into production layout.tsx by this phase (mirrors UX-02's precedent);
 * that swap is a product decision — see product-decisions-required.md.
 *
 * IMPORTANT: nav visibility (`canonicalRoles`/`readOnlyBehavior` below) is a
 * UX convenience only. It is NEVER an authorization boundary — the backend
 * enforces real access control (see app/core/permissions.py) independent of
 * whether a link is shown. See design-governance-rules.md.
 */
import type { NavGroup, NavItem } from "../nav-config";
import type { CanonicalTenantRole, ReadinessState } from "./types";

export interface Ux03NavItem extends NavItem {
  description: string;
  canonicalRoles: CanonicalTenantRole[];
  staffPermissionKey: string | null; // real permission_key gating this item, if any
  backendCapability: string;
  readiness: ReadinessState;
  readOnlyBehavior: "hidden" | "visible_disabled" | "visible_read_only_view";
  badge?: "new" | "attention" | "none";
  mobileBehavior: "full" | "collapsed_summary" | "hidden_on_mobile";
  emptyState?: string;
}

export interface Ux03NavGroup extends Omit<NavGroup, "items"> {
  description: string;
  items: Ux03NavItem[];
}

const ALL_ROLES: CanonicalTenantRole[] = ["tenant_owner", "staff", "technician"];
const OWNER_ONLY: CanonicalTenantRole[] = ["tenant_owner"];
const OWNER_AND_STAFF: CanonicalTenantRole[] = ["tenant_owner", "staff"];

export const UX03_NAV_GROUPS: Ux03NavGroup[] = [
  {
    id: "overview", label: "Overview", description: "Landing dashboard, pre- and post-approval.",
    items: [
      { id: "ux03-dashboard", label: "Dashboard", href: "/dashboard", group: "overview", description: "One configurable dashboard: pre-approval setup view or approved-business operations view.", canonicalRoles: ALL_ROLES, staffPermissionKey: null, backendCapability: "analytics/intelligence + admin_catalog/tenant_service", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "setup", label: "Setup and Profile", description: "First-time setup wizard, business profile, review state.",
    items: [
      { id: "ux03-setup-wizard", label: "Business Setup", href: "/tenant/setup", group: "setup", description: "First-time setup wizard with save/resume.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "admin_catalog/tenant_service onboarding flow", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "hidden", mobileBehavior: "full" },
      { id: "ux03-profile", label: "Business Profile", href: "/profile", group: "setup", description: "Profile sections + review-state banner.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: "settings:read", backendCapability: "admin_catalog/tenant_service", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "team", label: "Team", description: "Members, technicians, invitations, permissions.",
    items: [
      { id: "ux03-team-list", label: "Team Members", href: "/provider/staff", group: "team", description: "All staff + technicians, unified list.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: null, backendCapability: "auth/service staff management", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
      { id: "ux03-team-permissions", label: "Permission Editor", href: "/provider/staff/[id]/permissions", group: "team", description: "Grouped, searchable StaffPermission editor.", canonicalRoles: OWNER_ONLY, staffPermissionKey: "auth:permissions:manage", backendCapability: "auth/service _get_staff_permissions + apply_staff_permissions", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "hidden", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "services", label: "Services and Pricing", description: "Catalog, multi-service setup, pricing.",
    items: [
      { id: "ux03-catalog", label: "Service Catalog", href: "/provider/services", group: "services", description: "List + multi-service setup wizard.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: "settings:read", backendCapability: "catalog engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
      { id: "ux03-pricing", label: "Pricing", href: "/provider/pricing", group: "services", description: "Platform min/max always visible; below-minimum validation.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "catalog + admin_catalog pricing", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "areas", label: "Service Areas", description: "Coverage, zones, conflicts — frozen-slice authorization applies.",
    items: [
      { id: "ux03-service-areas", label: "Service Areas", href: "/provider/service-areas", group: "areas", description: "Coverage overview; mutation actions gated per geo-auth frozen-slice status.", canonicalRoles: OWNER_ONLY, staffPermissionKey: "tenant_service_area:update", backendCapability: "geo/service (partial authorization closure)", readiness: "PRODUCT_DECISION_REQUIRED", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "bookings", label: "Bookings", description: "Booking -> field_ops.Job pipeline only.",
    items: [
      { id: "ux03-bookings-list", label: "Bookings", href: "/bookings", group: "bookings", description: "List preserving field_ops.Job identity; cancel/reschedule unresolved.", canonicalRoles: ALL_ROLES, staffPermissionKey: "booking:bookings:read", backendCapability: "booking engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full", emptyState: "No bookings scheduled yet." },
    ],
  },
  {
    id: "jobs", label: "Jobs", description: "ServiceBooking -> ServiceJob pipeline only.",
    items: [
      { id: "ux03-jobs-list", label: "Jobs", href: "/service-jobs", group: "jobs", description: "List preserving ServiceJob identity.", canonicalRoles: ALL_ROLES, staffPermissionKey: "field_ops:jobs:read", backendCapability: "field_ops engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full", emptyState: "No jobs assigned yet." },
      { id: "ux03-dispatch", label: "Assignment / Dispatch", href: "/dispatch", group: "jobs", description: "Technician availability/workload/skills workspace.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: "field_ops:jobs:assign", backendCapability: "field_ops engine dispatch", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "hidden", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "customers", label: "Customers", description: "Customer list, protected PII.",
    items: [
      { id: "ux03-customers", label: "Customers", href: "/customers", group: "customers", description: "Masked contact info by default.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: null, backendCapability: "customer_reviews + booking engines", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
  {
    id: "quotes", label: "Quotes and Checklists", description: "Quote + checklist reusable patterns.",
    items: [
      { id: "ux03-quotes", label: "Quotes", href: "/service-jobs/[id]#quote", group: "quotes", description: "Quote section embedded in Job Detail.", canonicalRoles: ALL_ROLES, staffPermissionKey: "field_ops:quotes:manage", backendCapability: "field_ops engine", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "parts", label: "Parts and Inventory", description: "PartsRequest is ServiceJob-only.",
    items: [
      { id: "ux03-parts", label: "Parts Requests", href: "/service-jobs/[id]#parts", group: "parts", description: "Technician requests; provider-side approves/rejects/marks-installed only.", canonicalRoles: ALL_ROLES, staffPermissionKey: "inventory:items:write", backendCapability: "field_ops + inventory engines", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "finance", label: "Finance and Credits", description: "Package credit / commission / deposit — kept separate, no payout UI.",
    items: [
      { id: "ux03-finance-package", label: "Package & Credits", href: "/finance/package", group: "finance", description: "Credit balance, commission rate, cycle usage.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "finance_hub", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
      { id: "ux03-finance-history", label: "Finance History", href: "/finance/usage-credit-ledger", group: "finance", description: "Transaction table, filters, export presentation only.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "finance_hub ledger", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
      { id: "ux03-security-deposit", label: "Security Deposit", href: "/finance/security-deposit", group: "finance", description: "Separate from credits/package/job payment.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "finance_hub deposit", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "complaints", label: "Complaints and Support", description: "Provider proposal/response authority only.",
    items: [
      { id: "ux03-complaints", label: "Complaints", href: "/reviews", group: "complaints", description: "No invented dispute-resolution authority.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: null, backendCapability: "complaints engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "full" },
    ],
  },
  {
    id: "compliance", label: "Compliance", description: "Requirement/submission/status/history.",
    items: [
      { id: "ux03-compliance", label: "Compliance", href: "/provider/compliance", group: "compliance", description: "Document submission + review history.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "compliance engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "media", label: "Media", description: "Upload/replace/preview — never expose storage keys/signed URLs.",
    items: [
      { id: "ux03-media", label: "Media", href: "/media", group: "media", description: "Logo/gallery/job-photo/document management.", canonicalRoles: OWNER_AND_STAFF, staffPermissionKey: "field_ops:photos:create", backendCapability: "media engine (N01 integrity backlog open)", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "reports", label: "Reports", description: "Operational reporting, no invented metrics.",
    items: [
      { id: "ux03-reports", label: "Reports", href: "/reports", group: "reports", description: "Existing production route.", canonicalRoles: OWNER_ONLY, staffPermissionKey: "field_ops:reports:read", backendCapability: "analytics engine", readiness: "READ_ONLY_READY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "settings", label: "Settings", description: "Business settings patterns with save-bar/unsaved-change warning.",
    items: [
      { id: "ux03-settings", label: "Settings", href: "/settings", group: "settings", description: "Details/hours/booking prefs/notifications/branding/security/team defaults.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "varies per section", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
  {
    id: "audit", label: "Audit Activity", description: "Tenant-scoped only — never platform-wide events.",
    items: [
      { id: "ux03-audit", label: "Activity", href: "/activity", group: "audit", description: "Tenant-scoped audit/activity feed.", canonicalRoles: OWNER_ONLY, staffPermissionKey: null, backendCapability: "audit logging (partial coverage)", readiness: "MOCK_DESIGN_ONLY", readOnlyBehavior: "visible_read_only_view", mobileBehavior: "collapsed_summary" },
    ],
  },
];
