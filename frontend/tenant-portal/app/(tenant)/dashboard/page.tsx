"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Wrench, Users2, MapPin, CreditCard, Package, Shield, RefreshCw,
  CheckCircle2, XCircle, ClipboardCheck, ChevronRight, Building2,
  FileEdit, Plus, Clock,
} from "lucide-react";
import {
  providerStatusApi, providerServiceAreasApi, providerTeamMembersApi,
  masterCatalogApi, myStatusApi,
  type ProviderStatusResult, type ProviderServiceArea, type TenantEnabledService,
  type ProviderTeamMember, type AdminMasterServiceRow,
  type PackageAssignmentSummary, type TenantSecurityDepositStatus, type TenantCreditWalletDetail,
  type TenantStatusAuditLogEntry,
} from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { Btn, Card, Badge, Skeleton } from "../../../components/shared/ui";

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;
function safeStr(v: unknown, fb = "—"): string { const s = String(v ?? "").trim(); return s || fb; }
function timeOfDayGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good Morning";
  if (h < 17) return "Good Afternoon";
  return "Good Evening";
}
function humanizeAction(action: string): string {
  return action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
function timeAgo(iso: string): string {
  const d = new Date(iso).getTime();
  if (isNaN(d)) return "—";
  const diffMs = Date.now() - d;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

const CHECKLIST_DEFS: { key: string; label: string; blockerCode: string; route: string }[] = [
  { key: "account_active", label: "Account Active & Verified", blockerCode: "TENANT_SUSPENDED_OR_REJECTED", route: "/support" },
  { key: "business_profile", label: "Business Profile Complete", blockerCode: "BUSINESS_PROFILE_INCOMPLETE", route: "/profile" },
  { key: "service_published", label: "At Least One Service Published", blockerCode: "NO_PUBLISHED_SERVICE", route: "/tenant/setup/services" },
  { key: "price_range", label: "Provider Price Range Configured", blockerCode: "PROVIDER_PRICE_RANGE_MISSING", route: "/tenant/setup/services" },
  { key: "service_area", label: "At Least One Service Area", blockerCode: "SERVICE_AREA_MISSING", route: "/provider/service-areas" },
  { key: "availability", label: "Availability Configured", blockerCode: "AVAILABILITY_MISSING", route: "/provider/availability" },
  { key: "usage_credits", label: "Usage Credits Available", blockerCode: "USAGE_CREDITS_INSUFFICIENT", route: "/finance/usage-credit-ledger" },
  { key: "security_deposit", label: "Security Deposit Satisfied", blockerCode: "SECURITY_DEPOSIT_REQUIRED", route: "/finance/security-deposit" },
];

export default function DashboardPage() {
  const [tenantName, setTenantName] = useState("Your Business");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const n = localStorage.getItem("serviceos_tenant_name");
      if (n) setTenantName(n);
    }
  }, []);

  const statusApi = useApi<ProviderStatusResult>(useCallback(() => providerStatusApi.get(), []), []);
  const svcEnabledApi = useApi<{ services: TenantEnabledService[] }>(useCallback(() => masterCatalogApi.listEnabled(), []), []);
  const svcAvailableApi = useApi<{ services: AdminMasterServiceRow[] }>(useCallback(() => masterCatalogApi.listAvailable(), []), []);
  const areasApi = useApi<{ areas: ProviderServiceArea[]; total: number }>(useCallback(() => providerServiceAreasApi.list(), []), []);
  const staffApi = useApi<{ members: ProviderTeamMember[]; count: number }>(useCallback(() => providerTeamMembersApi.list(), []), []);
  const pkgApi = useApi<PackageAssignmentSummary>(useCallback(() => myStatusApi.getPackageSummary(), []), []);
  const depositApi = useApi<TenantSecurityDepositStatus>(useCallback(() => myStatusApi.getSecurityDeposit(), []), []);
  const walletApi = useApi<TenantCreditWalletDetail>(useCallback(() => myStatusApi.getCreditWallet(), []), []);
  const activityApi = useApi<{ logs: TenantStatusAuditLogEntry[] }>(useCallback(() => myStatusApi.getAuditLog(6), []), []);

  const loading = statusApi.loading || svcEnabledApi.loading || areasApi.loading || staffApi.loading;

  const refreshAll = useCallback(() => {
    statusApi.refetch(); svcEnabledApi.refetch(); svcAvailableApi.refetch();
    areasApi.refetch(); staffApi.refetch(); pkgApi.refetch(); depositApi.refetch();
    walletApi.refetch(); activityApi.refetch();
  }, [statusApi, svcEnabledApi, svcAvailableApi, areasApi, staffApi, pkgApi, depositApi, walletApi, activityApi]);

  const s = statusApi.data;
  const isBookable = s?.is_bookable ?? false;
  const allBlockerCodes = useMemo(() => {
    const set = new Set<string>();
    (s?.visibility_blockers ?? []).forEach((b) => set.add(b.code));
    (s?.bookability_blockers ?? []).forEach((b) => set.add(b.code));
    return set;
  }, [s]);

  const checklist = CHECKLIST_DEFS.map((c) => ({ ...c, done: !allBlockerCodes.has(c.blockerCode) }));
  const doneCount = checklist.filter((c) => c.done).length;
  const setupPct = Math.round((doneCount / checklist.length) * 100);

  const svcNameMap = useMemo(() => {
    const m = new Map<string, string>();
    (svcAvailableApi.data?.services ?? []).forEach((r) => m.set(r.service_id, r.service_name));
    return m;
  }, [svcAvailableApi.data]);

  const enabledSvcList = svcEnabledApi.data?.services ?? [];
  const activeSvc = enabledSvcList.filter((sv) => sv.is_enabled !== false && sv.is_active !== false);

  const areasList = areasApi.data?.areas ?? [];
  const activeAreas = areasList.filter((a) => a.is_active);
  const primaryArea = areasList.find((a) => a.is_primary) ?? activeAreas[0];

  const staffList = staffApi.data?.members ?? [];
  const activeStaff = staffList.filter((m) => m.status === "active");

  const pkg = pkgApi.data;
  const deposit = depositApi.data;
  const wallet = walletApi.data;
  const activityLogs = activityApi.data?.logs ?? [];

  const pill = (v: string) => (
    <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "rgba(255,255,255,0.12)", color: "#fff", border: "1px solid rgba(255,255,255,0.2)" }}>{v}</span>
  );

  return (
    <div>
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div style={{ background: "linear-gradient(135deg,#0f172a 0%,#1e293b 60%,#0f172a 100%)",
        borderRadius: 20, padding: "26px 28px", color: "#fff", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 20 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
              <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }}>{tenantName}</h1>
              {isBookable
                ? pill("Bookable")
                : <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "rgba(232,97,90,0.2)", color: "#FCA5A5", border: "1px solid rgba(252,165,165,0.3)" }}>Not Bookable</span>}
              <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: setupPct === 100 ? "rgba(112,207,160,0.2)" : "rgba(255,180,92,0.2)", color: setupPct === 100 ? "#86EFAC" : "#FDBA74" }}>
                Setup {setupPct}%
              </span>
            </div>
            {primaryArea && (
              <p style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", display: "flex", alignItems: "center", gap: 5, margin: "0 0 6px" }}>
                <MapPin size={12} /> {safeStr(primaryArea.city)}, {safeStr(primaryArea.state)}
              </p>
            )}
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.55)", margin: 0 }}>
              Manage your services, staff, service areas, pricing, package, credits, and setup readiness.
            </p>
          </div>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={13} />} onClick={refreshAll}
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.18)", color: "#fff" }}>
            Refresh
          </Btn>
        </div>

        <div style={{ display: "flex", gap: 32, flexWrap: "wrap", marginTop: 22, paddingTop: 18, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
          {[
            { icon: <Wrench size={12} />, label: "Active Services", value: loading ? "—" : String(activeSvc.length) },
            { icon: <MapPin size={12} />, label: "Service Areas", value: loading ? "—" : `${activeAreas.length} / ${areasList.length || activeAreas.length}` },
            { icon: <Users2 size={12} />, label: "Technicians", value: loading ? "—" : `${activeStaff.length} / ${staffList.length || activeStaff.length}` },
            { icon: <CreditCard size={12} />, label: "Usage Credits", value: walletApi.loading ? "—" : String(safeNum(wallet?.balance)) },
            { icon: <Shield size={12} />, label: "Security Deposit", value: depositApi.loading ? "—" : `₹${safeNum(deposit?.paid_amount ?? deposit?.required_amount)}` },
          ].map((m) => (
            <div key={m.label} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", display: "flex", alignItems: "center", gap: 5 }}>{m.icon}{m.label}</span>
              <span style={{ fontSize: 18, fontWeight: 700 }}>{m.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 24 }}>
        {[
          { icon: <ClipboardCheck size={20} />, label: "Setup Progress", value: `${setupPct}%`, sub: setupPct === 100 ? "Complete" : "In Progress", tone: setupPct === 100 ? "success" as const : "warning" as const },
          { icon: <Wrench size={20} />, label: "Active Services", value: String(activeSvc.length), sub: "Configured", tone: activeSvc.length > 0 ? "success" as const : "default" as const },
          { icon: <Users2 size={20} />, label: "Team", value: `${activeStaff.length} / ${staffList.length || activeStaff.length}`, sub: "Active", tone: activeStaff.length > 0 ? "success" as const : "default" as const },
          { icon: <MapPin size={20} />, label: "Coverage", value: `${activeAreas.length} / ${areasList.length || activeAreas.length}`, sub: "Configured", tone: activeAreas.length > 0 ? "success" as const : "default" as const },
        ].map((k) => (
          <Card key={k.label}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 44, height: 44, borderRadius: 14, background: "var(--accent-muted)", color: "var(--brand)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{k.icon}</div>
              <div>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 3px" }}>{k.label}</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 3px" }}>{loading ? <Skeleton width={50} height={22} /> : k.value}</p>
                <Badge variant={k.tone} size="sm">{k.sub}</Badge>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* ── Main grid ────────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }} className="dash-grid">
        <style>{`@media (max-width: 1024px) { .dash-grid { grid-template-columns: 1fr !important; } }`}</style>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Setup Readiness */}
          <Card>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <ClipboardCheck size={16} color="var(--brand)" /> Setup Readiness
              </h3>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", background: "var(--surface-sunken)", padding: "3px 10px", borderRadius: 999 }}>
                {doneCount} / {checklist.length} complete
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "10px 20px" }}>
              {loading ? Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={18} />) : checklist.map((c) => (
                <a key={c.key} href={c.done ? undefined : c.route} style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none",
                  cursor: c.done ? "default" : "pointer" }}>
                  {c.done
                    ? <CheckCircle2 size={16} color="var(--success)" style={{ flexShrink: 0 }} />
                    : <XCircle size={16} color="var(--danger)" style={{ flexShrink: 0 }} />}
                  <span style={{ fontSize: 13, color: c.done ? "var(--text-primary)" : "var(--text-secondary)" }}>{c.label}</span>
                </a>
              ))}
            </div>
          </Card>

          {/* Enabled Services */}
          <Card padding={0}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px 14px" }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <Wrench size={16} color="var(--brand)" /> Enabled Services
              </h3>
              <a href="/tenant/setup/services" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Manage Services</a>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
                    {["Service Name", "Job Type", "Customer Visible"].map((h) => (
                      <th key={h} style={{ textAlign: "left", padding: "8px 20px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={3} style={{ padding: 20 }}><Skeleton height={16} /></td></tr>
                  ) : activeSvc.length === 0 ? (
                    <tr><td colSpan={3} style={{ padding: "24px 20px", fontSize: 13, color: "var(--text-tertiary)", textAlign: "center" }}>No services enabled yet.</td></tr>
                  ) : activeSvc.map((sv) => (
                    <tr key={sv.tenant_service_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-primary)", fontWeight: 500 }}>
                        {safeStr(sv.tenant_display_name ?? svcNameMap.get(sv.master_service_id), "Service")}
                      </td>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-secondary)", textTransform: "capitalize" }}>{safeStr(sv.job_type)}</td>
                      <td style={{ padding: "10px 20px" }}>
                        {sv.is_active ? <Badge variant="success" size="sm">Visible</Badge> : <Badge variant="default" size="sm">Hidden</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!loading && (
              <p style={{ padding: "12px 20px", fontSize: 12, color: "var(--text-tertiary)", margin: 0, borderTop: "1px solid var(--border)" }}>
                Total {activeSvc.length} service{activeSvc.length === 1 ? "" : "s"}
              </p>
            )}
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Package & Credits */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              <Package size={16} color="var(--brand)" /> Package & Credits
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Usage Credit Balance</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
                  {walletApi.loading ? <Skeleton width={40} height={22} /> : safeNum(wallet?.balance)}
                </p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  {wallet ? `${safeNum(wallet.lifetime_consumed)} consumed lifetime` : ""}
                </p>
                <a href="/finance/usage-credit-ledger" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Ledger <ChevronRight size={12} /></a>
              </div>
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Package</p>
                <p style={{ fontSize: 15, fontWeight: 700, color: pkg?.has_package ? "var(--success-text)" : "var(--warning-text)", margin: "0 0 4px" }}>
                  {pkgApi.loading ? <Skeleton width={100} height={18} /> : safeStr(pkg?.package_name, "No active package")}
                </p>
                <a href="/finance/package" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>Manage Package <ChevronRight size={12} /></a>
              </div>
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Security Deposit</p>
                <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                  {depositApi.loading ? <Skeleton width={60} height={18} /> : `₹${safeNum(deposit?.paid_amount ?? deposit?.required_amount)}`}
                </p>
                <a href="/finance/security-deposit" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Details <ChevronRight size={12} /></a>
              </div>
            </div>
          </Card>

          {/* People & Coverage */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              <Users2 size={16} color="var(--brand)" /> People & Coverage
            </h3>
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 5 }}><Users2 size={12} /> Staff / Technicians</p>
              {staffApi.loading ? <Skeleton height={30} /> : staffList.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No technicians added yet.</p>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{safeStr(staffList[0].full_name)}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, textTransform: "capitalize" }}>{safeStr(staffList[0].designation, staffList[0].member_type)}</p>
                  </div>
                  <Badge variant={staffList[0].status === "active" ? "success" : "default"} size="sm">{staffList[0].status === "active" ? "Active" : "Inactive"}</Badge>
                </div>
              )}
              <a href="/provider/staff" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 6 }}>View All Staff <ChevronRight size={12} /></a>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 5 }}><MapPin size={12} /> Service Areas</p>
              {areasApi.loading ? <Skeleton height={30} /> : areasList.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No service areas added yet.</p>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{safeStr(primaryArea?.city)}, {safeStr(primaryArea?.state)}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{safeStr(primaryArea?.zipcode)}</p>
                  </div>
                  <Badge variant={primaryArea?.is_active ? "success" : "default"} size="sm">{primaryArea?.is_active ? "Active" : "Inactive"}</Badge>
                </div>
              )}
              <a href="/provider/service-areas" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 6 }}>View All Areas <ChevronRight size={12} /></a>
            </div>
          </Card>

          {/* Recent Activity */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              <Clock size={16} color="var(--brand)" /> Recent Activity
            </h3>
            {activityApi.loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={16} />)}</div>
            ) : activityLogs.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No recent activity.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {activityLogs.map((log) => (
                  <div key={log.log_id} style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--brand)", marginTop: 5, flexShrink: 0 }} />
                      <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{humanizeAction(log.action_type)}</span>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{timeAgo(log.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
            <a href="/activity" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 14 }}>View All Activity <ChevronRight size={12} /></a>
          </Card>
        </div>
      </div>

      {/* ── Quick Actions ────────────────────────────────────────────────── */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Quick Actions</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
          {[
            { icon: <ClipboardCheck size={18} />, title: "Complete Setup", desc: "Finish setup checklist to go live", href: "/provider/status" },
            { icon: <Building2 size={18} />, title: "Business Profile", desc: "Update your business information", href: "/profile" },
            { icon: <Plus size={18} />, title: "Add Service Area", desc: "Add coverage locations", href: "/provider/service-areas" },
            { icon: <FileEdit size={18} />, title: "Manage Services", desc: "Enable and configure services", href: "/tenant/setup/services" },
            { icon: <Clock size={18} />, title: "Availability", desc: "Set working hours and breaks", href: "/provider/availability" },
            { icon: <Package size={18} />, title: "Package & Credits", desc: "View usage credits and package", href: "/finance/package" },
          ].map((a) => (
            <a key={a.title} href={a.href} style={{ textDecoration: "none" }}>
              <Card hover onClick={() => { window.location.href = a.href; }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: "var(--accent-muted)", color: "var(--brand)",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{a.icon}</div>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 3px" }}>{a.title}</p>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, lineHeight: 1.4 }}>{a.desc}</p>
                  </div>
                </div>
              </Card>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
