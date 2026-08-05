"use client";
import React, { useState, useEffect, createContext, useContext, useCallback } from "react";
import Link from "next/link";

const TenantShellCtx = createContext(false);
import {
  LayoutDashboard, Wrench, Users2,
  FileText,
  Settings, Sun, Moon, ChevronLeft, ChevronRight,
  Bell, Search, HelpCircle, CalendarCheck, Package, LogOut,
  BarChart2, Megaphone,
  Activity, CheckSquare, X, RefreshCw,
  CheckCircle2, XCircle, AlertCircle, ArrowRight,
  CreditCard, Shield,
  MapPin, Clock, Star, Truck, Wallet, ListChecks,
  Image, UserCog, Lock,
} from "lucide-react";
import { useTheme } from "../../hooks/useTheme";
import { useTour } from "../../hooks/useTour";
import { useTenant } from "../../hooks/useTenant";
import { Toaster, type ToastItem } from "../shared/ui";
import { TourGuide } from "../tour/TourGuide";
import { DefaultAvatar } from "../shared/ProfilePhotoUploader";
import { Breadcrumbs } from "./Breadcrumbs";
import { authApi, providerStatusApi, entitlementApi, providerNotifApi, categoryDashboardApi, clearSession, type InAppNotificationItem } from "../../lib/api";
import { useSetupStatus } from "../../hooks/useSetupStatus";

// FINAL-L5-04B: live tenant module/category entitlement state, fetched once
// per shell mount and refreshable after an admin entitlement mutation —
// mirrors the AdminMenuRefreshCtx pattern used for the super-admin vertical
// sidebar (FINAL-L5-04). This is a UX convenience layer only — the backend
// independently enforces entitlement on every mutating endpoint regardless
// of what this hides (see FINAL_L5_04B_SERVICE_SETUP_ENFORCEMENT_REPORT.md).
const EntitlementCtx = createContext<{
  entitledModuleKeys: string[];
  hasAnyModule: boolean;
  loaded: boolean;
  refresh: () => void;
}>({ entitledModuleKeys: [], hasAnyModule: true, loaded: false, refresh: () => {} });

export function useTenantEntitlements() {
  return useContext(EntitlementCtx);
}

type NavItem = { id: string; href: string; label: string; icon: React.ReactNode; badge?: number };
type NavGroup = { label: string; items: NavItem[]; special?: string };

// ── Enterprise static nav ─────────────────────────────────────────────────────
/**
 * Sidebar information architecture.
 *
 * This adopts the GROUPING and LABELS from the approved UX-03 IA
 * (lib/ux03/nav-ia.ts) but deliberately does NOT import it wholesale, for
 * three evidence-based reasons:
 *
 *   1. UX03_NAV_GROUPS predates the Home Services consolidation. Its hrefs
 *      still point at the legacy routes (/bookings, /service-jobs,
 *      /dispatch, /provider/staff), so adopting it verbatim would send the
 *      menu BACK to the superseded pages.
 *   2. Three of its hrefs are route TEMPLATES ("/service-jobs/[id]#quote",
 *      "/provider/staff/[id]/permissions") which are not navigable at all.
 *   3. Several items are marked `readiness: "MOCK_DESIGN_ONLY"` -- design
 *      approved, never built.
 *
 * So the structure is UX-03's; the destinations are the canonical routes
 * that actually exist and are backed by mounted endpoints. Where a Home
 * Services workspace supersedes a legacy page, the workspace wins -- the
 * legacy route stays live and reachable by URL, it simply leaves the nav.
 */
const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { id: "dashboard", href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16}/> },
    ],
  },
  {
    // Business Setup + Business Profile removed from nav 2026-08-04 (user:
    // "no longer using") -- routes still exist and are reachable by direct
    // URL, just no longer linked from the sidebar.
    label: "Setup & Profile",
    items: [
      { id: "provider-compliance", href: "/provider/compliance", label: "Compliance", icon: <Shield size={16}/> },
    ],
  },
  {
    // UX-03 groups "Bookings" and "Jobs" separately; the two pipelines are
    // consolidated into one workspace here, which is what that separation
    // was eventually resolved into.
    label: "Operations",
    items: [
      { id: "hs-bookings-jobs",   href: "/home-services/bookings-jobs",   label: "Bookings & Jobs", icon: <Wrench size={16}/>, badge: 0 },
      { id: "hs-dispatch",        href: "/home-services/dispatch",        label: "Assignment & Dispatch", icon: <Truck size={16}/> },
      { id: "appointments",       href: "/appointments",                  label: "Appointments", icon: <CalendarCheck size={16}/> },
      { id: "hs-availability",    href: "/home-services/availability",    label: "Availability", icon: <Clock size={16}/> },
    ],
  },
  {
    // UX-03 groups: "Services and Pricing" + "Service Areas".
    label: "Services & Coverage",
    items: [
      { id: "hs-services",  href: "/home-services/services",  label: "Services & Pricing", icon: <ListChecks size={16}/> },
      { id: "hs-coverage",  href: "/home-services/coverage",  label: "Service Areas", icon: <MapPin size={16}/> },
      { id: "inventory",    href: "/inventory",               label: "Parts & Inventory", icon: <Package size={16}/> },
    ],
  },
  {
    label: "Team",
    items: [
      { id: "hs-team", href: "/home-services/team", label: "Team Members", icon: <UserCog size={16}/> },
    ],
  },
  {
    // UX-03 groups: "Customers" + "Complaints and Support".
    label: "Customers",
    items: [
      { id: "customers",     href: "/customers",               label: "Customers", icon: <Users2 size={16}/> },
      { id: "hs-reviews",    href: "/home-services/reviews",   label: "Reviews", icon: <Star size={16}/> },
      // UX-03 pointed "Complaints" at /reviews, which is a different
      // surface entirely -- corrected to the real complaints workspace.
      { id: "hs-complaints", href: "/home-services/complaints", label: "Complaints", icon: <AlertCircle size={16}/> },
      { id: "marketing",     href: "/marketing",               label: "Marketing", icon: <Megaphone size={16}/> },
    ],
  },
  {
    // UX-03 group: "Finance and Credits". Its three separate finance links
    // are tabs of the consolidated finance workspace now.
    label: "Finance",
    items: [
      { id: "hs-finance",         href: "/home-services/finance",         label: "Finance & Credits", icon: <Wallet size={16}/> },
      { id: "hs-direct-payments", href: "/home-services/direct-payments", label: "Direct Payments", icon: <CreditCard size={16}/> },
      // "Billing" (-> /packages) removed from nav 2026-08-04 (user: "no
      // longer using") -- route still exists, just no longer linked here.
    ],
  },
  {
    label: "More",
    items: [
      { id: "media",        href: "/media",           label: "Media", icon: <Image size={16}/> },
      { id: "reports",      href: "/reports",         label: "Reports", icon: <BarChart2 size={16}/> },
      { id: "privacy",      href: "/account/privacy", label: "Privacy & Data", icon: <Lock size={16}/> },
      { id: "activity",     href: "/activity",        label: "Activity", icon: <Activity size={16}/> },
      { id: "settings",     href: "/settings",        label: "Settings", icon: <Settings size={16}/> },
      { id: "help-support", href: "/help-support",    label: "Help & Support", icon: <HelpCircle size={16}/> },
    ],
  },
];

// ── Setup Wizard Drawer ───────────────────────────────────────────────────────
export function SetupWizardDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const setup = useSetupStatus();
  const { steps, doneCount, total, isBookable, loading } = setup;
  const statusApi = { error: setup.error, refetch: setup.refetch };
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 999, backdropFilter: "blur(2px)" }}
      />
      {/* Drawer */}
      <div style={{
        position: "fixed", top: 0, right: 0, width: 420, height: "100vh",
        background: "var(--surface)", borderLeft: "1px solid var(--border)",
        zIndex: 1000, display: "flex", flexDirection: "column",
        boxShadow: "-8px 0 32px rgba(0,0,0,0.15)",
        animation: "slideIn 0.22s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <style>{`@keyframes slideIn { from { transform: translateX(100%) } to { transform: translateX(0) } }`}</style>

        {/* Header */}
        <div style={{ padding: "20px 22px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Setup Checklist</h2>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "3px 0 0" }}>
              Complete all steps to go live and accept bookings
            </p>
          </div>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
            <X size={15}/>
          </button>
        </div>

        {/* Progress bar */}
        <div style={{ padding: "16px 22px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999,
                background: isBookable ? "var(--success-bg)" : "var(--warning-bg)",
                color: isBookable ? "var(--success-text)" : "var(--warning-text)",
                border: `1px solid ${isBookable ? "var(--success-border)" : "var(--warning-border)"}`,
                display: "flex", alignItems: "center", gap: 5,
              }}>
                {isBookable ? <><CheckCircle2 size={11}/> Bookable</> : <><XCircle size={11}/> Not Bookable</>}
              </span>
              {!loading && (
                <button onClick={statusApi.refetch}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 4, display: "flex", alignItems: "center" }}>
                  <RefreshCw size={12}/>
                </button>
              )}
            </div>
            <span style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>{pct}%</span>
          </div>
          {/* Progress bar */}
          <div style={{ height: 8, background: "var(--surface-sunken)", borderRadius: 999, overflow: "hidden", border: "1px solid var(--border)" }}>
            <div style={{
              height: "100%",
              width: loading ? "0%" : `${pct}%`,
              borderRadius: 999,
              background: pct === 100 ? "var(--success)" : pct >= 60 ? "var(--brand)" : "var(--warning)",
              transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)",
            }}/>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
            {doneCount} of {total} steps complete
          </p>
        </div>

        {/* Steps list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 22px" }}>
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[...Array(6)].map((_, i) => (
                <div key={i} style={{ height: 60, background: "var(--surface-sunken)", borderRadius: "var(--radius-lg)", animation: "pulse 1.5s ease-in-out infinite" }}/>
              ))}
            </div>
          ) : statusApi.error ? (
            <div style={{ padding: "16px", background: "var(--danger-bg)", borderRadius: "var(--radius-lg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: "0 0 8px" }}>Could not load setup status.</p>
              <button onClick={statusApi.refetch} style={{ fontSize: 12, padding: "5px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 5 }}>
                <RefreshCw size={11}/> Retry
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {steps.map((step, idx) => {
                const done = step.done;
                const stepStyle: React.CSSProperties = {
                  display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                  background: done ? "var(--success-bg)" : "var(--surface-sunken)",
                  border: `1px solid ${done ? "var(--success-border)" : "var(--border)"}`,
                  borderRadius: "var(--radius-lg)", textDecoration: "none",
                  cursor: done ? "default" : "pointer",
                  transition: "all 0.12s",
                };
                const stepContent = (
                  <>
                    {/* Step number / check */}
                    <div style={{
                      width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: done ? "var(--success)" : "var(--border)",
                    }}>
                      {done
                        ? <CheckCircle2 size={15} style={{ color: "white" }}/>
                        : <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)" }}>{idx + 1}</span>}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: done ? "var(--success-text)" : "var(--text-primary)", margin: 0 }}>{step.label}</p>
                      <p style={{ fontSize: 12, color: done ? "var(--success-text)" : "var(--text-tertiary)", margin: "2px 0 0", opacity: 0.85 }}>{step.desc}</p>
                    </div>

                    {done
                      ? <CheckCircle2 size={15} style={{ color: "var(--success-text)", flexShrink: 0 }}/>
                      : <ArrowRight size={14} style={{ color: "var(--brand)", flexShrink: 0 }}/>}
                  </>
                );
                return done ? (
                  <div key={step.key} style={stepStyle}>{stepContent}</div>
                ) : (
                  <Link key={step.key} href={step.href} onClick={onClose} style={stepStyle}>{stepContent}</Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!loading && !statusApi.error && (
          <div style={{ padding: "16px 22px", borderTop: "1px solid var(--border)", flexShrink: 0 }}>
            {pct === 100 ? (
              <div style={{ padding: "12px 16px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: "var(--radius-lg)", display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle2 size={16} style={{ color: "var(--success-text)" }}/>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--success-text)", margin: 0 }}>Setup complete! You're live and accepting bookings.</p>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 10 }}>
                <Link href="/profile" onClick={onClose} style={{
                  flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                  padding: "10px", borderRadius: "var(--radius-lg)", textDecoration: "none",
                  background: "var(--brand)", color: "white", fontSize: 13, fontWeight: 600,
                }}>
                  <AlertCircle size={14}/> Go to Business Profile
                </Link>
                <button onClick={onClose} style={{
                  padding: "10px 16px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
                  background: "var(--surface-sunken)", color: "var(--text-secondary)", fontSize: 13,
                  cursor: "pointer", fontFamily: "inherit",
                }}>
                  Close
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export function TenantLayout({ children, activeNav, addToast }: {
  children: React.ReactNode;
  activeNav?: string;
  addToast?: (t: Omit<ToastItem, "id">) => void;
}) {
  const alreadyMounted = useContext(TenantShellCtx);
  if (alreadyMounted) return <TenantShellCtx.Provider value={true}>{children}</TenantShellCtx.Provider>;
  return <TenantShellInner activeNav={activeNav} addToast={addToast}>{children}</TenantShellInner>;
}

function TenantShellInner({ children, activeNav }: {
  children: React.ReactNode;
  activeNav?: string;
  addToast?: (t: Omit<ToastItem, "id">) => void;
}) {
  const { theme, toggle } = useTheme();
  const tour   = useTour();
  const tenant = useTenant();
  const setupStatus = useSetupStatus();
  // Real bug: this always defaulted to collapsed on every fresh session,
  // so the sidebar rendered as a bare icon rail instead of the labeled,
  // grouped navigation the IA below actually defines -- reported as the
  // whole app "looking old". Now defaults open and remembers the user's
  // last choice, same persistence pattern as useTheme.
  const [collapsed,    setCollapsed]    = useState(false);
  useEffect(() => {
    const saved = localStorage.getItem("serviceos-tenant-sidebar-collapsed");
    if (saved != null) setCollapsed(saved === "1");
  }, []);
  const setCollapsedPersist = useCallback((v: boolean) => {
    setCollapsed(v);
    localStorage.setItem("serviceos-tenant-sidebar-collapsed", v ? "1" : "0");
  }, []);
  const [toasts,       setToasts]       = useState<ToastItem[]>([]);
  const [myName,       setMyName]       = useState<string>("");
  const [myAvatar,     setMyAvatar]     = useState<string | null>(null);
  const [setupOpen,    setSetupOpen]    = useState(false);
  const [setupPct,     setSetupPct]     = useState<number | null>(null);
  const [entitledModuleKeys, setEntitledModuleKeys] = useState<string[]>([]);
  const [entitlementsLoaded, setEntitlementsLoaded] = useState(false);
  // Multi-vertical Phase 3: real vertical capabilities from the backend
  // registry (GET /v1/tenant/navigation), replacing hardcoded per-vertical
  // string lookup tables. Fails open (null) until loaded so nav doesn't
  // flash-hide items on a slow/failed request.
  const [verticalCapabilities, setVerticalCapabilities] = useState<string[] | null>(null);
  const [verticalKey, setVerticalKey] = useState<string | null>(null);
  useEffect(() => {
    categoryDashboardApi.getNavigation()
      .then(nav => {
        setVerticalCapabilities(nav.vertical_context?.capabilities ?? null);
        setVerticalKey(nav.vertical_context?.vertical_key ?? null);
      })
      .catch(() => { setVerticalCapabilities(null); setVerticalKey(null); });
  }, []);

  // Notification bell dropdown: real data via providerNotifApi (backs the
  // /provider/notifications inbox -- same InAppNotificationItem model).
  // Replaces the old plain bell-link-to-page with an in-place popover.
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  const [bellOpen, setBellOpen] = useState(false);
  const [recentNotifs, setRecentNotifs] = useState<InAppNotificationItem[] | null>(null);
  const bellRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    providerNotifApi.unreadCount().then(r => setUnreadCount(r.unread_count)).catch(() => setUnreadCount(null));
  }, []);

  const openBell = () => {
    setBellOpen(o => !o);
    if (!bellOpen) {
      providerNotifApi.list({ limit: 7 })
        .then(r => setRecentNotifs(r.items ?? [])).catch(() => setRecentNotifs([]));
    }
  };

  useEffect(() => {
    if (!bellOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setBellOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [bellOpen]);

  // Profile dropdown — avatar click opens a small menu with profile, billing,
  // settings, theme switch, current package, and logout (replaces the old
  // bare avatar-link + standalone logout button).
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = React.useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!profileOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setProfileOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [profileOpen]);

  const loadEntitlements = useCallback(() => {
    entitlementApi.getMyModules()
      .then(r => { setEntitledModuleKeys(r.modules.map(m => m.module_key)); setEntitlementsLoaded(true); })
      .catch(() => { setEntitlementsLoaded(true); /* fail-open: don't hide nav on a transient error */ });
  }, []);

  useEffect(() => { loadEntitlements(); }, [loadEntitlements]);

  useEffect(() => {
    authApi.me().then(u => {
      setMyName(u.full_name ?? "");
      setMyAvatar((u as unknown as { avatar_url?: string }).avatar_url ?? null);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("serviceos_tenant_token");
    if (!token) { window.location.href = "/login"; return; }
    if (localStorage.getItem("serviceos_force_pw_change") === "1") {
      window.location.href = "/change-password";
    }
  }, []);

  // Load setup pct for sidebar badge (silent, best-effort)
  useEffect(() => {
    providerStatusApi.get().then(s => {
      const blockers = [...(s?.visibility_blockers ?? []), ...(s?.bookability_blockers ?? [])];
      // Simple heuristic: fewer blockers = higher pct
      const est = Math.max(0, Math.round((1 - blockers.length / 10) * 100));
      setSetupPct(est);
    }).catch(() => {});
  }, []);

  async function handleLogout() {
    try { await authApi.logout(); } catch { /* best effort */ }
    // Real bug found this pass (mirrors the identical super-admin one):
    // this only ever cleared serviceos_tenant_token, leaving the refresh
    // token and 7 other session keys behind so the app could silently
    // re-authenticate right after landing on /login. clearSession() is
    // the same helper this file's own 401 handling already relies on.
    clearSession();
  }

  const w = collapsed ? 84 : 248;

  const hasAnyModule = entitlementsLoaded ? entitledModuleKeys.length > 0 : true;
  const ALWAYS_VISIBLE_GROUPS = new Set(["Overview", "More"]);
  // Multi-vertical Phase 3: nav items requiring a specific real capability,
  // resolved from the backend's vertical registry (GET /v1/tenant/navigation
  // -> vertical_context.capabilities) instead of a hardcoded per-vertical-key
  // string list. "jobs" (Bookings & Jobs) is the booking->service_jobs
  // pipeline (Home Services only); "appointments" is the coaching
  // CoachingAppointment model. Fails open (shows the item) until the
  // capability list has loaded, matching the entitlement-gating fail-open
  // pattern already used above for module visibility.
  const ITEM_REQUIRES_CAPABILITY: Record<string, string> = {
    appointments: "appointments",
    jobs: "jobs",
  };
  // Items hidden for a specific vertical rather than gated by a capability --
  // Marketing/Compliance/Privacy & Data removed from the Home Services
  // sidebar per product decision (platform admin manages those policies
  // centrally for that vertical). Driven by the real backend-resolved
  // vertical_key, not a client guess.
  const VERTICAL_HIDDEN_ITEMS: Record<string, string[]> = {
    marketing: ["home_services"], "provider-compliance": ["home_services"], privacy: ["home_services"],
  };
  const itemVisible = (itemId: string) => {
    const hidden = VERTICAL_HIDDEN_ITEMS[itemId];
    if (hidden && verticalKey && hidden.includes(verticalKey)) return false;
    const requiredCapability = ITEM_REQUIRES_CAPABILITY[itemId];
    if (!requiredCapability) return true;
    if (verticalCapabilities === null) return true; // fail open until loaded
    return verticalCapabilities.includes(requiredCapability);
  };
  // "provider-staff" label was hardcoded "Staff & Technicians" regardless of
  // vertical, while the page it links to already computes a category-aware
  // title ("Technicians" / "Trainers & Counsellors" / "Agents" — see
  // pageTitle() in the team-members page). The sidebar label was never kept
  // in sync with that, so a coaching tenant saw "Technicians" in the page
  // but "Staff & Technicians" in the menu that led there.
  const itemLabel = (item: NavItem): string => {
    if (item.id !== "provider-staff") return item.label;
    if (tenant.vertical === "coaching") return "Staff & Trainers";
    if (tenant.vertical === "real_estate") return "Staff & Agents";
    return "Staff & Technicians";
  };
  // Once every real setup step is done (10/10, from the shared hook), the
  // The "Setup" nav group was removed entirely -- Business Profile (in
  // "Overview" above) is now the one-stop place to reach every individual
  // setup page (Service Areas, Service Setup, Service Coverage, Business
  // Hours) or reopen the wizard drawer, via its "Business Setup" section.
  const visibleNavGroups = (hasAnyModule ? NAV_GROUPS : NAV_GROUPS.filter(g => ALWAYS_VISIBLE_GROUPS.has(g.label)))
    .map(g => ({ ...g, items: g.items.filter(it => itemVisible(it.id)).map(it => ({ ...it, label: itemLabel(it) })) }))
    .filter(g => g.items.length > 0);

  return (
    <TenantShellCtx.Provider value={true}>
    <EntitlementCtx.Provider value={{
      entitledModuleKeys,
      hasAnyModule: entitlementsLoaded ? entitledModuleKeys.length > 0 : true,
      loaded: entitlementsLoaded,
      refresh: loadEntitlements,
    }}>
    <div style={{ display: "flex", height: "100vh", background: "var(--bg-soft, var(--bg))", overflow: "hidden" }}>
      <style>{`
        .sidebar-rail-item:focus-visible { outline: 2px solid var(--border-focus); outline-offset: -2px; }
        @media (prefers-reduced-motion: reduce) {
          .sidebar-rail-item, aside, aside * { transition: none !important; animation: none !important; }
        }
      `}</style>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside style={{
        width: w, flexShrink: 0, height: "100vh",
        background: "var(--sidebar-bg)", display: "flex", flexDirection: "column",
        borderRight: "1px solid var(--sidebar-border)",
        transition: "width 0.22s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden",
      }}>
        {/* Logo */}
        <div style={{ height: 64, padding: collapsed ? "0 16px" : "0 18px", display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0 }}>
          <div style={{ width: 34, height: 34, borderRadius: "var(--radius-lg)", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <span style={{ color: "var(--text-on-brand)", fontWeight: 800, fontSize: 15, lineHeight: 1 }}>
              {tenant.tenantName?.[0]?.toUpperCase() ?? "T"}
            </span>
          </div>
          {!collapsed && (
            <div style={{ minWidth: 0 }}>
              <p style={{ color: "var(--sidebar-text-active)", fontWeight: 700, fontSize: 13, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>
                {tenant.tenantName ?? "My Business"}
              </p>
              <p style={{ color: "var(--sidebar-category)", fontSize: 10, margin: 0, fontWeight: 600, letterSpacing: "0.07em" }}>
                {tenant.vertical?.replace(/_/g, " ").toUpperCase() ?? "TENANT PORTAL"}
              </p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, minHeight: 0, padding: "12px 8px", overflowY: "auto" }}>
          {/* FINAL-L5-04B: operational groups (everything except Overview/More)
              require at least one active tenant module entitlement. This is a
              UX convenience, not the security boundary -- see the comment on
              EntitlementCtx above. Fails open (shows everything) until the
              entitlement fetch resolves, and always if it errors. */}
          {visibleNavGroups.map((group, gi) => {
            const isActive = (item: NavItem) =>
              activeNav === item.id || activeNav === item.href?.replace(/^\//, "");

            if (collapsed) {
              // Boxed rail: one connected, bordered, rounded container per
              // group with 1px separators between items -- gap between
              // containers signals group boundaries (a group-name heading
              // wouldn't fit at this width).
              if (group.special === "setup-wizard") {
                return (
                  <div key={group.label} style={{
                    border: "1px solid var(--sidebar-border)", borderRadius: "var(--radius-lg)",
                    overflow: "hidden", marginBottom: 10,
                  }}>
                    <SetupWizardRailButton onClick={() => setSetupOpen(true)} pct={setupPct}/>
                  </div>
                );
              }
              return (
                <div key={group.label} style={{
                  border: "1px solid var(--sidebar-border)", borderRadius: "var(--radius-lg)",
                  overflow: "hidden", marginBottom: 10,
                }}>
                  {group.items.map((item, ii) => (
                    <SidebarItem
                      key={item.id} item={item} active={isActive(item)} collapsed
                      isLast={ii === group.items.length - 1}
                    />
                  ))}
                </div>
              );
            }

            return (
            // Group category headings restored (2026-08-04): the earlier
            // "one clean ordered list" decision read as generic/unlabeled
            // once the sidebar actually rendered expanded by default --
            // the approved reference IA groups items under small-caps
            // section headers (Overview/Operations/Team/etc.), which also
            // gives the tenant a map of the app instead of a long flat list.
            <div key={group.label} style={{ marginBottom: gi < visibleNavGroups.length - 1 ? 16 : 0 }}>
              {!group.special && (
                <p style={{
                  fontSize: 10.5, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase",
                  color: "var(--sidebar-text-muted, var(--sidebar-text))", opacity: 0.55,
                  margin: "0 0 6px", padding: "0 10px",
                }}>{group.label}</p>
              )}
              {group.special === "setup-wizard" ? (
                /* ── Special: Setup wizard button ── */
                <button
                  onClick={() => setSetupOpen(true)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 10px",
                    borderRadius: "var(--radius-md)", background: "transparent",
                    border: "none", cursor: "pointer",
                    color: "var(--sidebar-text)", fontFamily: "inherit",
                    fontSize: 13, fontWeight: 500,
                    transition: "all 0.12s ease", marginBottom: 1,
                  }}
                  onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.background = "var(--sidebar-hover)"}
                  onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.background = "transparent"}
                >
                  <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: 0.75 }}>
                    <CheckSquare size={16}/>
                  </span>
                  <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1, textAlign: "left" }}>Setup</span>
                  {setupPct !== null && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999, flexShrink: 0,
                      background: setupPct === 100 ? "var(--success-bg)" : "var(--sidebar-active)",
                      color: setupPct === 100 ? "var(--success-text)" : "var(--sidebar-text-active)",
                    }}>{setupPct}%</span>
                  )}
                </button>
              ) : (
                group.items.map(item => (
                  <SidebarItem key={item.id} item={item} active={isActive(item)} collapsed={false}/>
                ))
              )}
            </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div style={{ padding: "10px 8px", borderTop: "1px solid var(--sidebar-border)", display: "flex", flexDirection: "column", gap: 2 }}>
          {!collapsed && (
            <button onClick={tour.restart} style={footerBtnStyle(collapsed)}>
              <HelpCircle size={15} style={{ flexShrink: 0 }}/><span style={{ fontSize: 12 }}>Help & Tour</span>
            </button>
          )}
          <button onClick={() => setCollapsedPersist(!collapsed)} style={footerBtnStyle(collapsed)}>
            {collapsed ? <ChevronRight size={15} style={{ flexShrink: 0 }}/> : <ChevronLeft size={15} style={{ flexShrink: 0 }}/>}
            {!collapsed && <span style={{ fontSize: 12 }}>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        {/* Top nav */}
        <header style={{ height: 58, display: "flex", alignItems: "center", gap: 14, padding: "0 28px", background: "var(--surface)", borderBottom: "1px solid var(--border)", boxShadow: "var(--shadow-sm)", flexShrink: 0 }}>
          <div style={{ flex: 1, maxWidth: 360 }}>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }}/>
              <input
                placeholder="Search jobs, customers, bookings…"
                style={{ width: "100%", height: 36, padding: "0 12px 0 34px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit" }}
                onFocus={e => { e.currentTarget.style.borderColor = "var(--border-focus)"; e.currentTarget.style.background = "var(--surface)"; }}
                onBlur={e  => { e.currentTarget.style.borderColor = "var(--border)";       e.currentTarget.style.background = "var(--surface-sunken)"; }}
              />
            </div>
          </div>
          <div style={{ flex: 1 }}/>
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 999, background: "var(--success-bg)", border: "1px solid var(--success-border)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }}/>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--success-text)" }}>Online</span>
          </div>
          <div ref={bellRef} style={{ position: "relative" }}>
            <button onClick={openBell}
              aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
              title="Notifications"
              style={{ width: 36, height: 36, borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)", position: "relative" }}>
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
                      onClick={() => { providerNotifApi.markAllRead().then(() => {
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
                      if (unread) {
                        providerNotifApi.markRead(n.id).catch(() => {});
                        setUnreadCount(c => (c ?? 1) > 0 ? (c as number) - 1 : 0);
                        setRecentNotifs(rs => (rs ?? []).map(x => x.id === n.id ? { ...x, read_status: "read" } : x));
                      }
                      setBellOpen(false);
                      if (n.action_url) window.location.href = n.action_url;
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

                <Link href="/provider/notifications" onClick={() => setBellOpen(false)}
                  style={{ display: "block", textAlign: "center", padding: "12px 16px",
                    borderTop: "1px solid var(--border)", fontSize: 13, fontWeight: 600,
                    color: "var(--accent)", textDecoration: "none" }}>
                  View all notifications
                </Link>
              </div>
            )}
          </div>
          <div ref={profileRef} style={{ position: "relative" }}>
            <button onClick={() => setProfileOpen(o => !o)} style={{
              display: "flex", alignItems: "center", gap: 10, background: "none", border: "none",
              cursor: "pointer", padding: "4px 4px 4px 10px", borderRadius: "var(--radius-lg)",
              fontFamily: "inherit" }}>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>{myName || tenant.tenantName || "Owner"}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>{tenant.planType ?? "plan"}</p>
              </div>
              <DefaultAvatar name={myName || tenant.tenantName || "Owner"} src={myAvatar} size={34}/>
            </button>

            {profileOpen && (
              <div style={{
                position: "absolute", top: 48, right: 0, width: 288,
                background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-lg)", zIndex: 60, overflow: "hidden",
              }}>
                {/* Identity header */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
                  <DefaultAvatar name={myName || tenant.tenantName || "Owner"} src={myAvatar} size={38}/>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {myName || tenant.tenantName || "Owner"}
                    </p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {tenant.tenantName || "Your business"}
                    </p>
                  </div>
                </div>

                {/* Current package / plan */}
                <div style={{ margin: "12px 16px", padding: "10px 12px", borderRadius: "var(--radius-md)",
                  background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
                  {tenant.planType ? (
                    <>
                      <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
                        color: "var(--text-tertiary)", margin: "0 0 2px" }}>Current Plan</p>
                      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--brand)", margin: 0, textTransform: "capitalize" }}>
                        {tenant.planType.replace(/_/g, " ")}
                      </p>
                    </>
                  ) : (
                    <>
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 6px" }}>No active package yet</p>
                      <Link href="/packages" onClick={() => setProfileOpen(false)} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none" }}>
                        Choose a plan →
                      </Link>
                    </>
                  )}
                </div>

                {/* Menu items -- Business Profile / Billing removed 2026-08-04
                    (user: "no longer using"); routes still exist, just no
                    longer linked from this menu. */}
                <div style={{ padding: "4px 8px" }}>
                  <Link href="/analytics" onClick={() => setProfileOpen(false)} style={profileMenuItemStyle}>
                    <BarChart2 size={15}/> Analytics
                  </Link>
                  <Link href="/reports" onClick={() => setProfileOpen(false)} style={profileMenuItemStyle}>
                    <FileText size={15}/> Reports
                  </Link>
                  <button onClick={toggle} style={{ ...profileMenuItemStyle, width: "100%", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", justifyContent: "space-between" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      {theme === "dark" ? <Moon size={15}/> : <Sun size={15}/>} Theme
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "capitalize" }}>{theme}</span>
                  </button>
                  <Link href="/settings" onClick={() => setProfileOpen(false)} style={profileMenuItemStyle}>
                    <Settings size={15}/> Settings
                  </Link>
                </div>

                <div style={{ borderTop: "1px solid var(--border)", padding: "4px 8px" }}>
                  <button onClick={handleLogout} style={{ ...profileMenuItemStyle, width: "100%", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", color: "var(--danger)" }}>
                    <LogOut size={15}/> Log out
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        <main style={{ flex: 1, overflowY: "auto", padding: "28px 32px", background: "var(--bg-gradient)" }}>
          <div style={{ maxWidth: 1440, margin: "0 auto" }}>
            <Breadcrumbs/>
            {children}
          </div>
        </main>
      </div>

      {/* Setup Wizard Drawer */}
      <SetupWizardDrawer open={setupOpen} onClose={() => setSetupOpen(false)} />

      {tour.mounted && <TourGuide tour={tour}/>}
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))}/>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </div>
    </EntitlementCtx.Provider>
    </TenantShellCtx.Provider>
  );
}

const profileMenuItemStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: "var(--radius-md)",
  fontSize: 13, fontWeight: 500, color: "var(--text-primary)", textDecoration: "none",
};

function footerBtnStyle(collapsed: boolean): React.CSSProperties {
  return { width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: "var(--radius-md)", border: "none", background: "transparent", cursor: "pointer", color: "var(--sidebar-text)", fontFamily: "inherit", justifyContent: collapsed ? "center" : undefined };
}

function SetupWizardRailButton({ onClick, pct }: { onClick: () => void; pct: number | null }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      className="sidebar-rail-item"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        gap: 4, padding: "10px 4px", border: "none", cursor: "pointer", fontFamily: "inherit",
        background: hov ? "var(--sidebar-hover)" : "transparent",
        color: "var(--sidebar-text)",
        transition: "background 0.18s ease",
      }}
    >
      <span style={{ position: "relative", display: "flex", opacity: 0.75 }}>
        <CheckSquare size={21}/>
        {pct !== null && pct < 100 && (
          <span style={{
            position: "absolute", top: -5, right: -7, minWidth: 13, height: 13, padding: "0 3px",
            borderRadius: 999, background: "var(--sidebar-active)", color: "var(--sidebar-text-active)",
            fontSize: 8, fontWeight: 700, lineHeight: 1,
            display: "flex", alignItems: "center", justifyContent: "center",
            border: "1.5px solid var(--sidebar-bg)",
          }}>{pct}</span>
        )}
      </span>
      <span style={{ fontSize: 9.5, fontWeight: 500, lineHeight: 1.2 }}>Setup</span>
    </button>
  );
}

function SidebarItem({ item, active, collapsed, isLast }: { item: NavItem; active: boolean; collapsed: boolean; isLast?: boolean }) {
  const [hov, setHov] = useState(false);

  if (collapsed) {
    return (
      <Link
        href={item.href} id={`nav-${item.id}`} title={item.label}
        aria-current={active ? "page" : undefined}
        className="sidebar-rail-item"
        onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
        style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          gap: 4, padding: "10px 4px", textDecoration: "none",
          background: active ? "var(--sidebar-active)" : hov ? "var(--sidebar-hover)" : "transparent",
          color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
          borderBottom: isLast ? "none" : "1px solid var(--sidebar-border)",
          boxShadow: active ? "inset 3px 0 0 0 var(--brand)" : "none",
          transition: "background 0.18s ease, box-shadow 0.18s ease",
          position: "relative",
        }}
      >
        <span style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center", opacity: active ? 1 : 0.75 }}>
          {React.isValidElement(item.icon) ? React.cloneElement(item.icon as React.ReactElement<{ size?: number }>, { size: 21 }) : item.icon}
          {item.badge != null && item.badge > 0 && (
            <span style={{
              position: "absolute", top: -5, right: -7, minWidth: 13, height: 13, padding: "0 3px",
              borderRadius: 999, background: "var(--terra)", color: "#fff",
              fontSize: 8, fontWeight: 700, lineHeight: 1,
              display: "flex", alignItems: "center", justifyContent: "center",
              border: "1.5px solid var(--sidebar-bg)",
            }}>{item.badge > 9 ? "9+" : item.badge}</span>
          )}
        </span>
        <span style={{
          fontSize: 9.5, fontWeight: active ? 700 : 500, lineHeight: 1.2, textAlign: "center",
          maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{item.label}</span>
      </Link>
    );
  }

  return (
    <Link href={item.href} id={`nav-${item.id}`} aria-current={active ? "page" : undefined}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "8px 10px",
        borderRadius: "var(--radius-full)", textDecoration: "none",
        background: active ? "var(--sidebar-active)" : hov ? "var(--sidebar-hover)" : "transparent",
        color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
        fontWeight: active ? 600 : 400, fontSize: 13,
        transition: "all 0.12s ease", position: "relative", marginBottom: 1,
      }}
    >
      <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: active ? 1 : 0.75 }}>{item.icon}</span>
      <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1 }}>{item.label}</span>
      {item.badge != null && item.badge > 0 && (
        <span style={{ background: "var(--terra)", color: "#fff", borderRadius: 999, fontSize: 10, fontWeight: 700, padding: "1px 7px", flexShrink: 0 }}>{item.badge}</span>
      )}
    </Link>
  );
}
