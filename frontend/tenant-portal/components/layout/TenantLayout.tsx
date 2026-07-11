"use client";
import React, { useState, useEffect, createContext, useContext, useCallback } from "react";

const TenantShellCtx = createContext(false);
import {
  LayoutDashboard, Wrench, CalendarDays, Users2,
  Star, MessageCircle, FileText,
  Settings, Sun, Moon, ChevronLeft, ChevronRight,
  Bell, Search, HelpCircle, CalendarCheck, Package, LogOut,
  BarChart2, Megaphone,
  Activity, CheckSquare, X, RefreshCw,
  CheckCircle2, XCircle, AlertCircle, ArrowRight, Zap,
  CreditCard, Shield, Receipt,
} from "lucide-react";
import { useTheme } from "../../hooks/useTheme";
import { useTour } from "../../hooks/useTour";
import { useTenant } from "../../hooks/useTenant";
import { Toaster, type ToastItem } from "../shared/ui";
import { TourGuide } from "../tour/TourGuide";
import { DefaultAvatar } from "../shared/ProfilePhotoUploader";
import { Breadcrumbs } from "./Breadcrumbs";
import { authApi, providerStatusApi, tenantSetupApi, staffApi, providerServiceAreasApi, usageCreditsApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

type NavItem = { id: string; href: string; label: string; icon: React.ReactNode; badge?: number };
type NavGroup = { label: string; items: NavItem[]; special?: string };

// ── Setup wizard steps ────────────────────────────────────────────────────────
const SETUP_STEPS = [
  { key: "profile_complete",        label: "Business Profile",       desc: "Add business name, GST, address",           href: "/profile",                   icon: <Zap size={14}/> },
  { key: "package_active",          label: "Package Active",         desc: "Activate your subscription package",        href: "/finance/package",            icon: <Package size={14}/> },
  { key: "credits_available",       label: "Usage Credits",          desc: "Ensure credits are available",              href: "/finance/usage-credit-ledger",icon: <CreditCard size={14}/> },
  { key: "security_deposit_ok",     label: "Security Deposit",       desc: "₹5,000 deposit required",                  href: "/finance/security-deposit",   icon: <Shield size={14}/> },
  { key: "service_areas_count",     label: "Service Areas",          desc: "Add at least one coverage area",            href: "/provider/service-areas",     icon: <ArrowRight size={14}/> },
  { key: "active_services_count",   label: "Enable a Service",       desc: "Enable AC Repair or another service",       href: "/tenant/setup/services",      icon: <Zap size={14}/> },
  { key: "coverage_configured",     label: "Service Coverage",       desc: "Set types, brands & issue types",           href: "/provider/service-coverage",  icon: <Shield size={14}/> },
  { key: "staff_count",             label: "Add Technician",         desc: "Add at least one technician",               href: "/provider/staff",             icon: <Users2 size={14}/> },
  { key: "availability_configured", label: "Business Hours",          desc: "Set working hours",                         href: "/tenant/setup/availability",  icon: <CalendarCheck size={14}/> },
  { key: "documents_submitted",     label: "Documents",              desc: "Submit required business documents",        href: "/documents",                  icon: <FileText size={14}/> },
];

// ── Enterprise static nav ─────────────────────────────────────────────────────
const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { id: "dashboard", href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16}/> },
    ],
  },
  {
    label: "Setup",
    items: [
      { id: "provider-status",                    href: "/provider/status",                    label: "Setup Checklist",       icon: <CheckSquare size={16}/> },
      { id: "profile",                            href: "/profile",                            label: "Business Profile",      icon: <Zap size={16}/> },
      { id: "provider-service-areas",             href: "/provider/service-areas",             label: "Service Areas",         icon: <ArrowRight size={16}/> },
      { id: "tenant-setup-services",              href: "/tenant/setup/services",              label: "Service Setup",         icon: <Wrench size={16}/> },
      { id: "provider-service-coverage",          href: "/provider/service-coverage",          label: "Service Coverage",      icon: <Shield size={16}/> },
      { id: "provider-availability",              href: "/tenant/setup/availability",          label: "Business Hours",        icon: <CalendarCheck size={16}/> },
    ],
  },
  {
    label: "Team",
    items: [
      { id: "provider-staff", href: "/provider/staff", label: "Staff & Technicians", icon: <Users2 size={16}/> },
    ],
  },
  {
    label: "Operations",
    items: [
      { id: "jobs",         href: "/jobs",         label: "Jobs",         icon: <Wrench size={16}/>,       badge: 0 },
      { id: "bookings",     href: "/bookings",     label: "Bookings",     icon: <CalendarDays size={16}/>,  badge: 0 },
      { id: "appointments", href: "/appointments", label: "Appointments", icon: <CalendarCheck size={16}/> },
    ],
  },
  {
    label: "Finance",
    items: [
      { id: "finance-package",       href: "/finance/package",             label: "Package & Credits",   icon: <Package size={16}/> },
      { id: "finance-credit-ledger", href: "/finance/usage-credit-ledger", label: "Usage Credit Ledger", icon: <Receipt size={16}/> },
      { id: "finance-deposit",       href: "/finance/security-deposit",    label: "Security Deposit",    icon: <Shield size={16}/> },
    ],
  },
  {
    label: "Engagement",
    items: [
      { id: "reviews",   href: "/reviews",   label: "Reviews",   icon: <Star size={16}/> },
      { id: "marketing", href: "/marketing", label: "Marketing", icon: <Megaphone size={16}/> },
      { id: "customers", href: "/customers", label: "Customers", icon: <Users2 size={16}/> },
      { id: "chat",      href: "/chat",      label: "Chat",      icon: <MessageCircle size={16}/> },
    ],
  },
  {
    label: "Insights",
    items: [
      { id: "analytics", href: "/analytics", label: "Analytics", icon: <BarChart2 size={16}/> },
      { id: "reports",   href: "/reports",   label: "Reports",   icon: <FileText size={16}/> },
    ],
  },
  {
    label: "More",
    items: [
      { id: "documents",     href: "/documents",     label: "Documents",     icon: <FileText size={16}/> },
      { id: "notifications", href: "/notifications", label: "Notifications", icon: <Bell size={16}/> },
      { id: "activity",      href: "/activity",      label: "Activity",      icon: <Activity size={16}/> },
      { id: "settings",      href: "/settings",      label: "Settings",      icon: <Settings size={16}/> },
    ],
  },
];

// ── Setup Wizard Drawer ───────────────────────────────────────────────────────
function SetupWizardDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const statusApi = useApi(useCallback(() => providerStatusApi.get(), []), []);
  const pkgApi    = useApi(useCallback(() => tenantSetupApi.getPackage(), []), []);
  // FINAL-L5-03: was tenantSetupApi.getWallet() -> /v1/provider/wallet, which
  // reads the dormant `tenant_wallets` table (never populated by the
  // canonical seed) and always 500s. Usage Credit Balance is the real,
  // canonical source (tenant_billing.credit_balance via usage_credit_ledger),
  // already used elsewhere in this app -- see project memory on
  // tenant_wallets being legacy/dormant.
  const creditApi = useApi(useCallback(() => usageCreditsApi.getBalance(), []), []);
  const staffApi2 = useApi(useCallback(() => staffApi.list(), []), []);
  const areasApi  = useApi(useCallback(() => providerServiceAreasApi.list(), []), []);

  const s       = statusApi.data;
  const blockers = [...(s?.visibility_blockers ?? []), ...(s?.bookability_blockers ?? [])];
  const pkg     = pkgApi.data as Record<string, unknown> | null;
  const staffCount = staffApi2.data?.users?.length ?? 0;
  const areasCount = areasApi.data?.total ?? areasApi.data?.areas?.length ?? 0;
  const creditBal  = creditApi.data?.usage_credit_balance ?? 0;
  const pkgStatus  = String(pkg?.status ?? "inactive");
  const depositSt  = String(pkg?.security_deposit_status ?? "pending");

  function isDone(key: string): boolean {
    switch (key) {
      case "profile_complete":        return !blockers.some(b => b.code?.includes("profile"));
      case "package_active":          return pkgStatus === "active";
      case "credits_available":       return creditBal > 0;
      case "security_deposit_ok":     return depositSt === "received" || depositSt === "waived";
      case "service_areas_count":     return areasCount > 0;
      case "active_services_count":   return !blockers.some(b => b.code?.includes("service") || b.code?.includes("offering"));
      case "coverage_configured":     return !blockers.some(b => b.code?.includes("coverage"));
      case "staff_count":             return staffCount > 0;
      case "availability_configured": return !blockers.some(b => b.code?.includes("availability") || b.code?.includes("slot"));
      case "documents_submitted":     return !blockers.some(b => b.code?.includes("document"));
      default:                        return false;
    }
  }

  const doneCount  = SETUP_STEPS.filter(st => isDone(st.key)).length;
  const total      = SETUP_STEPS.length;
  const pct        = Math.round((doneCount / total) * 100);
  const isBookable = s?.is_bookable ?? false;
  const loading    = statusApi.loading || pkgApi.loading || creditApi.loading;

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
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
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
                <button onClick={() => { statusApi.refetch(); pkgApi.refetch(); creditApi.refetch(); staffApi2.refetch(); areasApi.refetch(); }}
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
                <div key={i} style={{ height: 60, background: "var(--surface-sunken)", borderRadius: 10, animation: "pulse 1.5s ease-in-out infinite" }}/>
              ))}
            </div>
          ) : statusApi.error ? (
            <div style={{ padding: "16px", background: "var(--danger-bg)", borderRadius: 10, border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: "0 0 8px" }}>Could not load setup status.</p>
              <button onClick={statusApi.refetch} style={{ fontSize: 12, padding: "5px 12px", borderRadius: 8, border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 5 }}>
                <RefreshCw size={11}/> Retry
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {SETUP_STEPS.map((step, idx) => {
                const done = isDone(step.key);
                return (
                  <a
                    key={step.key}
                    href={done ? undefined : step.href}
                    onClick={done ? undefined : onClose}
                    style={{
                      display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                      background: done ? "var(--success-bg)" : "var(--surface-sunken)",
                      border: `1px solid ${done ? "var(--success-border)" : "var(--border)"}`,
                      borderRadius: 10, textDecoration: "none",
                      cursor: done ? "default" : "pointer",
                      transition: "all 0.12s",
                    }}
                  >
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
                  </a>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!loading && !statusApi.error && (
          <div style={{ padding: "16px 22px", borderTop: "1px solid var(--border)", flexShrink: 0 }}>
            {pct === 100 ? (
              <div style={{ padding: "12px 16px", background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: 10, display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle2 size={16} style={{ color: "var(--success-text)" }}/>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--success-text)", margin: 0 }}>Setup complete! You're live and accepting bookings.</p>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 10 }}>
                <a href="/provider/status" onClick={onClose} style={{
                  flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                  padding: "10px", borderRadius: 10, textDecoration: "none",
                  background: "var(--brand)", color: "white", fontSize: 13, fontWeight: 600,
                }}>
                  <AlertCircle size={14}/> View Full Status
                </a>
                <button onClick={onClose} style={{
                  padding: "10px 16px", borderRadius: 10, border: "1px solid var(--border)",
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
  const [collapsed,    setCollapsed]    = useState(false);
  const [toasts,       setToasts]       = useState<ToastItem[]>([]);
  const [myName,       setMyName]       = useState<string>("");
  const [myAvatar,     setMyAvatar]     = useState<string | null>(null);
  const [setupOpen,    setSetupOpen]    = useState(false);
  const [setupPct,     setSetupPct]     = useState<number | null>(null);

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
    localStorage.removeItem("serviceos_tenant_token");
    window.location.href = "/login";
  }

  const w = collapsed ? 68 : 248;

  return (
    <TenantShellCtx.Provider value={true}>
    <div style={{ display: "flex", height: "100vh", background: "var(--bg-soft, var(--bg))", overflow: "hidden" }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside style={{
        width: w, flexShrink: 0, height: "100vh",
        background: "var(--sidebar-bg)", display: "flex", flexDirection: "column",
        borderRight: "1px solid var(--sidebar-border)",
        transition: "width 0.22s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden",
      }}>
        {/* Logo */}
        <div style={{ height: 64, padding: collapsed ? "0 16px" : "0 18px", display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: "rgba(255,255,255,0.15)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: "1px solid rgba(255,255,255,0.2)" }}>
            <span style={{ color: "white", fontWeight: 800, fontSize: 15, lineHeight: 1 }}>
              {tenant.tenantName?.[0]?.toUpperCase() ?? "T"}
            </span>
          </div>
          {!collapsed && (
            <div style={{ minWidth: 0 }}>
              <p style={{ color: "#fff", fontWeight: 700, fontSize: 13, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>
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
          {NAV_GROUPS.map((group, gi) => (
            <div key={group.label} style={{ marginBottom: gi < NAV_GROUPS.length - 1 ? 8 : 0 }}>
              {!collapsed && (
                <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.09em", color: "var(--sidebar-category)", padding: "10px 10px 4px", margin: 0, textTransform: "uppercase" }}>
                  {group.label}
                </p>
              )}
              {collapsed && gi > 0 && <div style={{ height: 1, background: "var(--sidebar-border)", margin: "6px 10px" }}/>}

              {group.special === "setup-wizard" ? (
                /* ── Special: Setup wizard button ── */
                <button
                  onClick={() => setSetupOpen(true)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 10,
                    padding: collapsed ? "9px 0" : "8px 10px",
                    justifyContent: collapsed ? "center" : undefined,
                    borderRadius: 8, background: "transparent",
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
                  {!collapsed && (
                    <>
                      <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1, textAlign: "left" }}>Setup</span>
                      {setupPct !== null && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999, flexShrink: 0,
                          background: setupPct === 100 ? "rgba(5,150,105,0.25)" : "rgba(255,255,255,0.18)",
                          color: setupPct === 100 ? "#a7f3d0" : "rgba(255,255,255,0.85)",
                        }}>{setupPct}%</span>
                      )}
                    </>
                  )}
                </button>
              ) : (
                group.items.map(item => (
                  <SidebarItem
                    key={item.id}
                    item={item}
                    active={activeNav === item.id || activeNav === item.href?.replace(/^\//, "")}
                    collapsed={collapsed}
                  />
                ))
              )}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ padding: "10px 8px", borderTop: "1px solid var(--sidebar-border)", display: "flex", flexDirection: "column", gap: 2 }}>
          {!collapsed && (
            <button onClick={tour.restart} style={footerBtnStyle(collapsed)}>
              <HelpCircle size={15} style={{ flexShrink: 0 }}/><span style={{ fontSize: 12 }}>Help & Tour</span>
            </button>
          )}
          <button onClick={() => setCollapsed(!collapsed)} style={footerBtnStyle(collapsed)}>
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
                style={{ width: "100%", height: 36, padding: "0 12px 0 34px", fontSize: 13, background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-primary)", outline: "none", fontFamily: "inherit" }}
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
          <button onClick={toggle} title={theme === "dark" ? "Light mode" : "Dark mode"} style={{ width: 36, height: 36, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
            {theme === "dark" ? <Sun size={16}/> : <Moon size={16}/>}
          </button>
          <a href="/notifications" aria-label="Notifications" title="Notifications" style={{ width: 36, height: 36, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)", textDecoration: "none" }}>
            <Bell size={16}/>
          </a>
          <a href="/profile" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>{myName || tenant.tenantName || "Owner"}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>{tenant.planType ?? "plan"}</p>
            </div>
            <DefaultAvatar name={myName || tenant.tenantName || "Owner"} src={myAvatar} size={34}/>
          </a>
          <button onClick={handleLogout} title="Log out" style={{ width: 36, height: 36, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
            <LogOut size={16}/>
          </button>
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
    </TenantShellCtx.Provider>
  );
}

function footerBtnStyle(collapsed: boolean): React.CSSProperties {
  return { width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 8, border: "none", background: "transparent", cursor: "pointer", color: "var(--sidebar-text)", fontFamily: "inherit", justifyContent: collapsed ? "center" : undefined };
}

function SidebarItem({ item, active, collapsed }: { item: NavItem; active: boolean; collapsed: boolean }) {
  const [hov, setHov] = useState(false);
  return (
    <a href={item.href} id={`nav-${item.id}`} title={collapsed ? item.label : undefined}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: collapsed ? "9px 0" : "8px 10px",
        justifyContent: collapsed ? "center" : undefined,
        borderRadius: 8, textDecoration: "none",
        background: active ? "var(--sidebar-active)" : hov ? "var(--sidebar-hover)" : "transparent",
        color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
        fontWeight: active ? 600 : 400, fontSize: 13,
        transition: "all 0.12s ease", position: "relative", marginBottom: 1,
      }}
    >
      {active && <span style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)", width: 3, height: 20, borderRadius: "0 3px 3px 0", background: "rgba(255,255,255,0.9)" }}/>}
      <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: active ? 1 : 0.75 }}>{item.icon}</span>
      {!collapsed && (
        <>
          <span style={{ flex: 1, whiteSpace: "nowrap", lineHeight: 1 }}>{item.label}</span>
          {item.badge != null && item.badge > 0 && (
            <span style={{ background: "var(--terra)", color: "#fff", borderRadius: 999, fontSize: 10, fontWeight: 700, padding: "1px 7px", flexShrink: 0 }}>{item.badge}</span>
          )}
        </>
      )}
    </a>
  );
}
