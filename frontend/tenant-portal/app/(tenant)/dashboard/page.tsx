"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Wrench, Users2, MapPin, CreditCard, Package, Shield, RefreshCw,
  ClipboardCheck, ChevronRight, Building2,
  FileEdit, Plus, Clock,
} from "lucide-react";
import {
  providerServiceAreasApi, providerTeamMembersApi,
  masterCatalogApi, myStatusApi,
  type ProviderServiceArea, type TenantEnabledService,
  type ProviderTeamMember, type AdminMasterServiceRow,
  type PackageAssignmentSummary, type TenantSecurityDepositStatus, type TenantCreditWalletDetail,
  type TenantStatusAuditLogEntry,
} from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { useSetupStatus } from "../../../hooks/useSetupStatus";
import { SetupWizardDrawer } from "../../../components/layout/TenantLayout";
import { PageHeader, Card, Button, StatCard } from "@serviceos/design-system";
import { Badge, Skeleton } from "../../../components/shared/ui";

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

export default function DashboardPage() {
  const [tenantName, setTenantName] = useState("Your Business");
  const [wizardOpen, setWizardOpen] = useState(false);
  // Shared hook (also used by TenantLayout's nav filtering and the Profile
  // page's "Business Setup" section) -- first-time banner only, so it must
  // not render once every real step is done.
  const setupStatus = useSetupStatus();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const n = localStorage.getItem("serviceos_tenant_name");
      if (n) setTenantName(n);
    }
  }, []);

  const svcEnabledApi = useApi<{ services: TenantEnabledService[] }>(useCallback(() => masterCatalogApi.listEnabled(), []), []);
  const svcAvailableApi = useApi<{ services: AdminMasterServiceRow[] }>(useCallback(() => masterCatalogApi.listAvailable(), []), []);
  const areasApi = useApi<{ areas: ProviderServiceArea[]; total: number }>(useCallback(() => providerServiceAreasApi.list(), []), []);
  const staffApi = useApi<{ members: ProviderTeamMember[]; count: number }>(useCallback(() => providerTeamMembersApi.list(), []), []);
  const pkgApi = useApi<PackageAssignmentSummary>(useCallback(() => myStatusApi.getPackageSummary(), []), []);
  const depositApi = useApi<TenantSecurityDepositStatus>(useCallback(() => myStatusApi.getSecurityDeposit(), []), []);
  const walletApi = useApi<TenantCreditWalletDetail>(useCallback(() => myStatusApi.getCreditWallet(), []), []);
  const activityApi = useApi<{ logs: TenantStatusAuditLogEntry[] }>(useCallback(() => myStatusApi.getAuditLog(6), []), []);

  const loading = setupStatus.loading || svcEnabledApi.loading || areasApi.loading || staffApi.loading;

  const refreshAll = useCallback(() => {
    setupStatus.refetch(); svcEnabledApi.refetch(); svcAvailableApi.refetch();
    areasApi.refetch(); staffApi.refetch(); pkgApi.refetch(); depositApi.refetch();
    walletApi.refetch(); activityApi.refetch();
  }, [setupStatus, svcEnabledApi, svcAvailableApi, areasApi, staffApi, pkgApi, depositApi, walletApi, activityApi]);

  // Setup readiness now comes from the single canonical useSetupStatus hook
  // (also used by TenantLayout's nav filtering, the Profile page, and the
  // SetupWizardDrawer below) instead of a second, hand-rolled 8-step
  // checklist independently computed from the same blockers -- avoids the
  // two counts ever disagreeing.
  const isBookable = setupStatus.isBookable;
  const doneCount = setupStatus.doneCount;
  const setupPct = setupStatus.total > 0 ? Math.round((setupStatus.doneCount / setupStatus.total) * 100) : 0;

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

  const pill = (v: string, tone: "success" | "warning" | "danger" = "success") => (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999,
      background: `var(--${tone}-bg)`, color: `var(--${tone}-text)`, border: `1px solid var(--${tone}-border)`,
    }}>{v}</span>
  );

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <PageHeader title="Dashboard" description={`${tenantName} — services, staff, service areas, pricing, package, credits, and setup readiness.`} />
      </div>

      {/* ── First-time setup banner ─────────────────────────────────────────
          Shown only while setup is incomplete (via the shared hook's 10-step
          isComplete). Once complete, this never renders -- setup access then
          lives permanently on the Profile page's "Business Setup" section. */}
      {!setupStatus.loading && !setupStatus.error && !setupStatus.isComplete && (
        <Card style={{ marginBottom: 20, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 44, height: 44, borderRadius: "var(--radius-lg)", background: "var(--warning)", color: "white",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <ClipboardCheck size={20} />
              </div>
              <div>
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 3px" }}>Finish setting up your business</p>
                <p style={{ fontSize: 13, color: "var(--warning-text)", margin: 0, opacity: 0.85 }}>
                  {setupStatus.doneCount} of {setupStatus.total} setup steps complete — finish the rest to go live and accept bookings.
                </p>
              </div>
            </div>
            <Button variant="primary" size="sm" onClick={() => setWizardOpen(true)}>Continue Setup</Button>
          </div>
        </Card>
      )}
      <SetupWizardDrawer open={wizardOpen} onClose={() => setWizardOpen(false)} />

      {/* ── Identity strip ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 24 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>{tenantName}</h1>
            {isBookable ? pill("Bookable", "success") : pill("Not Bookable", "danger")}
            {pill(`Setup ${setupPct}%`, setupPct === 100 ? "success" : "warning")}
          </div>
          {primaryArea && (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 5, margin: 0 }}>
              <MapPin size={12} /> {safeStr(primaryArea.city)}, {safeStr(primaryArea.state)}
            </p>
          )}
        </div>
        <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={13} />} onClick={refreshAll}>
          Refresh
        </Button>
      </div>

      {/* ── KPI cards — one consolidated row, each metric shown exactly once ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 }}>
        <StatCard icon={ClipboardCheck} label="Setup Progress" tone={setupPct === 100 ? "success" : "warning"}
          value={loading ? <Skeleton width={40} height={22} /> : `${setupPct}%`}
          change={{ value: setupPct === 100 ? "Complete" : "In progress", direction: setupPct === 100 ? "up" : "flat" }} />
        <StatCard icon={Wrench} label="Active Services" tone="brand"
          value={loading ? <Skeleton width={30} height={22} /> : String(activeSvc.length)}
          change={{ value: "Configured", direction: "flat" }} />
        <StatCard icon={Users2} label="Team" tone="brand"
          value={loading ? <Skeleton width={40} height={22} /> : `${activeStaff.length} / ${staffList.length || activeStaff.length}`}
          change={{ value: "Active", direction: "flat" }} />
        <StatCard icon={MapPin} label="Coverage" tone="brand"
          value={loading ? <Skeleton width={40} height={22} /> : `${activeAreas.length} / ${areasList.length || activeAreas.length}`}
          change={{ value: "Service areas", direction: "flat" }} />
        <StatCard icon={CreditCard} label="Usage Credits" tone="info"
          value={walletApi.loading ? <Skeleton width={30} height={22} /> : String(safeNum(wallet?.balance))}
          change={wallet ? { value: `${safeNum(wallet.lifetime_consumed)} consumed`, direction: "flat" } : undefined} />
        <StatCard icon={Shield} label="Security Deposit" tone="info"
          value={depositApi.loading ? <Skeleton width={40} height={22} /> : `₹${safeNum(deposit?.paid_amount ?? deposit?.required_amount)}`} />
      </div>

      {/* ── Main grid ────────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }} className="dash-grid">
        <style>{`@media (max-width: 1024px) { .dash-grid { grid-template-columns: 1fr !important; } }`}</style>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Setup Readiness -- summary only; the full step-by-step
              checklist lives in one place, the SetupWizardDrawer (opened
              from here or from the banner above), instead of being
              re-rendered a second time on this page. */}
          <Card>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 8 }}>
                  <ClipboardCheck size={16} color="var(--brand)" /> Setup Readiness
                </h3>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                  {loading ? <Skeleton width={140} height={16} /> : `${doneCount} of ${setupStatus.total} steps complete`}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setWizardOpen(true)}>Review Checklist</Button>
            </div>
          </Card>

          {/* Enabled Services */}
          <Card padding="none">
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
                {/* FINAL-L5-03: <div> not <p> -- Skeleton renders a <div>,
                    invalid inside a <p> and caused a real hydration mismatch. */}
                <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
                  {walletApi.loading ? <Skeleton width={40} height={22} /> : safeNum(wallet?.balance)}
                </div>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  {wallet ? `${safeNum(wallet.lifetime_consumed)} consumed lifetime` : ""}
                </p>
                <a href="/finance/usage-credit-ledger" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Ledger <ChevronRight size={12} /></a>
              </div>
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Package</p>
                <div style={{ fontSize: 15, fontWeight: 700, color: pkg?.has_package ? "var(--success-text)" : "var(--warning-text)", margin: "0 0 4px" }}>
                  {pkgApi.loading ? <Skeleton width={100} height={18} /> : safeStr(pkg?.package_name, "No active package")}
                </div>
                <a href="/finance/package" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>Manage Package <ChevronRight size={12} /></a>
              </div>
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Security Deposit</p>
                <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                  {depositApi.loading ? <Skeleton width={60} height={18} /> : `₹${safeNum(deposit?.paid_amount ?? deposit?.required_amount)}`}
                </div>
                <a href="/finance/security-deposit" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Details <ChevronRight size={12} /></a>
              </div>
            </div>
          </Card>

          {/* People & Coverage */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              <Users2 size={16} color="var(--brand)" /> People & Coverage
            </h3>
            {/* Staff count already shown in the "Team" KPI card above, and
                primary area location already shown in the identity strip --
                this card links out rather than re-displaying either. */}
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 5 }}><Users2 size={12} /> Staff / Technicians</p>
              {staffApi.loading ? <Skeleton height={20} /> : staffList.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No technicians added yet.</p>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{activeStaff.length} active of {staffList.length} total</p>
              )}
              <a href="/provider/staff" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 6 }}>View All Staff <ChevronRight size={12} /></a>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 5 }}><MapPin size={12} /> Service Areas</p>
              {areasApi.loading ? <Skeleton height={20} /> : areasList.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No service areas added yet.</p>
              ) : (
                <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0 }}>{activeAreas.length} active of {areasList.length} total</p>
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
            { icon: <Building2 size={18} />, title: "Business Profile", desc: "Update your business information", href: "/profile" },
            { icon: <Plus size={18} />, title: "Add Service Area", desc: "Add coverage locations", href: "/provider/service-areas" },
            { icon: <FileEdit size={18} />, title: "Manage Services", desc: "Enable and configure services", href: "/tenant/setup/services" },
            { icon: <Clock size={18} />, title: "Availability", desc: "Set working hours and breaks", href: "/provider/availability" },
            { icon: <Package size={18} />, title: "Package & Credits", desc: "View usage credits and package", href: "/finance/package" },
          ].map((a) => (
            <a key={a.title} href={a.href} style={{ textDecoration: "none" }}>
              <Card onClick={() => { window.location.href = a.href; }} style={{ cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: "var(--radius-md)", background: "var(--accent-muted)", color: "var(--brand)",
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
