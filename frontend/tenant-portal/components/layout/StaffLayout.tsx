"use client";
import React from "react";
import Link from "next/link";
import {
  LayoutDashboard, UserCircle, Wrench, MapPin, Clock,
  ClipboardList, Bell, ShieldCheck, LogOut,
} from "lucide-react";
import { useStaffContext, StaffContextProvider } from "../../hooks/useStaffContext";
import { Skeleton, Badge } from "../shared/ui";
import { authApi } from "../../lib/api";
import FuvayLogo from "../brand/FuvayLogo";

type NavItem = { id: string; href: string; label: string; icon: React.ReactNode };

const NAV: NavItem[] = [
  { id: "dashboard",      href: "/staff/dashboard",          label: "Dashboard",         icon: <LayoutDashboard size={16}/> },
  { id: "profile",        href: "/staff/profile",            label: "My Profile",        icon: <UserCircle size={16}/> },
  { id: "skills",         href: "/staff/skills",             label: "Skills & Services", icon: <Wrench size={16}/> },
  { id: "service-areas",  href: "/staff/service-areas",      label: "Service Areas",     icon: <MapPin size={16}/> },
  { id: "availability",   href: "/staff/availability",       label: "Availability",      icon: <Clock size={16}/> },
  { id: "jobs",           href: "/staff/jobs",                label: "Assigned Work",     icon: <ClipboardList size={16}/> },
  { id: "notifications",  href: "/staff/notifications",      label: "Notifications",     icon: <Bell size={16}/> },
  { id: "sessions",       href: "/staff/security/sessions",  label: "Security / Sessions", icon: <ShieldCheck size={16}/> },
];

export function StaffLayout({ activeNav, children }: { activeNav: string; children: React.ReactNode }) {
  const ctx = useStaffContext();

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
          <Link href="/staff/login" style={{ color: "var(--brand)", fontSize: 13, fontWeight: 600 }}>Go to Staff Login</Link>
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
          <FuvayLogo height={28}/>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>Technician App</div>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
          {NAV.map(item => (
            <Link key={item.id} href={item.href} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: "var(--radius-full)",
              textDecoration: "none", fontSize: 13,
              color: activeNav === item.id ? "var(--brand-hover)" : "var(--text-secondary)",
              background: activeNav === item.id ? "var(--accent-muted)" : "transparent",
              fontWeight: activeNav === item.id ? 600 : 400,
            }}>
              {item.icon}{item.label}
            </Link>
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
