"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import FuvayLogo from "../brand/FuvayLogo";
import {
  LayoutGrid, Building2, FileText, Tag, MapPin, Users2, Wallet,
  ClipboardCheck, HelpCircle, Bell, ChevronDown, LogOut, User, Shield, Menu, X, Rocket,
  Sun, Moon,
} from "lucide-react";
import { useTenant } from "../../hooks/useTenant";
import { useTheme } from "../../hooks/useTheme";
import { DefaultAvatar } from "../shared/ProfilePhotoUploader";
import { Breadcrumbs } from "../layout/Breadcrumbs";
import { authApi, clearSession, homeServicesSetupOverviewApi, providerNotifApi } from "../../lib/api";

type OnboardingNavId =
  | "overview" | "business-profile" | "documents" | "services-pricing"
  | "coverage-availability" | "staff" | "finance" | "review"
  | "application-status" | "submitted-setup" | "activation-center" | "messages" | "help";

const NAV_ITEMS: { id: OnboardingNavId; href: string; label: string; icon: React.ReactNode }[] = [
  { id: "overview", href: "/tenant/home-services/setup/overview", label: "Setup Overview", icon: <LayoutGrid size={16}/> },
  { id: "business-profile", href: "/tenant/home-services/setup/business-profile", label: "Business Profile", icon: <Building2 size={16}/> },
  { id: "documents", href: "/tenant/home-services/setup/documents", label: "Documents", icon: <FileText size={16}/> },
  { id: "services-pricing", href: "/tenant/home-services/setup/services-pricing", label: "Services & Pricing", icon: <Tag size={16}/> },
  { id: "coverage-availability", href: "/tenant/home-services/setup/coverage-availability", label: "Coverage & Availability", icon: <MapPin size={16}/> },
  { id: "staff", href: "/tenant/home-services/setup/staff", label: "Staff & Technicians", icon: <Users2 size={16}/> },
  { id: "finance", href: "/tenant/home-services/setup/finance", label: "Finance Readiness", icon: <Wallet size={16}/> },
  { id: "review", href: "/tenant/home-services/setup/review", label: "Review & Submit", icon: <ClipboardCheck size={16}/> },
];

// After submission, editable setup navigation is replaced with this
// restricted set -- no operational menus (Dashboard/Jobs/Staff ops/Finance
// ops/etc.) until the backend reports the enrollment as 'active'.
//
// BUG FIX (navigation-all-same-page): "Submitted Setup" and "Messages &
// Requests" used to be hash fragments (#submitted-setup / #messages) on
// /onboarding/application-status rather than real distinct routes -- Next.js
// <Link> to a hash on the CURRENT route just scrolls, it never renders
// different content, so both items always showed Application Status. They
// now point at real pages: /onboarding/submitted-setup and
// /onboarding/messages.
//
// "Setup Overview" was ALSO removed from this restricted set: that page
// (app/(onboarding)/tenant/home-services/setup/overview/page.tsx) calls
// homeServicesSetupOverviewApi.getRouting() on every mount and immediately
// router.replace()s to /onboarding/application-status for any tenant whose
// destination isn't HOME_SERVICES_SETUP_OVERVIEW -- which is every
// submitted/under_review/changes_requested/approved tenant this restricted
// shell is shown to. Linking to it from here meant "Setup Overview" ALSO
// always bounced to Application Status, compounding the same reported bug.
// Removing the link (rather than editing that resolver, which is also used
// as the real top-level onboarding landing-page gate and is out of scope
// here) is the safe fix; "Continue corrections" on Application Status
// already routes there conditionally when it's actually valid.
export const RESTRICTED_NAV_ITEMS: { id: OnboardingNavId; href: string; label: string; icon: React.ReactNode }[] = [
  { id: "application-status", href: "/onboarding/application-status", label: "Application Status", icon: <ClipboardCheck size={16}/> },
  { id: "submitted-setup", href: "/onboarding/submitted-setup", label: "Submitted Setup", icon: <FileText size={16}/> },
  { id: "activation-center", href: "/onboarding/activation-center", label: "Activation Center", icon: <Rocket size={16}/> },
  { id: "messages", href: "/onboarding/messages", label: "Messages & Requests", icon: <Bell size={16}/> },
];

export function OnboardingShell({ children, activeNav, restricted = false, showProgress = true }: {
  children: React.ReactNode;
  activeNav: OnboardingNavId;
  restricted?: boolean;
  /** Active tenants may reuse a setup editor from an operational workspace.
   * Their onboarding overview is intentionally locked (409), so that mode
   * must not make the setup-progress request. */
  showProgress?: boolean;
}) {
  const navItems = restricted ? RESTRICTED_NAV_ITEMS : NAV_ITEMS;

  /**
   * Setup completion is driven by the server's own `progress` object (percentage +
   * completed_required/total_required from the setup overview), never by
   * counting nav items -- the server decides what "required" means, and an
   * optional section must not inflate the number.
   *
   * Only fetched for the editable setup flow; once submitted (`restricted`)
   * the nav is the post-submission set and a setup progress bar would be
   * meaningless.
   */
  const [progress, setProgress] = useState<{ pct: number; done: number; total: number } | null>(null);
  useEffect(() => {
    if (restricted || !showProgress) return;
    let cancelled = false;
    homeServicesSetupOverviewApi
      .getOverview()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((o: any) => {
        const pr = o?.progress;
        if (cancelled || !pr) return;
        const total = Number(pr.total_required ?? 0);
        if (!total) return;
        setProgress({
          pct: Math.max(0, Math.min(100, Number(pr.percentage ?? 0))),
          done: Number(pr.completed_required ?? 0),
          total,
        });
      })
      // A missing progress bar must never break the shell the tenant is
      // trying to complete setup in.
      .catch(() => {});
    return () => { cancelled = true; };
  }, [restricted, showProgress]);
  const tenant = useTenant();
  const { theme, toggle } = useTheme();
  const [myName, setMyName] = useState("");
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const profileRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    authApi.me().then(u => setMyName(u.full_name ?? "")).catch(() => {});
    providerNotifApi.unreadCount().then(r => setUnreadCount(r.unread_count)).catch(() => setUnreadCount(null));
  }, []);

  useEffect(() => {
    if (!profileOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [profileOpen]);

  async function handleLogout() {
    try { await authApi.logout(); } catch { /* best effort */ }
    clearSession();
  }

  return (
    <div className="provider-app-shell" style={{ display: "flex", height: "100vh", background: "var(--bg-soft, var(--bg))", overflow: "hidden" }}>
      <style>{`
        .onboarding-sidebar { width: 248px; transform: translateX(0); transition: transform 0.2s ease; }
        .onboarding-hamburger { display: none; }
        .onboarding-drawer-backdrop { display: none; }
        @media (min-width: 1025px) and (max-width: 1366px) {
          .onboarding-sidebar { width: 220px; }
          .onboarding-main-pad { padding: 22px 20px !important; }
          .onboarding-header-pad { padding-left: 20px !important; padding-right: 20px !important; }
        }
        @media (max-width: 1024px) {
          .onboarding-sidebar {
            position: fixed; top: 0; left: 0; height: 100vh; z-index: 200;
            transform: translateX(-100%);
          }
          .onboarding-sidebar.open { transform: translateX(0); }
          .onboarding-hamburger { display: flex; }
          .onboarding-workspace-selector-text { display: none; }
        }
        @media (max-width: 1024px) {
          .onboarding-drawer-backdrop.open {
            display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 190;
          }
        }
        @media (max-width: 640px) {
          .onboarding-main-pad { padding: 16px !important; }
          .onboarding-header-pad { padding: 0 12px !important; gap: 8px !important; }
          .onboarding-help-text { display: none; }
          .onboarding-help-link { padding: 8px !important; }
          .onboarding-profile-text { display: none; }
        }
      `}</style>

      {/* Sidebar */}
      <aside aria-label="Onboarding navigation" className={`provider-sidebar onboarding-sidebar${drawerOpen ? " open" : ""}`} style={{
        flexShrink: 0, height: "100vh",
        background: "var(--sidebar-bg)", display: "flex", flexDirection: "column",
        borderRight: "1px solid var(--sidebar-border)",
      }}>
        <div style={{ height: 64, padding: "0 18px", display: "flex", alignItems: "center", gap: 10, borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0 }}>
          <FuvayLogo height={32}/>
          <span style={{ flex: 1 }}/>
          <button aria-label="Close menu" onClick={() => setDrawerOpen(false)} className="onboarding-hamburger"
            style={{ background: "none", border: "none", color: "var(--sidebar-text)", cursor: "pointer", padding: 4 }}>
            <X size={18}/>
          </button>
        </div>

        {progress && (
          <div style={{ padding: "14px 18px 4px", flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", color: "var(--sidebar-category)" }}>
                SETUP PROGRESS
              </span>
              <span style={{ fontSize: 11, color: "var(--sidebar-text)" }}>{progress.pct}%</span>
            </div>
            <div
              role="progressbar"
              aria-valuenow={progress.pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Setup completion"
              style={{ height: 6, borderRadius: "var(--radius-full)", background: "var(--sidebar-active)", overflow: "hidden" }}
            >
              <div style={{ width: `${progress.pct}%`, height: "100%", background: "var(--brand)", transition: "width 0.3s ease" }} />
            </div>
            <div style={{ fontSize: 11, color: "var(--sidebar-text)", marginTop: 6 }}>
              {progress.done} of {progress.total} required sections complete
            </div>
          </div>
        )}

        <nav style={{ flex: 1, minHeight: 0, padding: "12px 8px", overflowY: "auto" }}>
          <p style={{
            fontSize: 10.5, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase",
            color: "var(--sidebar-text)", opacity: 0.55, margin: "0 0 6px", padding: "0 10px",
          }}>
            {restricted ? "Application review" : "Tenant onboarding"}
          </p>
          {navItems.map(item => {
            const active = activeNav === item.id;
            return (
              <Link key={item.id} href={item.href} aria-current={active ? "page" : undefined}
                onClick={() => setDrawerOpen(false)}
                style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "9px 10px",
                  borderRadius: "var(--radius-full)", textDecoration: "none",
                  background: active ? "var(--sidebar-active)" : "transparent",
                  color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
                  fontWeight: active ? 600 : 400, fontSize: 13, marginBottom: 2,
                  minHeight: 44,
                }}>
                <span style={{ flexShrink: 0, display: "flex", alignItems: "center", opacity: active ? 1 : 0.75 }}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
          <div style={{ height: 1, background: "var(--sidebar-border)", margin: "10px 8px" }}/>
          <Link href="/help" onClick={() => setDrawerOpen(false)} style={{
            display: "flex", alignItems: "center", gap: 10, padding: "9px 10px",
            borderRadius: "var(--radius-full)", textDecoration: "none",
            color: "var(--sidebar-text)", fontSize: 13, minHeight: 44,
          }}>
            <HelpCircle size={16}/> Help & Support
          </Link>
        </nav>
      </aside>

      <div className={`onboarding-drawer-backdrop${drawerOpen ? " open" : ""}`} onClick={() => setDrawerOpen(false)}/>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <header className="provider-topbar onboarding-header-pad" style={{ height: 58, display: "flex", alignItems: "center", gap: 14, padding: "0 28px", background: "var(--surface)", borderBottom: "1px solid var(--border)", boxShadow: "var(--shadow-sm)", flexShrink: 0 }}>
          <button aria-label="Open menu" onClick={() => setDrawerOpen(true)} className="onboarding-hamburger"
            style={{
              width: 36, height: 36, borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
              background: "var(--surface)", cursor: "pointer", alignItems: "center", justifyContent: "center",
              color: "var(--text-secondary)", flexShrink: 0,
            }}>
            <Menu size={18}/>
          </button>
          <div aria-label="Current workspace" style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", background: "var(--surface-sunken)", minWidth: 0 }}>
            <Building2 size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>
            <span className="onboarding-workspace-selector-text" style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {tenant.tenantName ?? "My Business"}
            </span>
          </div>
          <div style={{ flex: 1 }}/>
          <button type="button" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} title="Change theme" style={{
            width: 36, height: 36, borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
            background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center",
            justifyContent: "center", color: "var(--text-secondary)",
          }}>
            {theme === "dark" ? <Sun size={16}/> : <Moon size={16}/>}
          </button>
          <Link href="/provider/notifications" aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"} title="Notifications" style={{
            width: 36, height: 36, borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
            background: "var(--surface)", cursor: "pointer", display: "flex", alignItems: "center",
            justifyContent: "center", color: "var(--text-secondary)", position: "relative",
          }}>
            <Bell size={16}/>
            {!!unreadCount && unreadCount > 0 && <span style={{
              position: "absolute", top: 2, right: 2, minWidth: 15, height: 15, padding: "0 3px", borderRadius: 999,
              background: "var(--danger)", color: "#fff", border: "2px solid var(--surface)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 700,
            }}>{unreadCount > 99 ? "99+" : unreadCount}</span>}
          </Link>
          <Link href="/help" className="onboarding-help-link" style={{
            display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)",
            textDecoration: "none", padding: "6px 10px",
          }}>
            <HelpCircle size={15}/> <span className="onboarding-help-text">Help</span>
          </Link>
          <div ref={profileRef} style={{ position: "relative" }}>
            <button onClick={() => setProfileOpen(o => !o)} style={{
              display: "flex", alignItems: "center", gap: 10, background: "none", border: "none",
              cursor: "pointer", padding: "4px 4px 4px 10px", borderRadius: "var(--radius-lg)", fontFamily: "inherit",
            }}>
              <div style={{ position: "relative", flexShrink: 0 }}>
                <DefaultAvatar name={myName || tenant.tenantName || "Owner"} src={null} size={32}/>
                <span style={{
                  position: "absolute", bottom: -1, right: -1, width: 10, height: 10, borderRadius: "50%",
                  background: "var(--success)", border: "2px solid var(--surface)",
                }}/>
              </div>
              <div className="onboarding-profile-text" style={{ textAlign: "left" }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.3 }}>
                  {myName || "Owner"}
                </p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, textTransform: "capitalize" }}>Owner</p>
              </div>
              <ChevronDown size={13} className="onboarding-profile-text" style={{ color: "var(--text-tertiary)" }}/>
            </button>
            {profileOpen && (
              <div style={{
                position: "absolute", top: 48, right: 0, width: 220,
                background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-lg)", zIndex: 60, overflow: "hidden", padding: "4px 8px",
              }}>
                <Link href="/settings" style={menuItemStyle}><User size={15}/> My Profile</Link>
                <Link href="/settings?tab=security" style={menuItemStyle}><Shield size={15}/> Security &amp; Sessions</Link>
                <Link href="/help" style={menuItemStyle}><HelpCircle size={15}/> Help</Link>
                <button onClick={handleLogout} style={{ ...menuItemStyle, width: "100%", background: "none", border: "none", cursor: "pointer", color: "var(--danger)" }}>
                  <LogOut size={15}/> Sign Out
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="provider-main onboarding-main-pad" style={{ flex: 1, overflowY: "auto", padding: "28px 32px", background: "var(--bg-gradient)" }}>
          <div className="provider-content" style={{ maxWidth: 1440, margin: "0 auto" }}>
            <Breadcrumbs/>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

const menuItemStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: "var(--radius-md)",
  fontSize: 13, fontWeight: 500, color: "var(--text-primary)", textDecoration: "none",
};
