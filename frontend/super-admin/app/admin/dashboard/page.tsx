"use client";
/**
 * Platform Command Center — enterprise Super Admin dashboard.
 * PROVEN: every section reads from dashboardApi (migration 104 + Sprint 28
 * PlatformAnalyticsService reuse) — no mock data.
 * ServiceOS finance rule: Platform Revenue is shown separately from Provider
 * Direct Service Value (what customers pay providers directly) — never
 * combined, never labeled "commission collected".
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { StatCard, Btn, EmptyState, Badge } from "../../../components/shared/ui";
import { PageShell, PageHeader, Card, StatusBadge, Skeleton } from "@serviceos/design-system";
import {
  Building2, Activity, ClipboardCheck, AlertTriangle, ShieldAlert, HeartPulse,
  RefreshCw, Download, FileText, Bell, ListChecks, ScrollText, ShieldCheck,
  TrendingUp, ArrowRight, Wind, XCircle, Copy,
} from "lucide-react";
import { dashboardApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { usePermissions } from "../../../hooks/usePermissions";
import { SUPER_ADMIN_ONLY } from "../../../lib/permission-catalog";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";

// FINAL-L5-05O — dashboard widget permission keys (see permission-catalog.ts).
// Base sections (executive summary, platform health, tenant lifecycle, home
// services, trends, at-risk tenants, trust & quality, category performance)
// require only the base dashboard.read permission every dashboard-capable
// role holds; the domain-sensitive sections below require their own key.
const P_DASHBOARD_FINANCE   = "dashboard.finance.read";
const P_DASHBOARD_OPS       = "dashboard.operations.read";
const P_DASHBOARD_SECURITY  = "dashboard.security.read";
const P_DASHBOARD_EXPORT    = "dashboard.export";
const P_DASHBOARD_ACTIONS   = "dashboard.action_queue.manage";
const P_DASHBOARD_ENGINES   = "dashboard.engine_health.read";
const P_DASHBOARD_ACTIVITY  = "dashboard.activity.read";

const ENGINE_STATUS_BADGE: Record<string, "success"|"warning"|"danger"|"muted"> = {
  healthy: "success", warning: "warning", degraded: "danger", down: "danger",
  disabled: "muted", not_configured: "muted",
};
const RISK_BADGE: Record<string, "danger"|"warning"|"muted"> = {
  critical: "danger", high: "warning",
};

function fmtCurrency(n: number) { return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`; }

const HEALTH_BADGE: Record<string, "success"|"warning"|"danger"|"muted"> = {
  healthy: "success", warning: "warning", critical: "danger", not_configured: "muted",
};
function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

function SectionError({ title, error, requestId, onRetry }: {
  title: string; error: string; requestId?: string | null; onRetry: () => void;
}) {
  return (
    <div style={{ padding: "14px 16px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 10 }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: "var(--danger-text)", margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
        <XCircle size={13}/> {title}
      </p>
      <p style={{ fontSize: 11, color: "var(--danger-text)", margin: "0 0 8px", opacity: 0.85 }}>
        {error} Retry or contact support with the request ID below.
      </p>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={onRetry} style={{ fontSize: 11, fontWeight: 600, padding: "5px 10px", borderRadius: 7, border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
          <RefreshCw size={10}/> Retry
        </button>
        {requestId && (
          <button onClick={() => copyText(requestId)} style={{ fontSize: 11, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
            <Copy size={10}/> Request ID: {requestId}
          </button>
        )}
      </div>
    </div>
  );
}

export default function PlatformCommandCenterPage() {
  const [dateRange, setDateRange] = useState<"7d"|"30d"|"90d">("7d");
  const perm = usePermissions();

  // FINAL-L5-05O Part 5: permission resolves before any restricted request
  // begins. While perm.loading, has() fails closed (false) for every key,
  // so no restricted widget fetch fires before /v1/auth/me resolves.
  const financeAllowed  = perm.has(P_DASHBOARD_FINANCE);
  const opsAllowed      = perm.has(P_DASHBOARD_OPS);
  const securityAllowed = perm.has(P_DASHBOARD_SECURITY);
  const exportAllowed   = perm.has(P_DASHBOARD_EXPORT);
  const actionsAllowed  = perm.has(P_DASHBOARD_ACTIONS);
  const enginesAllowed  = perm.has(P_DASHBOARD_ENGINES);
  const activityAllowed = perm.has(P_DASHBOARD_ACTIVITY);

  const summary   = useApi(useCallback(() => dashboardApi.getExecutiveSummary(), []));
  const health    = useApi(useCallback(() => dashboardApi.getPlatformHealth(), []));
  const finance   = useApi(useCallback(() => dashboardApi.getFinanceSnapshot(), []), [], { enabled: financeAllowed });
  const lifecycle = useApi(useCallback(() => dashboardApi.getTenantLifecycle(), []));
  const ops       = useApi(useCallback(() => dashboardApi.getOperationsSnapshot(), []), [], { enabled: opsAllowed });
  const liveOps   = useApi(useCallback(() => dashboardApi.getLiveOperations(20), []), [], { enabled: opsAllowed });
  const trends    = useApi(useCallback(() => dashboardApi.getTrends(), []));
  const actions   = useApi(useCallback(() => dashboardApi.getActionQueue(50), []), [], { enabled: actionsAllowed });
  const engines   = useApi(useCallback(() => dashboardApi.getEngineHealth(), []), [], { enabled: enginesAllowed });
  const atRisk    = useApi(useCallback(() => dashboardApi.getAtRiskTenants(20), []));
  const compliance= useApi(useCallback(() => dashboardApi.getComplianceSecurity(), []), [], { enabled: securityAllowed });
  const trust     = useApi(useCallback(() => dashboardApi.getTrustQuality(), []));
  const activity  = useApi(useCallback(() => dashboardApi.getActivityFeed(15), []), [], { enabled: activityAllowed });
  const categories= useApi(useCallback(() => dashboardApi.getCategoryPerformance(), []));
  const homeServices = useApi(useCallback(() => dashboardApi.getHomeServicesSummary(), []));

  const resolveAction = useAction(useCallback((id: string) => dashboardApi.resolveAction(id), []));
  const snoozeAction  = useAction(useCallback((id: string) => dashboardApi.snoozeAction(id, 24), []));
  const exportAction  = useAction(useCallback(() => dashboardApi.exportSnapshot(), []));
  const refreshAction = useAction(useCallback(() => dashboardApi.refresh(), []));

  function refetchAll() {
    summary.refetch(); health.refetch(); finance.refetch(); lifecycle.refetch();
    ops.refetch(); liveOps.refetch(); trends.refetch(); actions.refetch();
    engines.refetch(); atRisk.refetch(); compliance.refetch(); trust.refetch();
    activity.refetch(); categories.refetch(); homeServices.refetch();
  }

  async function handleRefresh() { await refreshAction.execute(); refetchAll(); }
  async function handleExport() { await exportAction.execute(); }
  async function handleResolve(id: string) { if (await resolveAction.execute(id)) actions.refetch(); }
  async function handleSnooze(id: string) { if (await snoozeAction.execute(id)) actions.refetch(); }

  const s = summary.data;
  const h = health.data;
  const f = finance.data;
  const l = lifecycle.data;
  const o = ops.data;
  const t = trends.data;

  const loading = summary.loading || health.loading;

  return (
    <AdminLayout activeNav="dashboard">
      <PageShell>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: "-0.75rem" }}>
          Dashboard / Platform Overview
        </div>
        <PageHeader
          title="Platform Command Center"
          description="Monitor ServiceOS health, tenants, operations, finance, trust, compliance, and system engines in real time."
          actions={
            <>
              <Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} loading={refreshAction.loading} onClick={handleRefresh}>Refresh</Btn>
              {/* FINAL-L5-05O Part 6: dashboard quick action requires its own
                  mutation permission (dashboard.export), distinct from any
                  widget read permission -- omitted entirely when denied so it
                  never flashes or renders as a doomed 403 click target. */}
              {exportAllowed && (
                <Btn variant="secondary" size="sm" icon={<Download size={14}/>} loading={exportAction.loading} onClick={handleExport}>Export Snapshot</Btn>
              )}
              <Btn variant="secondary" size="sm" icon={<FileText size={14}/>}>Create Report</Btn>
              <a href="/admin/dashboard#actions" style={{ textDecoration: "none" }}>
                <Btn variant="ghost" size="sm" icon={<Bell size={14}/>}>Open Alerts</Btn>
              </a>
              <a href="/admin/operations" style={{ textDecoration: "none" }}>
                <Btn variant="ghost" size="sm" icon={<ListChecks size={14}/>}>Open Operations Board</Btn>
              </a>
              <a href="/admin/audit-logs" style={{ textDecoration: "none" }}>
                <Btn variant="ghost" size="sm" icon={<ScrollText size={14}/>}>Open Audit Logs</Btn>
              </a>
            </>
          }
        />

        {/* Top row: Executive KPI cards */}
        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 20 }}>
            {[...Array(6)].map((_, i) => <Skeleton key={i} height={120} radius="14px"/>)}
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 20 }}>
            <StatCard label="Platform Health" value={`${h?.score ?? 0} / 100`} icon={<HeartPulse/>}
              change={h?.status} trend={h && h.score >= 90 ? "up" : h && h.score < 60 ? "down" : "neutral"}
              alert={!!h && h.score < 60}/>
            <StatCard label="Active Tenants" value={s?.active_tenants.count ?? 0} icon={<Building2/>}
              change={`+${s?.active_tenants.new_this_month ?? 0} this month · ${s?.active_tenants.bookable ?? 0} bookable`} trend="up"
              onClick={() => { window.location.href = "/admin/tenants"; }}/>
            <StatCard label="Live Operations" value={s?.live_operations.total ?? 0} icon={<Activity/>}
              change={`${s?.live_operations.jobs ?? 0} jobs, ${s?.live_operations.bookings ?? 0} bookings, ${s?.live_operations.leads ?? 0} leads`} trend="neutral"
              onClick={() => { window.location.href = "/admin/operations"; }}/>
            <StatCard label="Pending Admin Actions" value={s?.pending_admin_actions.count ?? 0} icon={<ClipboardCheck/>}
              change="Approvals, disputes, compliance" trend="neutral" alert={(s?.pending_admin_actions.count ?? 0) > 0}/>
            <StatCard label="At-Risk Tenants" value={s?.at_risk_tenants.count ?? 0} icon={<AlertTriangle/>}
              change={`${s?.at_risk_tenants.high_risk ?? 0} high risk`} trend={(s?.at_risk_tenants.count ?? 0) > 0 ? "down" : "neutral"}
              alert={(s?.at_risk_tenants.count ?? 0) > 0}
              onClick={() => { window.location.href = "/admin/tenants?health_band=at_risk"; }}/>
            <StatCard label="Critical Alerts" value={s?.critical_alerts.count ?? 0} icon={<ShieldAlert/>}
              change={(s?.critical_alerts.count ?? 0) > 0 ? "Needs action" : "All clear"} trend="neutral"
              alert={(s?.critical_alerts.count ?? 0) > 0}
              onClick={() => { window.location.href = "/admin/security"; }}/>
          </div>
        )}

        {/* Second row: snapshot cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
          {/* FINAL-L5-05O Part 5/19: perm.loading -> skeleton (never denied
              content, never the section's absence read as final); resolved
              + denied -> section does not render at all (no empty card
              chrome, no doomed-403 flash). */}
          {perm.loading ? (
            <Card padding="md"><Skeleton height={90}/></Card>
          ) : financeAllowed ? (
            <Card padding="md">
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
                letterSpacing: "0.06em", margin: "0 0 12px" }}>Finance Snapshot</p>
              {finance.error ? (
                <SectionError title="We couldn't load finance data" error={finance.error} requestId={finance.requestId} onRetry={finance.refetch}/>
              ) : finance.loading ? <Skeleton height={90}/> : f ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <Row label="Platform Revenue" value={fmtCurrency(f.platform_revenue)} strong/>
                  <Row label="Provider Direct Service Value" value={fmtCurrency(f.provider_direct_service_value)}/>
                  <Row label="Completed Job Deductions" value={fmtCurrency(f.completed_job_deductions)}/>
                  <Row label="Security Deposits Held" value={fmtCurrency(f.security_deposits_held)}/>
                </div>
              ) : null}
            </Card>
          ) : null}
          <Card padding="md">
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
              letterSpacing: "0.06em", margin: "0 0 12px" }}>Tenant Lifecycle</p>
            {lifecycle.error ? (
              <SectionError title="We couldn't load tenant data" error={lifecycle.error} requestId={lifecycle.requestId} onRetry={lifecycle.refetch}/>
            ) : lifecycle.loading ? <Skeleton height={90}/> : l ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {/* pending_review / changes_requested intentionally omitted here --
                    identical counts already shown on /admin/tenants's own KPI row. */}
                <Row label="Bookable" value={String(l.bookable_tenants)}/>
                <Row label="Non-Bookable" value={String(l.non_bookable_tenants)} href="/admin/tenants?bookable_status=not_bookable"/>
                <Row label="View All Tenants" value="→" href="/admin/tenants"/>
              </div>
            ) : null}
          </Card>
          {perm.loading ? (
            <Card padding="md"><Skeleton height={90}/></Card>
          ) : opsAllowed ? (
            <Card padding="md">
              <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
                letterSpacing: "0.06em", margin: "0 0 12px" }}>Operations Snapshot</p>
              {ops.error ? (
                <SectionError title="We couldn't load operations data" error={ops.error} requestId={ops.requestId} onRetry={ops.refetch}/>
              ) : ops.loading ? <Skeleton height={90}/> : o ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <Row label="Live Jobs" value={String(o.live_jobs)}/>
                  <Row label="Today's Bookings" value={String(o.today_bookings)}/>
                  <Row label="Pending Provider Acceptance" value={String(o.pending_provider_acceptance)}/>
                  <Row label="SLA Breaches" value={String(o.sla_breaches)} danger={o.sla_breaches > 0}/>
                </div>
              ) : null}
            </Card>
          ) : null}
          <Card padding="md">
            <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase",
              letterSpacing: "0.06em", margin: "0 0 12px" }}>Trust & Quality</p>
            {trust.error ? (
              <SectionError title="We couldn't load trust & quality data" error={trust.error} requestId={trust.requestId} onRetry={trust.refetch}/>
            ) : trust.loading ? <Skeleton height={90}/> : trust.data ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <Row label="Avg Rating" value={trust.data.avg_rating.toFixed(1)}/>
                <Row label="Complaint Rate" value={`${trust.data.complaint_rate}%`}/>
                <Row label="Dispute Rate" value={`${trust.data.dispute_rate}%`}/>
                <Row label="Providers Under Review" value={String(trust.data.providers_under_review)}/>
              </div>
            ) : null}
          </Card>
        </div>

        {/* Home Services Summary — always its own dedicated section, never
            merged into the generic tenant/operations cards above. */}
        <Card padding="md">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Wind size={16} style={{ color: "var(--accent)" }}/>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Home Services Summary</p>
            </div>
            <a href="/admin/catalog-workspace" style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", textDecoration: "none" }}>
              Open Home Services →
            </a>
          </div>
          {homeServices.error ? (
            <SectionError title="We couldn't load Home Services data" error={homeServices.error} requestId={homeServices.requestId} onRetry={homeServices.refetch}/>
          ) : homeServices.loading ? <Skeleton height={110}/> : homeServices.data ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 16 }}>
                <MiniStat label="Home Services Providers" value={homeServices.data.home_services_providers}/>
                <MiniStat label="Bookable Providers" value={homeServices.data.bookable_providers}/>
                <MiniStat label="Not Bookable Providers" value={homeServices.data.not_bookable_providers}/>
                <MiniStat label="Published Services" value={homeServices.data.published_tenant_services}/>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, marginBottom: 16 }}>
                <HealthRow label="Service Catalog Health" status={homeServices.data.service_catalog_health.status}/>
                <HealthRow label="Pricing Rule Health" status={homeServices.data.pricing_rule_health.status}/>
                <HealthRow label="Service Area Coverage" status={homeServices.data.service_area_coverage_health.status}/>
                <HealthRow label="Provider Matching" status={homeServices.data.provider_matching_health}/>
                <HealthRow label="Auto Price Options" status={homeServices.data.auto_price_options_health}/>
                <HealthRow label="Completed Job Deduction" status={homeServices.data.completed_job_deduction_health}/>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {[
                  { label: "Service Catalog", href: "/admin/catalog-workspace" },
                  { label: "Provider Matching", href: "/admin/home-services/provider-matching" },
                  { label: "Matching Diagnostics", href: "/admin/home-services/matching-diagnostics" },
                  { label: "Service Area Requests", href: "/admin/service-area-requests" },
                  { label: "Completed Job Deduction", href: "/admin/home-services/completed-job-deduction" },
                ].map(l => (
                  <a key={l.href} href={l.href} style={{ fontSize: 11, fontWeight: 600, padding: "6px 12px", borderRadius: 999,
                    border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", textDecoration: "none" }}>
                    {l.label}
                  </a>
                ))}
              </div>
            </>
          ) : null}
        </Card>

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
          {/* Left column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Trends */}
            <Card padding="md">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Platform Revenue Trend</p>
                <div style={{ display: "flex", gap: 4 }}>
                  {(["7d","30d","90d"] as const).map(r => (
                    <button key={r} onClick={() => setDateRange(r)} style={{
                      fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 6, cursor: "pointer",
                      border: dateRange === r ? "1px solid var(--accent)" : "1px solid var(--border)",
                      background: dateRange === r ? "var(--accent-muted)" : "var(--surface)",
                      color: dateRange === r ? "var(--accent)" : "var(--text-tertiary)",
                    }}>{r}</button>
                  ))}
                </div>
              </div>
              {trends.loading ? <Skeleton height={200}/> : !t || t.revenue_trend.length === 0 ? (
                <EmptyState icon={<TrendingUp/>} title="No trend data for this period."
                  description="Try expanding the date range or selecting another vertical."/>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={t.revenue_trend}>
                    <defs>
                      <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="var(--accent)" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
                    <XAxis dataKey="date" tick={{ fontSize: 11 }}/>
                    <YAxis tick={{ fontSize: 11 }}/>
                    <Tooltip formatter={(v: number) => fmtCurrency(v)}/>
                    <Area type="monotone" dataKey="value" stroke="var(--accent)" fill="url(#rev)"/>
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card padding="md">
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 16px" }}>
                Jobs / Bookings / Leads Trend
              </p>
              {trends.loading ? <Skeleton height={200}/> : !t || t.jobs_trend.length === 0 ? (
                <EmptyState icon={<Activity/>} title="No live jobs right now."
                  description="Jobs will appear here when providers accept customer bookings."/>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={t.jobs_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
                    <XAxis dataKey="date" tick={{ fontSize: 11 }}/>
                    <YAxis tick={{ fontSize: 11 }}/>
                    <Tooltip/>
                    <Line type="monotone" dataKey="value" stroke="var(--success)" strokeWidth={2} dot={false}/>
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Live Operations Board */}
            {perm.loading ? (
              <Card padding="none"><div style={{ padding: 16 }}><Skeleton height={100}/></div></Card>
            ) : opsAllowed ? (
              <Card padding="none">
                <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Live Operations Board</p>
                </div>
                {liveOps.loading ? (
                  <div style={{ padding: 16 }}><Skeleton height={100}/></div>
                ) : (liveOps.data?.items ?? []).length === 0 ? (
                  <EmptyState icon={<Activity/>} title="No live jobs right now."
                    description="Jobs will appear here when providers accept customer bookings."/>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)" }}>
                        {["Item","Vertical","Tenant","Status","SLA","Updated"].map(hh => (
                          <th key={hh} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)" }}>{hh}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(liveOps.data?.items ?? []).map((it, i, arr) => (
                        <tr key={it.id} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                          <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{it.item}</td>
                          <td style={{ padding: "10px 16px", fontSize: 12 }}>{it.vertical ?? "—"}</td>
                          <td style={{ padding: "10px 16px", fontSize: 12 }}>{it.tenant ?? "—"}</td>
                          <td style={{ padding: "10px 16px" }}><StatusBadge status={it.status} size="sm"/></td>
                          <td style={{ padding: "10px 16px" }}>{it.sla_breach ? <Badge variant="danger" size="sm">Breach</Badge> : <Badge variant="success" size="sm">OK</Badge>}</td>
                          <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                            {it.updated_at ? new Date(it.updated_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Card>
            ) : null}

            {/* Pending Admin Action Queue -- FINAL-L5-05O Part 6: read
                permission (actionsAllowed via DASHBOARD_ACTION_QUEUE_MANAGE)
                gates the whole panel since this queue's only useful action
                is the mutation itself (resolve/snooze); a read-only variant
                is not a distinct capability in this system today. */}
            {perm.loading ? (
              <Card padding="none"><div style={{ padding: 16 }}><Skeleton height={100}/></div></Card>
            ) : actionsAllowed ? (
              <Card padding="none">
                <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }} id="actions">
                  <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Pending Admin Action Queue</p>
                </div>
                {actions.loading ? (
                  <div style={{ padding: 16 }}><Skeleton height={100}/></div>
                ) : (actions.data?.items ?? []).length === 0 ? (
                  <p style={{ padding: "28px 20px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>
                    No pending actions. Everything is on track.
                  </p>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)" }}>
                        {["Priority","Action","Vertical","Status","Actions"].map(hh => (
                          <th key={hh} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)" }}>{hh}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(actions.data?.items ?? []).map((a, i, arr) => (
                        <tr key={a.action_id} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                          <td style={{ padding: "10px 16px" }}>
                            <Badge variant={a.priority === "critical" ? "danger" : "warning"} size="sm">{a.priority}</Badge>
                          </td>
                          <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-primary)" }}>{a.action}</td>
                          <td style={{ padding: "10px 16px", fontSize: 12 }}>{a.vertical ?? "—"}</td>
                          <td style={{ padding: "10px 16px" }}><StatusBadge status={a.status} size="sm"/></td>
                          <td style={{ padding: "10px 16px" }}>
                            <div style={{ display: "flex", gap: 6 }}>
                              <Btn size="xs" variant="secondary" loading={resolveAction.loading} onClick={() => handleResolve(a.action_id)}>Resolve</Btn>
                              <Btn size="xs" variant="ghost" loading={snoozeAction.loading} onClick={() => handleSnooze(a.action_id)}>Snooze</Btn>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Card>
            ) : null}
          </div>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Engine Health */}
            {perm.loading ? (
              <Card padding="md"><Skeleton height={120}/></Card>
            ) : enginesAllowed ? (
              <Card padding="md">
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>System / Engine Health</p>
                {engines.loading ? <Skeleton height={120}/> : (
                  <>
                    {(engines.data?.items ?? []).map(e => (
                      <div key={e.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{e.name}</span>
                        <Badge variant={ENGINE_STATUS_BADGE[e.status] ?? "muted"} size="sm">{e.status.replace(/_/g," ")}</Badge>
                      </div>
                    ))}
                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "10px 0 0" }}>{engines.data?.note}</p>
                  </>
                )}
              </Card>
            ) : null}

            {/* At-Risk Tenants */}
            <Card padding="md">
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>At-Risk Tenants</p>
              {atRisk.loading ? <Skeleton height={100}/> : (atRisk.data?.items ?? []).length === 0 ? (
                <EmptyState icon={<ShieldCheck/>} title="No at-risk tenants."
                  description="All tenant health signals are within safe limits."/>
              ) : (atRisk.data?.items ?? []).map(t2 => (
                <a key={t2.tenant_id} href={`/admin/tenants/${t2.tenant_id}`} style={{ textDecoration: "none" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{t2.tenant_name}</p>
                      <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{t2.top_reason}</p>
                    </div>
                    <Badge variant={RISK_BADGE[t2.risk_level] ?? "warning"} size="sm">{t2.risk_level}</Badge>
                  </div>
                </a>
              ))}
            </Card>

            {/* Compliance & Security */}
            {perm.loading ? (
              <Card padding="md"><Skeleton height={100}/></Card>
            ) : securityAllowed ? (
              <Card padding="md">
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Compliance & Security</p>
                {/* Data Export/Deletion Requests, Open Threats, and Failed
                    Logins intentionally omitted here -- identical counts
                    already shown on /admin/compliance and /admin/security's
                    own summary cards. DPDP Requests Pending is a genuine
                    aggregate (sums multiple request types) not shown
                    anywhere else, so it stays. */}
                {compliance.loading ? <Skeleton height={40}/> : compliance.data && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <Row label="DPDP Requests Pending" value={String(compliance.data.dpdp_requests_pending)}/>
                  </div>
                )}
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <Btn size="xs" variant="ghost" onClick={() => { window.location.href = "/admin/compliance"; }}>Open Compliance</Btn>
                  <Btn size="xs" variant="ghost" onClick={() => { window.location.href = "/admin/security"; }}>Open Security</Btn>
                </div>
              </Card>
            ) : null}

            {/* Recent Activity */}
            {perm.loading ? (
              <Card padding="md"><Skeleton height={100}/></Card>
            ) : activityAllowed ? (
              <Card padding="md">
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Recent Activity</p>
                {activity.loading ? <Skeleton height={100}/> : (activity.data?.items ?? []).length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No activity yet.</p>
                ) : (activity.data?.items ?? []).map(ev => (
                  <div key={ev.id} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0 }}>{ev.action.replace(/[._]/g," ")}</p>
                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {ev.time ? new Date(ev.time).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : ""}
                    </p>
                  </div>
                ))}
              </Card>
            ) : null}
          </div>
        </div>

        {/* Bottom: Category Performance + Quick Links */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
          <Card padding="none">
            <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Category Performance</p>
            </div>
            {categories.loading ? (
              <div style={{ padding: 16 }}><Skeleton height={100}/></div>
            ) : (categories.data?.items ?? []).length === 0 ? (
              <p style={{ padding: "28px 20px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, margin: 0 }}>
                No category performance data yet.
              </p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Vertical","Tenants","Bookings","Avg Rating","Complaint Rate"].map(hh => (
                      <th key={hh} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)" }}>{hh}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(categories.data?.items ?? []).map((c, i, arr) => (
                    <tr key={c.vertical_key} style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding: "10px 16px", fontSize: 12, fontWeight: 600 }}>{c.category_name}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{c.tenant_count}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{c.booking_count}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{c.avg_rating.toFixed(1)}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>{c.complaint_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card padding="md">
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Quick Links</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {/* FINAL-L5-05O Part 9: each link appears only if perm.has()
                  resolves the DESTINATION route's own required permission
                  (matching NAV_GROUPS -- see AdminLayout.tsx), not this
                  page's permission. perm.loading -> [] (no flash of a link
                  the user turns out not to have). */}
              {(perm.loading ? [] : [
                { label: "Tenant Approvals", href: "/admin/tenants?status=pending_review", count: l?.pending_review, requires: "tenant:read" },
                { label: "Live Operations", href: "/admin/operations", requires: "admin:jobs:read" },
                { label: "Finance Summary", href: "/admin/finance", requires: "finance:hub:read" },
                { label: "Completed Job Deductions", href: "/admin/home-services/completed-job-deduction", requires: "finance:hub:read" },
                { label: "Customer Service Credits", href: "/admin/finance/customer-credits", requires: "finance:hub:read" },
                { label: "Complaints & Disputes", href: "/admin/complaints", requires: SUPER_ADMIN_ONLY },
                { label: "Security Center", href: "/admin/security", requires: "security:read" },
                { label: "Engine Health", href: "/admin/engines", requires: SUPER_ADMIN_ONLY },
              ]).filter(link =>
                link.requires === SUPER_ADMIN_ONLY ? perm.role === "super_admin" : perm.has(link.requires)
              ).map(link => (
                <a key={link.label} href={link.href} style={{ textDecoration: "none" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "8px 12px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                    <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{link.label}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      {link.count != null && <Badge variant="info" size="sm">{link.count}</Badge>}
                      <ArrowRight size={12} color="var(--text-tertiary)"/>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </Card>
        </div>
      </PageShell>
    </AdminLayout>
  );
}

function Row({ label, value, strong, danger, href }: { label: string; value: string; strong?: boolean; danger?: boolean; href?: string }) {
  const content = (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: danger ? "var(--danger-text)" : "var(--text-primary)", fontWeight: strong ? 700 : 500 }}>{value}</span>
    </div>
  );
  return href ? <a href={href} style={{ textDecoration: "none" }}>{content}</a> : content;
}

function MiniStat({ label, value }: { label: string; value: number | null | undefined }) {
  const safeValue = (typeof value === "number" && isFinite(value)) ? value : 0;
  return (
    <div style={{ padding: "10px 12px", borderRadius: 9, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-tertiary)", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{safeValue}</p>
    </div>
  );
}

function HealthRow({ label, status }: { label: string; status: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", borderRadius: 7, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
      <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</span>
      <Badge variant={HEALTH_BADGE[status] ?? "muted"} size="sm">{status.replace(/_/g, " ")}</Badge>
    </div>
  );
}
