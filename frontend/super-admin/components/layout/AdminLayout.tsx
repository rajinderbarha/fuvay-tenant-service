"use client";
import React, { useState, useEffect, useCallback, createContext, useContext } from "react";

// Prevents double-rendering when a page already wraps itself with AdminLayout
// AND the route-level layout also renders AdminLayout.
const AdminShellCtx = createContext(false);

// FINAL-L5-04: lets a page (e.g. Verticals/Categories) tell the already-mounted
// sidebar to re-fetch its effective-menu after a mutation, instead of the
// sidebar only ever fetching once on mount. No query-cache library exists in
// this codebase (see FINAL-L5-03's Query/Cache Standard) so this is a plain
// callback-context, matching the existing refetch-on-demand pattern used
// everywhere else in the app.
const AdminMenuRefreshCtx = createContext<() => void>(() => {});
/** Call after any mutation that can change which verticals/modules/categories
 * are enabled, so the sidebar reflects it without a full page reload. */
export function useAdminMenuRefresh(): () => void {
  return useContext(AdminMenuRefreshCtx);
}
import {
  LayoutDashboard, Building2, Inbox, Settings2, Banknote,
  Shield, ClipboardCheck, Brain, Users, Star, Bell,
  Settings, Sun, Moon, ChevronLeft, ChevronRight,
  Search, Zap, LogOut, Tag, CalendarDays, UserCheck, Wrench, LayoutGrid, Cpu, Layers, FolderTree,
  Megaphone, Package, ScrollText, ListChecks, BarChart3, MapPin,
  HelpCircle, Sliders, GitBranch, Image, AlertOctagon, Globe,
  FlaskConical, PercentSquare, FileText as FileTextIcon,
} from "lucide-react";
import { verticalCatalogApi, type EffectiveMenu } from "../../lib/api";
import { useTheme } from "../../hooks/useTheme";
import { useTour } from "../../hooks/useTour";
import { Toaster, type ToastItem } from "../shared/ui";
import { TourGuide } from "../tour/TourGuide";
import { DefaultAvatar } from "../shared/ProfilePhotoUploader";
import { Breadcrumbs } from "./Breadcrumbs";
import { authApi, sprint27AdminApi } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { SUPER_ADMIN_ONLY } from "../../lib/permission-catalog";

// FINAL-L5-05M: requiredPermission is the one source of nav-visibility
// gating alongside isNavItemVisible's module/category gating below. A
// real backend permission key filters the item via usePermissions().has();
// SUPER_ADMIN_ONLY marks items whose backing route is still gated by the
// coarse require_super_admin check (not yet converted — see
// FINAL_L5_05L_ADMIN_ROLE_RUNTIME.md), matching real backend behavior
// rather than inventing a permission the backend doesn't enforce.
type NavItem = {
  id: string; href: string; label: string; icon: React.ReactNode; badge?: number | null;
  requiredPermission: string;
};
type NavGroup = { label: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { id: "dashboard", href: "/admin/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16}/>, requiredPermission: "" },
    ],
  },
  {
    // Provider lifecycle: discover → request → verify → subscribe
    label: "Providers",
    items: [
      { id: "tenants",              href: "/admin/tenants",              label: "All Providers",    icon: <Building2 size={16}/>,  requiredPermission: "tenant:read" },
      { id: "onboarding",           href: "/admin/tenants/onboarding",   label: "New Requests",     icon: <Inbox size={16}/>,      requiredPermission: SUPER_ADMIN_ONLY },
      { id: "onboarding-providers", href: "/admin/onboarding/providers", label: "Verify & Approve", icon: <ListChecks size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "packages",             href: "/admin/packages",             label: "Packages",         icon: <Package size={16}/>,    requiredPermission: SUPER_ADMIN_ONLY },
      { id: "trust-quality",        href: "/admin/trust-quality",        label: "Trust & Quality",  icon: <Star size={16}/>,       requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    // Day-to-day operational monitoring
    label: "Operations",
    items: [
      { id: "bookings",   href: "/admin/bookings",   label: "Bookings",  icon: <CalendarDays size={16}/>, requiredPermission: SUPER_ADMIN_ONLY               },
      { id: "operations", href: "/admin/home-services/service-jobs", label: "Jobs", icon: <Wrench size={16}/>, badge: null, requiredPermission: "admin:jobs:read" },
      { id: "customers",  href: "/admin/customers",  label: "Customers", icon: <UserCheck size={16}/>,    requiredPermission: SUPER_ADMIN_ONLY                },
      { id: "staff",      href: "/admin/staff",      label: "Staff",     icon: <Users size={16}/>,        requiredPermission: "staff:read"                    },
      { id: "reviews",    href: "/admin/reviews",    label: "Reviews",    icon: <Star size={16}/>,        requiredPermission: SUPER_ADMIN_ONLY                },
      { id: "complaints", href: "/admin/complaints", label: "Complaints", icon: <AlertOctagon size={16}/>, requiredPermission: SUPER_ADMIN_ONLY               },
      { id: "complaint-policies", href: "/admin/complaint-policies", label: "Complaint Policies", icon: <AlertOctagon size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    // Marketplace verticals management. Brands/Brand Requests are NOT global —
    // they live inside each vertical's catalog section (e.g. Home Services →
    // Types & Brands) to avoid the same route appearing twice in the sidebar.
    label: "Catalog",
    items: [
      { id: "verticals",       href: "/admin/verticals",       label: "Verticals",      icon: <Globe size={16}/>,  requiredPermission: SUPER_ADMIN_ONLY },
      { id: "categories",      href: "/admin/categories",      label: "Categories",     icon: <Layers size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    // Multi-vertical pricing infrastructure only — genuinely vertical-agnostic
    // (tiers/city-zip mapping/provider overrides apply across all verticals).
    // Pricing Rules itself moved to the Home Services group below since, in
    // practice, every active pricing rule today is Home Services scoped —
    // see HOME_SERVICES_MENU_ORGANIZATION_REPORT.md.
    label: "Pricing & Rules",
    items: [
      { id: "pricing-tiers",       href: "/admin/pricing-tiers",              label: "Pricing Tiers",    icon: <LayoutGrid size={16}/>,     requiredPermission: SUPER_ADMIN_ONLY },
      { id: "location-mapping",    href: "/admin/location-mapping",           label: "City/Zip Mapping", icon: <MapPin size={16}/>,         requiredPermission: SUPER_ADMIN_ONLY },
      { id: "provider-overrides",  href: "/admin/pricing/provider-overrides", label: "Provider Pricing Overrides", icon: <PercentSquare size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "category-commission", href: "/admin/pricing/commission",          label: "Category Rates", icon: <PercentSquare size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    // All Home-Services-specific screens live here only — never duplicated
    // into a common/global menu group. Home Services only (see
    // matching_engine.assert_home_services_vertical / get_home_services_category_id).
    label: "Home Services",
    items: [
      { id: "hs-service-catalog", href: "/admin/home-services/service-catalog", label: "Service Catalog", icon: <ListChecks size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-pricing-rules", href: "/admin/home-services/pricing-rules", label: "Pricing Rules", icon: <Sliders size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-price-experience", href: "/admin/home-services/price-experience", label: "Customer Price Experience", icon: <FlaskConical size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-provider-matching", href: "/admin/home-services/provider-matching", label: "Provider Matching", icon: <Zap size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-matching-diagnostics", href: "/admin/home-services/matching-diagnostics", label: "Matching Diagnostics", icon: <Wrench size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-service-areas", href: "/admin/home-services/service-areas", label: "Service Areas / Zones", icon: <MapPin size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-completed-job-deduction", href: "/admin/home-services/completed-job-deduction", label: "Completed Job Deduction", icon: <PercentSquare size={16}/>, requiredPermission: "finance.completed_job_deduction_rules.read" },
      { id: "hs-settings", href: "/admin/home-services/settings", label: "Home Services Settings", icon: <Settings size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      // Migrated in from the dynamic per-vertical Catalog sub-menu
      // (VerticalCatalogSection) — home_services is now excluded from that
      // loop below to stop the sidebar showing two separate "Home Services"
      // sections. These are the vertical's real, backend-enabled catalog
      // modules (from GET /v1/admin/catalog/navigation/effective-menu);
      // "categories" is intentionally NOT migrated here since it already
      // exists as the Catalog group's own "Categories" item (same /admin/categories route).
      { id: "hs-service-groups", href: "/admin/service-groups", label: "Service Groups", icon: <Layers size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-master-services", href: "/admin/master-services", label: "Master Services", icon: <ListChecks size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-types-brands", href: "/admin/types-brands", label: "Types & Brands", icon: <Tag size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-service-options", href: "/admin/service-options", label: "Service Options", icon: <Sliders size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-issue-types", href: "/admin/issue-types", label: "Issue Types", icon: <AlertOctagon size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-checklist-templates", href: "/admin/checklists", label: "Checklist Templates", icon: <ListChecks size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "hs-service-setup", href: "/admin/service-setup", label: "Service Setup", icon: <Settings size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      // Phase 2A Slice 2 nav reconciliation: page existed and was fully
      // built (adminBookabilityApi-backed) but had zero sidebar entry —
      // confirmed orphaned in the Phase 1 frontend audit and still true.
      // Grouped here (not a new top-level section) since it's Home
      // Services matching/bookability diagnostics, same as the two items
      // above it.
      { id: "bookability", href: "/admin/bookability/providers", label: "Provider Bookability", icon: <Zap size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    // Finance Hub: overview → deposits → top-ups → warranty claims → payouts
    label: "Finance",
    items: [
      { id: "finance",          href: "/admin/finance",          label: "Finance Hub",    icon: <Banknote size={16}/>,      requiredPermission: "finance:hub:read" },
      { id: "finance-usage-credits", href: "/admin/finance/usage-credits", label: "Usage Credits", icon: <Banknote size={16}/>, requiredPermission: "finance.usage_credits.read" },
      { id: "finance-deposits", href: "/admin/finance/deposits",  label: "Security Deposits", icon: <Shield size={16}/>,     requiredPermission: "finance:deposits:read" },
      { id: "finance-topups",   href: "/admin/finance/topups",    label: "Credit Top-ups",  icon: <Tag size={16}/>,          requiredPermission: "finance:topups:read" },
      { id: "finance-claims",   href: "/admin/finance/claims",    label: "Warranty Claims", icon: <AlertOctagon size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "finance-payouts",  href: "/admin/finance/payouts",   label: "Payouts",         icon: <ScrollText size={16}/>,   requiredPermission: SUPER_ADMIN_ONLY },
      // Phase 2A Slice 2 nav reconciliation: these 5 pages existed and were
      // fully built but had zero sidebar entry (confirmed orphaned in the
      // Phase 1 frontend audit, still true in current source). Phase 1A's
      // final-page-disposition-matrix.csv calls for these to eventually
      // become DETAIL_TABs of one consolidated Finance Hub workspace —
      // that tab-consolidation is explicitly out of scope for this slice
      // ("no broad page consolidation"), so they are restored here as
      // plain sidebar entries under Finance (their approved parent group)
      // rather than left unreachable. True tab consolidation remains
      // deferred — see deferred-items.md.
      { id: "finance-service-invoices",   href: "/admin/service-invoices",   label: "Service Invoices",   icon: <FileTextIcon size={16}/>, requiredPermission: "finance:hub:read" },
      { id: "finance-provider-wallets",   href: "/admin/provider-wallets",   label: "Provider Wallets",   icon: <Banknote size={16}/>,     requiredPermission: "finance:hub:read" },
      { id: "finance-commission-records", href: "/admin/commission-records", label: "Commission Records", icon: <PercentSquare size={16}/>, requiredPermission: "finance:hub:read" },
      { id: "finance-payments",           href: "/admin/payments",           label: "Payments",           icon: <Tag size={16}/>,          requiredPermission: "finance:hub:read" },
      { id: "finance-financial-events",   href: "/admin/financial-events",   label: "Financial Events",   icon: <ScrollText size={16}/>,   requiredPermission: "finance:hub:read" },
      { id: "compliance",       href: "/admin/compliance",        label: "Compliance",      icon: <ClipboardCheck size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    label: "Marketing & Growth",
    items: [
      { id: "marketing",     href: "/admin/marketing",     label: "Campaigns",       icon: <Megaphone size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "notifications", href: "/admin/notifications", label: "Notifications",   icon: <Bell size={16}/>,      requiredPermission: SUPER_ADMIN_ONLY },
      { id: "notification-settings", href: "/admin/notifications/settings", label: "Notification Settings", icon: <Bell size={16}/>, requiredPermission: SUPER_ADMIN_ONLY },
      { id: "analytics",     href: "/admin/analytics",     label: "Analytics",       icon: <BarChart3 size={16}/>, requiredPermission: "analytics:dashboard:read" },
      { id: "reports",       href: "/admin/reports",       label: "Reports",         icon: <ScrollText size={16}/>, requiredPermission: "analytics:dashboard:read" },
      { id: "intelligence",  href: "/admin/intelligence",  label: "AI Intelligence", icon: <Brain size={16}/>,     requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
  {
    label: "Platform",
    items: [
      { id: "engines",            href: "/admin/engines",            label: "Engines",    icon: <Cpu size={16}/>,        requiredPermission: SUPER_ADMIN_ONLY },
      { id: "security",           href: "/admin/security",           label: "Security",   icon: <Shield size={16}/>,     requiredPermission: "security:read" },
      { id: "workflow-templates", href: "/admin/workflow-templates", label: "Workflows",  icon: <GitBranch size={16}/>,  requiredPermission: SUPER_ADMIN_ONLY },
      { id: "audit-logs",         href: "/admin/audit-logs",        label: "Audit Logs", icon: <ScrollText size={16}/>, requiredPermission: "auth:audit:read" },
      { id: "users",              href: "/admin/users",              label: "Users",      icon: <Users size={16}/>,      requiredPermission: "auth:users:read" },
      { id: "roles",              href: "/admin/users/roles",        label: "Roles",       icon: <Shield size={16}/>,    requiredPermission: "platform:roles:read" },
      { id: "permissions",        href: "/admin/users/permissions",  label: "Permissions", icon: <ClipboardCheck size={16}/>, requiredPermission: "platform:permissions:read" },
      { id: "media",              href: "/admin/media",              label: "Media",      icon: <Image size={16}/>,      requiredPermission: SUPER_ADMIN_ONLY },
      { id: "settings",           href: "/admin/settings",           label: "Settings",   icon: <Settings size={16}/>,   requiredPermission: SUPER_ADMIN_ONLY },
    ],
  },
];

// Flattened (id, href) list derived from the actual rendered sidebar (NAV_GROUPS),
// used by app/admin/layout.tsx to compute the active nav id via longest-href-prefix
// matching. This is the single source of truth for "what's really in the sidebar" —
// see ADMIN_TENANT_E2E_02_ADMIN_SIDEBAR_ACTIVE_STATE_REPORT.md for why a second,
// hand-maintained section-name map (lib/nav-config.ts) drifted out of sync and
// failed to highlight nested sub-routes correctly.
export const FLAT_NAV_HREFS: { id: string; href: string }[] =
  NAV_GROUPS.flatMap(g => g.items.map(item => ({ id: item.id, href: item.href })));

/**
 * Resolve a pathname to the nav item id whose href is the longest matching
 * prefix (exact segment boundary — "/admin/catalog" does not match
 * "/admin/catalog-module"). Falls back to the first path segment under /admin
 * if nothing matches, so unknown/new routes still degrade gracefully instead
 * of highlighting the wrong parent item.
 */
export function resolveActiveNavId(pathname: string): string {
  let best: { id: string; href: string } | null = null;
  for (const entry of FLAT_NAV_HREFS) {
    if (pathname === entry.href || pathname.startsWith(entry.href + "/")) {
      if (!best || entry.href.length > best.href.length) best = entry;
    }
  }
  if (best) return best.id;
  const segs = pathname.split("/").filter(Boolean);
  return segs[1] ?? "dashboard";
}

// FINAL-L5-05N — Part 3 route-permission registry: every nav item's
// requiredPermission, keyed by id. Detail/tab/wizard/create/edit routes
// that don't have their own NAV_GROUPS entry inherit their nearest
// (longest-prefix-matched) parent's permission via resolveActiveNavId,
// giving every reachable /admin/* route real permission coverage without
// a second, hand-maintained route table.
const NAV_ITEM_PERMISSIONS: Record<string, string> = Object.fromEntries(
  NAV_GROUPS.flatMap(g => g.items.map(item => [item.id, item.requiredPermission])),
);

// Self-service routes every authenticated admin role may reach regardless
// of their permission bundle (own profile/account/sessions) -- not a
// second permission registry, just the same "" (visible-to-all) sentinel
// Dashboard already uses, applied to a short, explicit allowlist of ids
// that resolveActiveNavId can produce for routes with no NAV_GROUPS entry.
const SELF_SERVICE_ROUTE_IDS = new Set(["profile", "account", "login", "change-password-required"]);

/** Used by app/admin/layout.tsx's root-level RequirePermission guard --
 * the one enforcement point covering every /admin/* route, current and
 * future, via nav-item inheritance rather than per-page wrapping. */
export function getRequiredPermissionForRoute(pathname: string): string {
  const id = resolveActiveNavId(pathname);
  if (id in NAV_ITEM_PERMISSIONS) return NAV_ITEM_PERMISSIONS[id];
  if (SELF_SERVICE_ROUTE_IDS.has(id)) return "";
  // Unknown id (no NAV_GROUPS entry, not a recognized self-service route):
  // fail closed rather than silently default to unrestricted (rule 18).
  return SUPER_ADMIN_ONLY;
}

// Nav items that are Home-Services-specific or otherwise vertical-gated, rather than
// global admin concepts — hidden when the backing vertical/operation is disabled so the
// sidebar doesn't show irrelevant modules for Coaching/Real Estate/Restaurant/Product tenants.
// Source of truth is the backend effective-menu resolver (operation_visibility / enabled_vertical_keys);
// while the menu is still loading (effectiveMenu === null) items are shown to avoid flicker/false-hides.
function isNavItemVisible(itemId: string, effectiveMenu: EffectiveMenu | null): boolean {
  if (!effectiveMenu) return true;
  switch (itemId) {
    case "operations": // "Jobs" — field-ops style verticals only
      return effectiveMenu.operation_visibility.jobs_field_ops;
    case "finance-deposits": // Security Deposits — Home Services usage-credit model only
      return effectiveMenu.operation_visibility.security_deposit;
    case "finance-topups": // Credit Top-ups — Home Services usage-credit model only
      return effectiveMenu.operation_visibility.usage_credits;
    default:
      return true;
  }
}

// FINAL-L5-05M: permission gating, orthogonal to the module/category gating
// above. `perms === null` means the effective-permission fetch has not
// resolved yet — items are hidden (fail closed), not shown, to avoid
// flashing unauthorized content before the real server payload arrives.
function isNavItemPermitted(
  item: { requiredPermission: string },
  perms: string[] | null,
  role: string | null,
): boolean {
  if (item.requiredPermission === "") return true; // Dashboard — visible to any authenticated admin role
  if (perms === null) return false; // still loading — fail closed
  if (item.requiredPermission === SUPER_ADMIN_ONLY) return role === "super_admin";
  return perms.includes("*") || perms.includes(item.requiredPermission);
}

export function AdminLayout({ children, activeNav }: { children: React.ReactNode; activeNav?: string }) {
  const alreadyMounted = useContext(AdminShellCtx);
  // If already inside an AdminLayout (route-level wraps page-level), skip shell render.
  if (alreadyMounted) return <AdminShellCtx.Provider value={true}>{children}</AdminShellCtx.Provider>;

  return <AdminShellInner activeNav={activeNav}>{children}</AdminShellInner>;
}

function AdminShellInner({ children, activeNav }: { children: React.ReactNode; activeNav?: string }) {
  const { theme, toggle } = useTheme();
  const tour = useTour();
  const [collapsed, setCollapsed] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [effectiveMenu, setEffectiveMenu] = useState<EffectiveMenu | null>(null);
  const { permissions: effectivePermissions, role: effectiveRole } = usePermissions();

  const loadEffectiveMenu = useCallback(() => {
    const token = typeof window !== "undefined" && localStorage.getItem("serviceos_admin_token");
    if (!token) return;
    verticalCatalogApi.getEffectiveMenu()
      .then(r => setEffectiveMenu(r))
      .catch(() => {/* non-critical — sidebar degrades gracefully */});
  }, []);

  useEffect(() => { loadEffectiveMenu(); }, [loadEffectiveMenu]);

  useEffect(() => {
    const token = localStorage.getItem("serviceos_admin_token");
    if (!token && typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const addToast = (t: Omit<ToastItem, "id">) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { ...t, id }]);
    setTimeout(() => setToasts(prev => prev.filter(x => x.id !== id)), 4000);
  };

  async function handleLogout() {
    try { await authApi.logout(); } catch { /* best effort */ }
    localStorage.removeItem("serviceos_admin_token");
    window.location.href = "/login";
  }

  const w = collapsed ? 68 : 248;

  return (
    <AdminShellCtx.Provider value={true}>
    <AdminMenuRefreshCtx.Provider value={loadEffectiveMenu}>
    <div style={{ display: "flex", height: "100vh", background: "var(--bg-soft, var(--bg))", overflow: "hidden" }}>

      {/* FINAL-L5-05AC: skip-to-content -- first focusable element in the
          shell, visually hidden until keyboard-focused. */}
      <a
        href="#admin-main-content"
        style={{
          position: "absolute", left: -9999, top: 0, zIndex: 1000,
          padding: "10px 16px", background: "var(--surface-elevated)",
          color: "var(--text-primary)", borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)", fontSize: 13, fontWeight: 600,
          boxShadow: "var(--shadow-md)",
        }}
        onFocus={e => { e.currentTarget.style.left = "12px"; e.currentTarget.style.top = "12px"; }}
        onBlur={e => { e.currentTarget.style.left = "-9999px"; }}
      >
        Skip to main content
      </a>

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside style={{
        width: w, flexShrink: 0,
        background: "var(--sidebar-bg)",
        display: "flex", flexDirection: "column",
        borderRight: "1px solid var(--sidebar-border)",
        transition: "width 0.22s cubic-bezier(0.4,0,0.2,1)",
        overflow: "hidden", position: "relative", zIndex: 50,
      }}>

        {/* Logo */}
        <div style={{
          height: 64, padding: collapsed ? "0 16px" : "0 18px",
          display: "flex", alignItems: "center", gap: 12,
          borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0,
        }}>
          <div style={{
            width: 34, height: 34, borderRadius: "var(--radius-lg)",
            background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            <Zap size={16} color="var(--text-on-brand)" fill="var(--text-on-brand)"/>
          </div>
          {!collapsed && (
            <div>
              <p style={{ color: "var(--sidebar-text-active)", fontWeight: 700, fontSize: 14, margin: 0, letterSpacing: "-0.02em" }}>ServiceOS</p>
              <p style={{ color: "var(--sidebar-category)", fontSize: 10, margin: 0, fontWeight: 600, letterSpacing: "0.08em" }}>SUPER ADMIN</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "12px 8px", display: "flex", flexDirection: "column", gap: 0, overflowY: "auto" }}>
          {NAV_GROUPS.map((group, gi) => {
            // FINAL-L5-05M: two independent gates, both must pass — module/
            // category entitlement (isNavItemVisible, pre-existing) AND
            // effective-permission (isNavItemPermitted, this sprint). An
            // empty group (0 permitted items, and no enabled-verticals
            // sub-menu for Catalog) renders nothing at all, per Part 6
            // requirement #2.
            const visibleItems = group.items
              .filter(item => isNavItemVisible(item.id, effectiveMenu))
              .filter(item => isNavItemPermitted(item, effectivePermissions, effectiveRole));
            const hasVerticalsSubmenu = group.label === "Catalog" && effectiveMenu &&
              effectiveMenu.verticals.some(v => v.is_enabled && v.vertical_key !== "home_services") &&
              effectiveRole === "super_admin"; // verticals management is SUPER_ADMIN_ONLY, matching "categories"/"verticals" items above; home_services excluded — its modules live in the static "Home Services" group instead
            if (visibleItems.length === 0 && !hasVerticalsSubmenu) return null;
            return (
            <div key={group.label} style={{ marginBottom: 8 }}>
              {!collapsed && (
                <p style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: "0.09em",
                  color: "var(--sidebar-category)", padding: "10px 10px 4px",
                  margin: 0, textTransform: "uppercase",
                }}>{group.label}</p>
              )}
              {collapsed && gi > 0 && (
                <div style={{ height: 1, background: "var(--sidebar-border)", margin: "6px 10px 6px" }}/>
              )}
              {visibleItems.map(item => (
                  <SidebarItem key={item.id} item={item} active={activeNav === item.id} collapsed={collapsed}/>
                ))}
              {/* After the Catalog group, inject per-vertical sub-menus.
                  home_services is excluded here: its real catalog modules
                  (Service Groups, Master Services, Types & Brands, Service
                  Options, Issue Types, Checklist Templates, Service Setup)
                  are migrated into the static "Home Services" nav group
                  above instead, so the sidebar doesn't show two separate
                  "Home Services" sections for the same vertical. */}
              {hasVerticalsSubmenu && effectiveMenu!.verticals
                .filter(v => v.is_enabled && v.vertical_key !== "home_services")
                .map(v => (
                  <VerticalCatalogSection
                    key={v.vertical_key}
                    vertical={v}
                    activeNav={activeNav}
                    collapsed={collapsed}
                  />
                ))
              }
            </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div style={{
          padding: "10px 8px",
          borderTop: "1px solid var(--sidebar-border)",
          display: "flex", flexDirection: "column", gap: 2,
        }}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={footerBtnStyle(collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : undefined}
          >
            {collapsed
              ? <ChevronRight size={15} style={{ flexShrink: 0 }}/>
              : <ChevronLeft size={15} style={{ flexShrink: 0 }}/>}
            {!collapsed && <span style={{ fontSize: 12 }}>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <TopNav theme={theme} onToggleTheme={toggle} onLogout={handleLogout}/>
        <main id="admin-main-content" tabIndex={-1} style={{ flex: 1, overflowY: "auto", padding: "28px 32px", position: "relative",
          background: "var(--bg-gradient)", outline: "none" }}>
          <div style={{ maxWidth: 1440, margin: "0 auto" }}>
            <Breadcrumbs/>
            {children}
          </div>
        </main>
      </div>

      {tour.mounted && <TourGuide tour={tour}/>}
      <Toaster toasts={toasts} onRemove={id => setToasts(prev => prev.filter(t => t.id !== id))}/>
    </div>
    </AdminMenuRefreshCtx.Provider>
    </AdminShellCtx.Provider>
  );
}

function footerBtnStyle(collapsed: boolean): React.CSSProperties {
  return {
    width: "100%", display: "flex", alignItems: "center",
    gap: 8, padding: "8px 10px", borderRadius: "var(--radius-md)",
    border: "none", background: "transparent", cursor: "pointer",
    color: "var(--sidebar-text)", fontFamily: "inherit",
    justifyContent: collapsed ? "center" : undefined,
    transition: "background 0.12s",
  };
}

// ── Per-Vertical catalog sub-section ─────────────────────────────────────────

function VerticalCatalogSection({ vertical, activeNav, collapsed }: {
  vertical: import("../../lib/api").EffectiveMenuVertical;
  activeNav?: string;
  collapsed: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const modules = vertical.modules.filter(m => m.is_enabled);
  if (modules.length === 0) return null;

  const verticalNavId = `catalog-${vertical.vertical_key}`;
  const isActiveSection = modules.some(m => activeNav === `catalog-${vertical.vertical_key}-${m.key}`);

  if (collapsed) {
    return (
      <a
        href={`/admin/catalog/${vertical.vertical_key}`}
        title={vertical.vertical_label}
        style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: "9px 0", borderRadius: "var(--radius-full)", textDecoration: "none",
          color: isActiveSection ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
          background: isActiveSection ? "var(--sidebar-active)" : "transparent",
          marginBottom: 1,
        }}
      >
        <FolderTree size={16} style={{ opacity: 0.75 }}/>
      </a>
    );
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "8px 12px", borderRadius: "var(--radius-full)", border: "none",
          background: isActiveSection ? "var(--sidebar-active)" : "transparent",
          color: isActiveSection ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
          cursor: "pointer", fontFamily: "inherit", fontSize: 13,
          fontWeight: isActiveSection ? 600 : 400,
          transition: "all 0.12s ease", marginBottom: 1,
        }}
      >
        <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: 0.75 }}>
          <FolderTree size={16}/>
        </span>
        <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1, textAlign: "left" }}>
          {vertical.vertical_label}
        </span>
        {vertical.is_beta && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
            background: "var(--terra-bg)", color: "var(--terra-text)", flexShrink: 0,
          }}>BETA</span>
        )}
        <ChevronRight size={12} style={{
          flexShrink: 0, opacity: 0.5,
          transform: expanded ? "rotate(90deg)" : "none",
          transition: "transform 0.15s",
        }}/>
      </button>
      {expanded && (
        <div style={{ paddingLeft: 14 }}>
          {modules.map(m => {
            const navId = `catalog-${vertical.vertical_key}-${m.key}`;
            const path = m.admin_path || `/admin/catalog/${vertical.vertical_key}`;
            return (
              <SidebarItem
                key={m.key}
                item={{ id: navId, href: path, label: m.label, icon: <Settings2 size={14}/>, requiredPermission: SUPER_ADMIN_ONLY }}
                active={activeNav === navId}
                collapsed={false}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function SidebarItem({
  item, active, collapsed,
}: {
  item: NavItem; active: boolean; collapsed: boolean;
}) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={item.href}
      id={`nav-${item.id}`}
      title={collapsed ? item.label : undefined}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: collapsed ? "9px 0" : "8px 12px",
        justifyContent: collapsed ? "center" : undefined,
        borderRadius: "var(--radius-full)", textDecoration: "none",
        background: active ? "var(--sidebar-active)" : hov ? "var(--sidebar-hover)" : "transparent",
        color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
        fontWeight: active ? 600 : 400,
        fontSize: 13,
        transition: "all 0.12s ease",
        position: "relative",
        marginBottom: 1,
      }}
    >
      <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: active ? 1 : 0.75 }}>
        {item.icon}
      </span>
      {!collapsed && (
        <>
          <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1 }}>{item.label}</span>
          {item.badge != null && item.badge > 0 && (
            <span style={{
              background: "var(--terra)", color: "#fff",
              borderRadius: 999, fontSize: 10, fontWeight: 700,
              padding: "1px 7px", flexShrink: 0,
            }}>{item.badge}</span>
          )}
        </>
      )}
    </a>
  );
}

function TopNav({ theme, onToggleTheme, onLogout }: {
  theme: string; onToggleTheme: () => void; onLogout: () => void;
}) {
  const [search, setSearch] = useState("");
  const [myName, setMyName]   = useState<string>("");
  const [myAvatar, setMyAvatar] = useState<string | null>(null);
  // HS ADMIN-TENANT-E2E-06 fix: the notification bell previously had no
  // onClick and a hardcoded, always-visible red dot (fake "unread"
  // indicator regardless of real state). Now fetches the real unread
  // count from the backend and navigates to the real notification center.
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  // MODULE-L5-11: the bell now opens a small dropdown card with the most recent
  // notifications and a "View all notifications" link, instead of navigating away.
  const [bellOpen, setBellOpen] = useState(false);
  const [recentNotifs, setRecentNotifs] = useState<import("../../lib/api").InAppNotification[] | null>(null);
  const bellRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    authApi.me().then(u => {
      setMyName(u.full_name ?? "Super Admin");
      setMyAvatar((u as unknown as { avatar_url?: string }).avatar_url ?? null);
    }).catch(() => {});
    sprint27AdminApi.getUnreadCount().then(r => setUnreadCount(r.unread_count)).catch(() => setUnreadCount(null));
  }, []);
  const openBell = () => {
    setBellOpen(o => !o);
    if (!bellOpen) {
      sprint27AdminApi.listNotifications({ limit: 6 })
        .then(r => setRecentNotifs(r.items ?? [])).catch(() => setRecentNotifs([]));
    }
  };
  React.useEffect(() => {
    if (!bellOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [bellOpen]);
  const iconBtnStyle: React.CSSProperties = {
    width: 36, height: 36, borderRadius: "var(--radius-lg)",
    border: "1px solid var(--border)", background: "var(--surface)",
    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
    color: "var(--text-secondary)",
    transition: "background 0.12s, border-color 0.12s",
  };
  return (
    <header style={{
      height: 58, display: "flex", alignItems: "center", gap: 14, padding: "0 28px",
      background: "var(--surface)", borderBottom: "1px solid var(--border)",
      boxShadow: "var(--shadow-sm)", flexShrink: 0, position: "sticky", top: 0, zIndex: 200,
    }}>
      {/* Search */}
      <div style={{ flex: 1, maxWidth: 380 }}>
        <div style={{ position: "relative" }}>
          <Search size={14} style={{
            position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)",
            color: "var(--text-tertiary)", pointerEvents: "none",
          }}/>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search tenants, jobs, users…"
            style={{
              width: "100%", height: 36, padding: "0 12px 0 34px", fontSize: 13,
              background: "var(--surface-sunken)", border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none",
              fontFamily: "inherit", transition: "border-color 0.15s, background 0.15s",
            }}
            onFocus={e => { e.currentTarget.style.borderColor = "var(--border-focus)"; e.currentTarget.style.background = "var(--surface)"; }}
            onBlur={e  => { e.currentTarget.style.borderColor = "var(--border)";       e.currentTarget.style.background = "var(--surface-sunken)"; }}
          />
        </div>
      </div>

      <div style={{ flex: 1 }}/>

      {/* Status badge */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "5px 12px", borderRadius: 999,
        background: "var(--success-bg)", border: "1px solid var(--success-border)",
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }}/>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--success-text)" }}>All Systems Live</span>
      </div>

      {/* Theme toggle */}
      <button onClick={onToggleTheme} title={theme === "dark" ? "Light mode" : "Dark mode"} style={iconBtnStyle}>
        {theme === "dark" ? <Sun size={16}/> : <Moon size={16}/>}
      </button>

      {/* Notifications */}
      <div ref={bellRef} style={{ position: "relative" }}>
        <button onClick={openBell}
          aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
          title="Notifications" style={{ ...iconBtnStyle, position: "relative" }}>
          <Bell size={16}/>
          {!!unreadCount && unreadCount > 0 && (
            <span style={{
              position: "absolute", top: 3, right: 3, minWidth: 15, height: 15, padding: "0 3px",
              borderRadius: "50%", background: "var(--danger)", border: "2px solid var(--surface)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 9, fontWeight: 700, color: "#fff", lineHeight: 1,
            }}>{unreadCount > 99 ? "99+" : unreadCount}</span>
          )}
        </button>

        {bellOpen && (
          <div style={{
            position: "absolute", top: 44, right: 0, width: 340, maxHeight: 440,
            background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-lg)", zIndex: 300, overflow: "hidden",
            display: "flex", flexDirection: "column",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Notifications</span>
              {!!unreadCount && unreadCount > 0 && (
                <button
                  onClick={() => { sprint27AdminApi.markAllRead().then(() => {
                    setUnreadCount(0);
                    setRecentNotifs(rs => (rs ?? []).map(n => ({ ...n, read_status: "read" })));
                  }).catch(() => {}); }}
                  style={{ fontSize: 12, color: "var(--accent)", background: "none", border: "none",
                    cursor: "pointer", padding: 0 }}>
                  Mark all read
                </button>
              )}
            </div>

            <div style={{ overflowY: "auto", flex: 1 }}>
              {recentNotifs === null ? (
                <div style={{ padding: 16, fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</div>
              ) : recentNotifs.length === 0 ? (
                <div style={{ padding: 24, textAlign: "center", fontSize: 13, color: "var(--text-tertiary)" }}>
                  No notifications
                </div>
              ) : recentNotifs.map(n => {
                const unread = n.read_status !== "read";
                const dot = n.severity === "critical" || n.severity === "danger" ? "var(--danger)"
                          : n.severity === "warning" ? "var(--warning, #b45309)" : "var(--accent)";
                const go = () => {
                  if (unread) sprint27AdminApi.markRead(n.id).catch(() => {});
                  setBellOpen(false);
                  window.location.href = n.action_url || "/admin/notifications";
                };
                return (
                  <div key={n.id} onClick={go} style={{
                    display: "flex", gap: 10, padding: "11px 16px", cursor: "pointer",
                    borderBottom: "1px solid var(--border)",
                    background: unread ? "var(--surface-2, rgba(0,0,0,0.02))" : "transparent",
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 5,
                      background: unread ? dot : "transparent", flexShrink: 0 }} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: unread ? 700 : 500, color: "var(--text-primary)",
                        marginBottom: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {n.title}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.4,
                        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                        {n.body}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3 }}>
                        {new Date(n.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <a href="/admin/notifications" onClick={() => setBellOpen(false)}
              style={{ display: "block", textAlign: "center", padding: "12px 16px",
                borderTop: "1px solid var(--border)", fontSize: 13, fontWeight: 600,
                color: "var(--accent)", textDecoration: "none" }}>
              View all notifications
            </a>
          </div>
        )}
      </div>

      {/* User → My Profile */}
      <a href="/admin/profile" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
        <div style={{ textAlign: "right" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>{myName || "Super Admin"}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Platform</p>
        </div>
        <DefaultAvatar name={myName || "Super Admin"} src={myAvatar} size={34}/>
      </a>

      {/* Logout */}
      <button onClick={onLogout} title="Log out" style={iconBtnStyle}>
        <LogOut size={16}/>
      </button>
    </header>
  );
}
