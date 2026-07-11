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
  FlaskConical, PercentSquare,
} from "lucide-react";
import { verticalCatalogApi, type EffectiveMenu } from "../../lib/api";
import { useTheme } from "../../hooks/useTheme";
import { useTour } from "../../hooks/useTour";
import { Toaster, type ToastItem } from "../shared/ui";
import { TourGuide } from "../tour/TourGuide";
import { DefaultAvatar } from "../shared/ProfilePhotoUploader";
import { Breadcrumbs } from "./Breadcrumbs";
import { authApi, sprint27AdminApi } from "../../lib/api";

type NavItem = { id: string; href: string; label: string; icon: React.ReactNode; badge?: number | null };
type NavGroup = { label: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { id: "dashboard", href: "/admin/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16}/> },
    ],
  },
  {
    // Provider lifecycle: discover → request → verify → subscribe
    label: "Providers",
    items: [
      { id: "tenants",              href: "/admin/tenants",              label: "All Providers",    icon: <Building2 size={16}/>  },
      { id: "onboarding",           href: "/admin/tenants/onboarding",   label: "New Requests",     icon: <Inbox size={16}/>      },
      { id: "onboarding-providers", href: "/admin/onboarding/providers", label: "Verify & Approve", icon: <ListChecks size={16}/> },
      { id: "packages",             href: "/admin/packages",             label: "Packages",         icon: <Package size={16}/>    },
    ],
  },
  {
    // Day-to-day operational monitoring
    label: "Operations",
    items: [
      { id: "bookings",   href: "/admin/bookings",   label: "Bookings",  icon: <CalendarDays size={16}/>              },
      { id: "operations", href: "/admin/home-services/service-jobs", label: "Jobs", icon: <Wrench size={16}/>, badge: null },
      { id: "customers",  href: "/admin/customers",  label: "Customers", icon: <UserCheck size={16}/>                 },
      { id: "staff",      href: "/admin/staff",      label: "Staff",     icon: <Users size={16}/>                     },
      { id: "reviews",    href: "/admin/reviews",    label: "Reviews",    icon: <Star size={16}/>          },
      { id: "complaints", href: "/admin/complaints", label: "Complaints", icon: <AlertOctagon size={16}/> },
    ],
  },
  {
    // Marketplace verticals management. Brands/Brand Requests are NOT global —
    // they live inside each vertical's catalog section (e.g. Home Services →
    // Types & Brands) to avoid the same route appearing twice in the sidebar.
    label: "Catalog",
    items: [
      { id: "verticals",       href: "/admin/verticals",       label: "Verticals",      icon: <Globe size={16}/>      },
      { id: "categories",      href: "/admin/categories",      label: "Categories",     icon: <Layers size={16}/>     },
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
      { id: "pricing-tiers",       href: "/admin/pricing-tiers",              label: "Pricing Tiers",    icon: <LayoutGrid size={16}/> },
      { id: "location-mapping",    href: "/admin/location-mapping",           label: "City/Zip Mapping", icon: <MapPin size={16}/>     },
      { id: "provider-overrides",  href: "/admin/pricing/provider-overrides", label: "Provider Pricing Overrides", icon: <PercentSquare size={16}/> },
    ],
  },
  {
    // All Home-Services-specific screens live here only — never duplicated
    // into a common/global menu group. Home Services only (see
    // matching_engine.assert_home_services_vertical / get_home_services_category_id).
    label: "Home Services",
    items: [
      { id: "hs-overview", href: "/admin/home-services/overview", label: "Overview", icon: <LayoutGrid size={16}/> },
      { id: "hs-service-catalog", href: "/admin/home-services/service-catalog", label: "Service Catalog", icon: <ListChecks size={16}/> },
      { id: "hs-pricing-rules", href: "/admin/home-services/pricing-rules", label: "Pricing Rules", icon: <Sliders size={16}/> },
      { id: "hs-price-experience", href: "/admin/home-services/price-experience", label: "Customer Price Experience", icon: <FlaskConical size={16}/> },
      { id: "hs-provider-matching", href: "/admin/home-services/provider-matching", label: "Provider Matching", icon: <Zap size={16}/> },
      { id: "hs-matching-diagnostics", href: "/admin/home-services/matching-diagnostics", label: "Matching Diagnostics", icon: <Wrench size={16}/> },
      { id: "hs-service-areas", href: "/admin/home-services/service-areas", label: "Service Areas / Zones", icon: <MapPin size={16}/> },
      { id: "hs-completed-job-deduction", href: "/admin/home-services/completed-job-deduction", label: "Completed Job Deduction", icon: <PercentSquare size={16}/> },
      { id: "hs-settings", href: "/admin/home-services/settings", label: "Home Services Settings", icon: <Settings size={16}/> },
    ],
  },
  {
    // Finance Hub: overview → deposits → top-ups → warranty claims → payouts
    label: "Finance",
    items: [
      { id: "finance",          href: "/admin/finance",          label: "Finance Hub",    icon: <Banknote size={16}/>      },
      { id: "finance-usage-credits", href: "/admin/finance/usage-credits", label: "Usage Credits", icon: <Banknote size={16}/> },
      { id: "finance-deposits", href: "/admin/finance/deposits",  label: "Security Deposits", icon: <Shield size={16}/>     },
      { id: "finance-topups",   href: "/admin/finance/topups",    label: "Credit Top-ups",  icon: <Tag size={16}/>          },
      { id: "finance-claims",   href: "/admin/finance/claims",    label: "Warranty Claims", icon: <AlertOctagon size={16}/> },
      { id: "finance-payouts",  href: "/admin/finance/payouts",   label: "Payouts",         icon: <ScrollText size={16}/>   },
      { id: "compliance",       href: "/admin/compliance",        label: "Compliance",      icon: <ClipboardCheck size={16}/> },
    ],
  },
  {
    label: "Marketing & Growth",
    items: [
      { id: "marketing",     href: "/admin/marketing",     label: "Campaigns",       icon: <Megaphone size={16}/> },
      { id: "notifications", href: "/admin/notifications", label: "Notifications",   icon: <Bell size={16}/>      },
      { id: "analytics",     href: "/admin/analytics",     label: "Analytics",       icon: <BarChart3 size={16}/> },
      { id: "reports",       href: "/admin/reports",       label: "Reports",         icon: <ScrollText size={16}/> },
      { id: "intelligence",  href: "/admin/intelligence",  label: "AI Intelligence", icon: <Brain size={16}/>     },
    ],
  },
  {
    label: "Platform",
    items: [
      { id: "engines",            href: "/admin/engines",            label: "Engines",    icon: <Cpu size={16}/>        },
      { id: "security",           href: "/admin/security",           label: "Security",   icon: <Shield size={16}/>     },
      { id: "workflow-templates", href: "/admin/workflow-templates", label: "Workflows",  icon: <GitBranch size={16}/>  },
      { id: "audit-logs",         href: "/admin/audit-logs",        label: "Audit Logs", icon: <ScrollText size={16}/> },
      { id: "users",              href: "/admin/users",              label: "Users",      icon: <Users size={16}/>      },
      { id: "roles",              href: "/admin/users/roles",        label: "Roles",       icon: <Shield size={16}/>     },
      { id: "permissions",        href: "/admin/users/permissions",  label: "Permissions", icon: <ClipboardCheck size={16}/> },
      { id: "media",              href: "/admin/media",              label: "Media",      icon: <Image size={16}/>      },
      { id: "settings",           href: "/admin/settings",           label: "Settings",   icon: <Settings size={16}/>   },
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
            width: 34, height: 34, borderRadius: 10,
            background: "rgba(255,255,255,0.15)",
            backdropFilter: "blur(4px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0, border: "1px solid rgba(255,255,255,0.2)",
          }}>
            <Zap size={16} color="white" fill="white"/>
          </div>
          {!collapsed && (
            <div>
              <p style={{ color: "#fff", fontWeight: 700, fontSize: 14, margin: 0, letterSpacing: "-0.02em" }}>ServiceOS</p>
              <p style={{ color: "var(--sidebar-category)", fontSize: 10, margin: 0, fontWeight: 600, letterSpacing: "0.08em" }}>SUPER ADMIN</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "12px 8px", display: "flex", flexDirection: "column", gap: 0, overflowY: "auto" }}>
          {NAV_GROUPS.map((group, gi) => (
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
              {group.items
                .filter(item => isNavItemVisible(item.id, effectiveMenu))
                .map(item => (
                  <SidebarItem key={item.id} item={item} active={activeNav === item.id} collapsed={collapsed}/>
                ))}
              {/* After the Catalog group, inject per-vertical sub-menus */}
              {group.label === "Catalog" && effectiveMenu && effectiveMenu.verticals
                .filter(v => v.is_enabled)
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
          ))}
        </nav>

        {/* Footer */}
        <div style={{
          padding: "10px 8px",
          borderTop: "1px solid var(--sidebar-border)",
          display: "flex", flexDirection: "column", gap: 2,
        }}>
          <button onClick={() => setCollapsed(!collapsed)} style={footerBtnStyle(collapsed)}>
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
        <main style={{ flex: 1, overflowY: "auto", padding: "28px 32px", position: "relative",
          background: "var(--bg-gradient)" }}>
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
    gap: 8, padding: "8px 10px", borderRadius: 8,
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
          padding: "9px 0", borderRadius: 8, textDecoration: "none",
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
          padding: "8px 10px", borderRadius: 8, border: "none",
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
            background: "rgba(124,58,237,0.2)", color: "#7c3aed", flexShrink: 0,
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
                item={{ id: navId, href: path, label: m.label, icon: <Settings2 size={14}/> }}
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
        padding: collapsed ? "9px 0" : "8px 10px",
        justifyContent: collapsed ? "center" : undefined,
        borderRadius: 8, textDecoration: "none",
        background: active ? "var(--sidebar-active)" : hov ? "var(--sidebar-hover)" : "transparent",
        color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
        fontWeight: active ? 600 : 400,
        fontSize: 13,
        transition: "all 0.12s ease",
        position: "relative",
        marginBottom: 1,
      }}
    >
      {/* Active indicator */}
      {active && (
        <span style={{
          position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)",
          width: 3, height: 20, borderRadius: "0 3px 3px 0",
          background: "rgba(255,255,255,0.9)",
        }}/>
      )}
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
  React.useEffect(() => {
    authApi.me().then(u => {
      setMyName(u.full_name ?? "Super Admin");
      setMyAvatar((u as unknown as { avatar_url?: string }).avatar_url ?? null);
    }).catch(() => {});
    sprint27AdminApi.getUnreadCount().then(r => setUnreadCount(r.unread_count)).catch(() => setUnreadCount(null));
  }, []);
  const iconBtnStyle: React.CSSProperties = {
    width: 36, height: 36, borderRadius: 10,
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
              borderRadius: 10, color: "var(--text-primary)", outline: "none",
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
      <a href="/admin/notifications" aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
        title="Notifications" style={{ ...iconBtnStyle, position: "relative", textDecoration: "none" }}>
        <Bell size={16}/>
        {!!unreadCount && unreadCount > 0 && (
          <span style={{
            position: "absolute", top: 3, right: 3, minWidth: 15, height: 15, padding: "0 3px",
            borderRadius: "50%", background: "var(--danger)", border: "2px solid var(--surface)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 9, fontWeight: 700, color: "#fff", lineHeight: 1,
          }}>{unreadCount > 99 ? "99+" : unreadCount}</span>
        )}
      </a>

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
