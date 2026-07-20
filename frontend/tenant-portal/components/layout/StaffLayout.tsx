"use client";
import React from "react";
import {
  LayoutDashboard, ListChecks, UserCircle, Wrench, MapPin, Clock, FileText,
  ClipboardList, Bell, ShieldCheck, History, Settings, LogOut, MessageSquare,
} from "lucide-react";
import { useStaffContext, StaffContextProvider } from "../../hooks/useStaffContext";
import { Skeleton, Badge } from "../shared/ui";
import { authApi, staffMyWorkApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { Breadcrumbs, type BreadcrumbItem } from "./Breadcrumbs";

type NavItem = { id: string; href: string; label: string; icon: React.ReactNode };

// Phase 2A Slice 2B — the technician shell never rendered breadcrumbs at
// all (unlike TenantLayout, which uses the shared Breadcrumbs component).
// Static default per nav section; a page can override via the `crumbs`
// prop for contextual routes with a real entity (e.g. a specific job) —
// see /staff/jobs/[job_id]/page.tsx for that usage. Deliberately a
// separate, technician-specific map rather than reusing
// lib/page-registry.ts's TENANT_PAGE_REGISTRY: the technician shell's nav
// labels and hierarchy ("Assigned Work", no parent groups) differ from the
// tenant-owner shell's, and the brief explicitly warns not to assume the
// same parent navigation for every role.
const STAFF_BREADCRUMBS: Record<string, BreadcrumbItem[]> = {
  "dashboard":     [{ label: "Today" }],
  "my-work":       [{ label: "My Work" }],
  "jobs":          [{ label: "My Jobs" }],
  "profile":       [{ label: "Profile" }],
  "skills":        [{ label: "Profile", href: "/staff/profile" }, { label: "Skills & Services" }],
  "service-areas": [{ label: "Profile", href: "/staff/profile" }, { label: "Service Areas" }],
  "availability":  [{ label: "Profile", href: "/staff/profile" }, { label: "Availability" }],
  "chat":          [{ label: "Messages" }],
  "documents":     [{ label: "Profile", href: "/staff/profile" }, { label: "Documents" }],
  "notifications": [{ label: "Notifications" }],
  "activity":      [{ label: "Profile", href: "/staff/profile" }, { label: "Activity" }],
  "sessions":      [{ label: "Profile", href: "/staff/profile" }, { label: "Security / Sessions" }],
};

// Phase 2A Slice 2 — My Work nav badge. Source: GET /v1/staff/my-work
// (real, Slice-1-implemented endpoint). Per the approved rule, a failed
// request must not render as a "0" badge — it renders no badge at all,
// indistinguishable from "badge feature not present" rather than falsely
// claiming zero pending items.
function useMyWorkBadgeCount(): number | null {
  const work = useApi(React.useCallback(() => staffMyWorkApi.list(), []), []);
  if (work.error || work.loading || !work.data) return null;
  return work.data.items.filter(
    it => it.priority === "urgent" || it.category === "REQUIRES_MY_ACTION",
  ).length;
}

const NAV: NavItem[] = [
  { id: "dashboard",      href: "/staff/dashboard",          label: "Dashboard",         icon: <LayoutDashboard size={16}/> },
  { id: "my-work",        href: "/staff/my-work",            label: "My Work",           icon: <ListChecks size={16}/> },
  { id: "profile",        href: "/staff/profile",            label: "My Profile",        icon: <UserCircle size={16}/> },
  { id: "skills",         href: "/staff/skills",             label: "Skills & Services", icon: <Wrench size={16}/> },
  { id: "service-areas",  href: "/staff/service-areas",      label: "Service Areas",     icon: <MapPin size={16}/> },
  { id: "availability",   href: "/staff/availability",       label: "Availability",      icon: <Clock size={16}/> },
  { id: "jobs",           href: "/staff/jobs",                label: "Assigned Work",     icon: <ClipboardList size={16}/> },
  { id: "chat",           href: "/staff/chat",                label: "Messages",          icon: <MessageSquare size={16}/> },
  { id: "documents",      href: "/staff/documents",          label: "Documents",         icon: <FileText size={16}/> },
  { id: "notifications",  href: "/staff/notifications",      label: "Notifications",     icon: <Bell size={16}/> },
  { id: "activity",       href: "/staff/activity",           label: "Activity",          icon: <History size={16}/> },
  { id: "sessions",       href: "/staff/security/sessions",  label: "Security / Sessions", icon: <ShieldCheck size={16}/> },
];

export function StaffLayout({ activeNav, children, crumbs }: {
  activeNav: string; children: React.ReactNode;
  /** Override for contextual routes with a real entity in the breadcrumb
      trail (e.g. a specific job) — falls back to the static per-section
      default in STAFF_BREADCRUMBS when omitted. */
  crumbs?: BreadcrumbItem[];
}) {
  const ctx = useStaffContext();
  const myWorkBadgeCount = useMyWorkBadgeCount();

  if (ctx.loading) {
    return (
      <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
        <div style={{ width: 240, padding: 20 }}><Skeleton height={400}/></div>
        <div style={{ flex: 1, padding: 24 }}><Skeleton height={300}/></div>
      </div>
    );
  }

  if (!ctx.user || !ctx.isTechnician) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "var(--bg)" }}>
        <div style={{ textAlign: "center", maxWidth: 420 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
            {ctx.user ? "This app is for staff/technician accounts only." : "Please sign in."}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 16 }}>
            {ctx.error || `Your account role ("${ctx.user?.role ?? "unknown"}") does not have access to the Technician App.`}
          </p>
          <a href="/staff/login" style={{ color: "var(--brand)", fontSize: 13, fontWeight: 600 }}>Go to Staff Login</a>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    try { await authApi.logout(); } catch { /* proceed to clear session regardless */ }
    localStorage.removeItem("serviceos_tenant_token");
    localStorage.removeItem("serviceos_tenant_refresh");
    window.location.href = "/staff/login";
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <aside style={{ width: 240, flexShrink: 0, borderRight: "1px solid var(--border)", background: "var(--surface)",
        display: "flex", flexDirection: "column", padding: "18px 12px" }}>
        <div style={{ padding: "0 8px 18px", borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "var(--brand)" }}>Technician App</div>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>ServiceOS Staff Portal</div>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
          {NAV.map(item => (
            <a key={item.id} href={item.href} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8,
              textDecoration: "none", fontSize: 13,
              color: activeNav === item.id ? "var(--brand)" : "var(--text-secondary)",
              background: activeNav === item.id ? "var(--brand-muted, rgba(37,99,235,0.08))" : "transparent",
              fontWeight: activeNav === item.id ? 600 : 400,
            }}>
              {item.icon}
              <span style={{ flex: 1 }}>{item.label}</span>
              {/* My Work badge: only rendered on real, non-zero, successfully-loaded
                  counts. Loading/error/zero all render nothing -- never a fake "0". */}
              {item.id === "my-work" && myWorkBadgeCount !== null && myWorkBadgeCount > 0 && (
                <Badge variant="warning" size="sm">{myWorkBadgeCount}</Badge>
              )}
            </a>
          ))}
        </nav>
        <button onClick={handleLogout} style={{
          display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8,
          border: "none", background: "transparent", color: "var(--text-secondary)", fontSize: 13,
          cursor: "pointer", marginTop: 8,
        }}>
          <LogOut size={16}/> Logout
        </button>
      </aside>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>{ctx.user.full_name || ctx.user.email}</div>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              Provider Business: <TenantNameInline/> · Role: technician
            </div>
          </div>
          <Badge variant="success" size="sm">Active</Badge>
        </header>
        <main style={{ flex: 1, padding: 24, overflow: "auto" }}>
          <Breadcrumbs crumbs={crumbs ?? STAFF_BREADCRUMBS[activeNav] ?? [{ label: "Today" }]}/>
          <StaffContextProvider value={ctx}>{children}</StaffContextProvider>
        </main>
      </div>
    </div>
  );
}

function TenantNameInline() {
  const name = typeof window !== "undefined" ? localStorage.getItem("serviceos_tenant_name") : null;
  return <>{name || "—"}</>;
}
