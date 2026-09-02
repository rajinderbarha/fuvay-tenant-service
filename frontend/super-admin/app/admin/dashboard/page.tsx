"use client";
import { TableSurface } from "@serviceos/design-system";

/**
 * Fuvay platform command center. All values come from dashboardApi; there is
 * no mock data. Expensive domain panels are loaded only when their URL-backed
 * workspace is opened, keeping the executive landing view small at scale.
 *
 * Compatibility note: this replaces the old description "Monitor ServiceOS
 * health, tenants, operations, finance, trust, compliance, and system engines
 * in real time." while retaining the same permission boundaries.
 */
import Link from "next/link";
import React, { useCallback, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, ArrowRight, Banknote, BellRing, Building2,
  CalendarClock, CheckCircle2, ClipboardCheck, Download, ExternalLink,
  FileBarChart, HeartPulse, History, ListChecks, RefreshCw,
  Search, ShieldAlert, ShieldCheck, Sparkles, UsersRound, Wrench,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Badge, Btn, Card, Skeleton, SummaryCard } from "../../../components/shared/ui";
import { PageHeader } from "@serviceos/design-system";
import { dashboardApi, type DashboardActionItem, type DashboardTrendPoint } from "../../../lib/api";
import { useAction, useApi } from "../../../hooks/useApi";
import { usePermissions } from "../../../hooks/usePermissions";
import { SUPER_ADMIN_ONLY } from "../../../lib/permission-catalog";
import styles from "./dashboard.module.css";

type Tab = "overview" | "operations" | "providers" | "finance" | "platform";
type Range = "7d" | "30d" | "90d";

const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
  { id: "overview", label: "Overview", icon: <Sparkles size={15}/> },
  { id: "operations", label: "Operations", icon: <ListChecks size={15}/> },
  { id: "providers", label: "Providers", icon: <Building2 size={15}/> },
  { id: "finance", label: "Finance", icon: <Banknote size={15}/> },
  { id: "platform", label: "Platform & risk", icon: <ShieldCheck size={15}/> },
];

const P_FINANCE = "dashboard.finance.read";
const P_OPS = "dashboard.operations.read";
const P_SECURITY = "dashboard.security.read";
const P_EXPORT = "dashboard.export";
const P_ACTIONS = "dashboard.action_queue.manage";
const P_ENGINES = "dashboard.engine_health.read";
const P_ACTIVITY = "dashboard.activity.read";

function formatCurrency(value: number) {
  return `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function rangeParams(range: Range) {
  const days = Number(range.slice(0, -1));
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - days + 1);
  return { date_from: start.toISOString().slice(0, 10), date_to: end.toISOString().slice(0, 10), vertical: "home_services" };
}

function chooseInitialTab(): Tab {
  if (typeof window === "undefined") return "overview";
  const candidate = new URLSearchParams(window.location.search).get("tab") as Tab | null;
  return candidate && TABS.some(tab => tab.id === candidate) ? candidate : "overview";
}

/** The dashboard used to render its own CSS-module KPI card, which is why its
 *  tiles never matched the rest of the admin. It is now an adapter onto the
 *  single canonical card: `note` is the shared `sub`, `href` navigates through
 *  the card itself (a real <a>, so middle-click still works), and "default"
 *  maps to no tone rather than a fourth colour. */
function Kpi({ label, value, note, icon, tone = "default", href, id }: {
  label: string; value: React.ReactNode; note: string; icon: React.ReactNode;
  tone?: "default" | "success" | "warning" | "danger"; href?: string; id?: string;
}) {
  return (
    <div id={id} style={{ minWidth: 0 }}>
      <SummaryCard
        label={label}
        value={value}
        sub={note}
        icon={icon}
        tone={tone === "default" ? undefined : tone}
        href={href}
      />
    </div>
  );
}

function SectionTitle({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return <div className={styles.sectionTitle}><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>;
}

function SectionError({ title, error, requestId, onRetry }: { title: string; error: string; requestId?: string | null; onRetry: () => void }) {
  return <div className={styles.errorBox} role="alert"><ShieldAlert size={18}/><div><strong>{title}</strong><p>{error}</p>{requestId && <code>Request ID: {requestId}</code>}</div><Btn size="xs" variant="secondary" onClick={onRetry}>Retry</Btn></div>;
}

function RangeControl({ value, onChange }: { value: Range; onChange: (value: Range) => void }) {
  return <div className={styles.segmented} aria-label="Reporting period">{(["7d", "30d", "90d"] as Range[]).map(range =>
    <button key={range} type="button" aria-pressed={value === range} className={value === range ? styles.segmentActive : ""} onClick={() => onChange(range)}>{range}</button>
  )}</div>;
}

function MetricRows({ rows }: { rows: Array<{ label: string; value: React.ReactNode; danger?: boolean; href?: string }> }) {
  return <div className={styles.metricRows}>{rows.map(row => {
    const content = <><span>{row.label}</span><strong className={row.danger ? styles.dangerText : ""}>{row.value}</strong></>;
    return row.href ? <Link key={row.label} href={row.href} className={styles.metricRow}>{content}</Link> : <div key={row.label} className={styles.metricRow}>{content}</div>;
  })}</div>;
}

function DataTable({ headers, children, empty }: { headers: string[]; children: React.ReactNode; empty?: boolean }) {
  return <div className={styles.tableWrap}><TableSurface><thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{empty ? <tr><td colSpan={headers.length} className={styles.tableEmpty}>No records match this workspace.</td></tr> : children}</tbody></TableSurface></div>;
}

function Chart({ data, kind = "area", color = "var(--text-link)", currency = false }: { data: DashboardTrendPoint[]; kind?: "area" | "line"; color?: string; currency?: boolean }) {
  if (!data.length) return <div className={styles.chartEmpty}><FileBarChart size={23}/><strong>No trend data for this period.</strong><span>Data will appear when native Home Services activity is recorded.</span></div>;
  const common = <><CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/><XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={value => value.slice(5)}/><YAxis tick={{ fontSize: 10 }} width={currency ? 56 : 35}/><Tooltip formatter={(value: number) => currency ? formatCurrency(value) : value.toLocaleString("en-IN")}/></>;
  return <ResponsiveContainer width="100%" height={245}>{kind === "line" ? <LineChart data={data}>{common}<Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.4} dot={false}/></LineChart> : <AreaChart data={data}><defs><linearGradient id={`fill-${currency ? "money" : "count"}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.3}/><stop offset="100%" stopColor={color} stopOpacity={0.02}/></linearGradient></defs>{common}<Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.2} fill={`url(#fill-${currency ? "money" : "count"})`}/></AreaChart>}</ResponsiveContainer>;
}

function ActionQueue({ items, loading, onResolve, onSnooze, busy }: { items: DashboardActionItem[]; loading: boolean; onResolve: (id: string) => void; onSnooze: (id: string) => void; busy: boolean }) {
  if (loading) return <div className={styles.loadingRows}><Skeleton height={52}/><Skeleton height={52}/><Skeleton height={52}/></div>;
  if (!items.length) return <div className={styles.positiveEmpty}><CheckCircle2 size={28}/><strong>No pending actions. Everything is on track.</strong><span>Escalations and approval work will appear here automatically.</span></div>;
  return <div className={styles.actionList}>{items.map(item => <div className={styles.actionItem} key={item.action_id}>
    <span className={`${styles.priorityMark} ${item.priority === "critical" ? styles.priorityCritical : styles.priorityHigh}`}/>
    <div className={styles.actionCopy}><div><Badge variant={item.priority === "critical" ? "danger" : "warning"}>{item.priority}</Badge><span>{item.entity_type?.replaceAll("_", " ") || "platform"}</span></div><strong>{item.action}</strong><small>{item.vertical?.replaceAll("_", " ") || "Home Services"}</small></div>
    <div className={styles.actionButtons}><Btn size="xs" variant="secondary" disabled={busy} onClick={() => onSnooze(item.action_id)}>Snooze 24h</Btn><Btn size="xs" disabled={busy} onClick={() => onResolve(item.action_id)}>Resolve</Btn></div>
  </div>)}</div>;
}

export default function PlatformCommandCenterPage() {
  const [tab, setTab] = useState<Tab>(chooseInitialTab);
  const [range, setRange] = useState<Range>("30d");
  const [operationSearch, setOperationSearch] = useState("");
  const [notice, setNotice] = useState("");
  const permissions = usePermissions();
  const financeAllowed = permissions.has(P_FINANCE), opsAllowed = permissions.has(P_OPS);
  const securityAllowed = permissions.has(P_SECURITY), exportAllowed = permissions.has(P_EXPORT);
  const actionsAllowed = permissions.has(P_ACTIONS), enginesAllowed = permissions.has(P_ENGINES);
  const activityAllowed = permissions.has(P_ACTIVITY);
  const period = useMemo(() => rangeParams(range), [range]);

  const summary = useApi(useCallback(() => dashboardApi.getExecutiveSummary(), []), []);
  const health = useApi(useCallback(() => dashboardApi.getPlatformHealth(), []), []);
  const home = useApi(useCallback(() => dashboardApi.getHomeServicesSummary(), []), [], { enabled: tab === "overview" });
  const trends = useApi(useCallback(() => dashboardApi.getTrends(period), [period]), [period], { enabled: tab === "overview" || tab === "finance" });
  const actions = useApi(useCallback(() => dashboardApi.getActionQueue(50), []), [], { enabled: actionsAllowed && (tab === "overview" || tab === "operations") });
  const activity = useApi(useCallback(() => dashboardApi.getActivityFeed(12), []), [], { enabled: activityAllowed && tab === "overview" });
  const operations = useApi(useCallback(() => dashboardApi.getOperationsSnapshot("home_services"), []), [], { enabled: opsAllowed && tab === "operations" });
  const liveOperations = useApi(useCallback(() => dashboardApi.getLiveOperations(50), []), [], { enabled: opsAllowed && tab === "operations" });
  const lifecycle = useApi(useCallback(() => dashboardApi.getTenantLifecycle(), []), [], { enabled: tab === "providers" });
  const atRisk = useApi(useCallback(() => dashboardApi.getAtRiskTenants(50), []), [], { enabled: tab === "providers" });
  const finance = useApi(useCallback(() => dashboardApi.getFinanceSnapshot(period), [period]), [period], { enabled: financeAllowed && tab === "finance" });
  const engines = useApi(useCallback(() => dashboardApi.getEngineHealth(), []), [], { enabled: enginesAllowed && tab === "platform" });
  const compliance = useApi(useCallback(() => dashboardApi.getComplianceSecurity(), []), [], { enabled: securityAllowed && tab === "platform" });
  const trust = useApi(useCallback(() => dashboardApi.getTrustQuality(), []), [], { enabled: tab === "platform" });
  const categories = useApi(useCallback(() => dashboardApi.getCategoryPerformance(period), [period]), [period], { enabled: tab === "platform" });

  const resolveAction = useAction(useCallback((id: string) => dashboardApi.resolveAction(id), []));
  const snoozeAction = useAction(useCallback((id: string) => dashboardApi.snoozeAction(id, 24), []));
  const exportAction = useAction(useCallback(() => dashboardApi.exportSnapshot(), []));
  const refreshAction = useAction(useCallback(() => dashboardApi.refresh(), []));

  function selectTab(next: Tab) { setTab(next); setNotice(""); const url = new URL(window.location.href); url.searchParams.set("tab", next); window.history.replaceState({}, "", url); }
  async function refresh() {
    const result = await refreshAction.execute(); if (!result) return;
    summary.refetch(); health.refetch();
    ({ overview: [home, trends, actions, activity], operations: [operations, liveOperations, actions], providers: [lifecycle, atRisk], finance: [finance, trends], platform: [engines, compliance, trust, categories] }[tab]).forEach(item => item.refetch());
    setNotice(`Dashboard refreshed at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
  }
  async function exportSnapshot() { const result = await exportAction.execute(); if (result) setNotice(`Snapshot ${result.snapshot_id.slice(0, 8)} saved to the audited export history.`); }
  async function resolve(id: string) { if (await resolveAction.execute(id)) actions.refetch(); }
  async function snooze(id: string) { if (await snoozeAction.execute(id)) actions.refetch(); }
  function moveTab(event: React.KeyboardEvent<HTMLButtonElement>, current: Tab) {
    const currentIndex = TABS.findIndex(item => item.id === current);
    let nextIndex = currentIndex;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % TABS.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = TABS.length - 1;
    else return;
    event.preventDefault();
    const next = TABS[nextIndex].id;
    selectTab(next);
    requestAnimationFrame(() => document.getElementById(`dashboard-tab-${next}`)?.focus());
  }

  const s = summary.data, h = health.data;
  const visibleOperations = (liveOperations.data?.items ?? []).filter(item => !operationSearch || `${item.item} ${item.tenant} ${item.status}`.toLowerCase().includes(operationSearch.toLowerCase()));
  const restrictedTab = (tab === "finance" && !permissions.loading && !financeAllowed) || (tab === "operations" && !permissions.loading && !opsAllowed);

  return <AdminLayout activeNav="dashboard"><main className={styles.page}>
    <PageHeader
      eyebrow="Platform command center"
      context="Home Services"
      title={`Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}, Super Admin`}
      description="One operational view of provider readiness, native bookings, completion charges, customer trust, and platform controls."
      actions={<div className={styles.heroActions}><Btn variant="secondary" size="sm" loading={refreshAction.loading} onClick={refresh}><RefreshCw size={14}/>Refresh</Btn>{exportAllowed && <Btn variant="secondary" size="sm" loading={exportAction.loading} onClick={exportSnapshot}><Download size={14}/>Export Snapshot</Btn>}<Link href="/admin/analytics?tab=reports"><Btn size="sm"><FileBarChart size={14}/>Reports</Btn></Link></div>}
    />
    <div className={styles.contextBar}><div><span className={`${styles.liveDot} ${h?.status === "healthy" ? styles.live : ""}`}/><strong>{h?.status === "healthy" ? "All core controls operational" : `${h?.status || "Checking"} platform state`}</strong><span>{h?.reasons?.[0] || "Verifying live controls"}</span></div><div><CalendarClock size={14}/><span>{notice || "Live data · refreshed on demand"}</span></div></div>
    <nav className={styles.tabs} aria-label="Dashboard workspaces" role="tablist">{TABS.map(item => <button type="button" role="tab" id={`dashboard-tab-${item.id}`} aria-controls="dashboard-active-panel" aria-selected={tab === item.id} tabIndex={tab === item.id ? 0 : -1} key={item.id} onClick={() => selectTab(item.id)} onKeyDown={event => moveTab(event, item.id)} className={tab === item.id ? styles.activeTab : ""}>{item.icon}{item.label}{item.id === "operations" && (s?.pending_admin_actions.count ?? 0) > 0 && <span>{s?.pending_admin_actions.count}</span>}</button>)}</nav>

    {summary.loading || health.loading ? <div className={styles.kpiGrid}>{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={126}/>)}</div> : <div className={styles.kpiGrid}>
      <Kpi label="Platform Health" value={`${h?.score ?? 0}/100`} note={(h?.status || "unknown").replaceAll("_", " ")} icon={<HeartPulse size={18}/>} tone={(h?.score ?? 0) >= 90 ? "success" : (h?.score ?? 0) >= 70 ? "warning" : "danger"}/>
      <Kpi label="Active Tenants" value={s?.active_tenants.count ?? 0} note={`${s?.active_tenants.bookable ?? 0} customer-bookable providers`} icon={<Building2 size={18}/>} href="/admin/home-services/providers"/>
      <Kpi label="Live Operations" value={s?.live_operations.jobs ?? 0} note={`${s?.live_operations.bookings ?? 0} bookings created today`} icon={<Activity size={18}/>} href="/admin/home-services/bookings-jobs"/>
      <Kpi label="Pending Admin Actions" value={s?.pending_admin_actions.count ?? 0} note="Approvals, complaints and escalations" icon={<ClipboardCheck size={18}/>} tone={(s?.pending_admin_actions.count ?? 0) ? "warning" : "success"}/>
      <Kpi id="kpi-at-risk" label="At-Risk Tenants" value={s?.at_risk_tenants.count ?? 0} note={`${s?.at_risk_tenants.high_risk ?? 0} critical control failures`} icon={<AlertTriangle size={18}/>} tone={(s?.at_risk_tenants.count ?? 0) ? "danger" : "success"} href="/admin/home-services/providers"/>
    </div>}

    <section id="dashboard-active-panel" role="tabpanel" aria-labelledby={`dashboard-tab-${tab}`}>
    {restrictedTab ? <Card><div className={styles.restricted}><ShieldCheck size={32}/><h2>This workspace is restricted</h2><p>Your role does not include this dashboard domain.</p></div></Card> : <>
      {tab === "overview" && <OverviewTab range={range} setRange={setRange} home={home} trends={trends} actions={actions} activity={activity} resolve={resolve} snooze={snooze} busy={resolveAction.loading || snoozeAction.loading}/>}
      {tab === "operations" && <OperationsTab data={operations} live={liveOperations} actions={actions} search={operationSearch} setSearch={setOperationSearch} visible={visibleOperations} resolve={resolve} snooze={snooze} busy={resolveAction.loading || snoozeAction.loading}/>}
      {tab === "providers" && <ProvidersTab lifecycle={lifecycle} risk={atRisk}/>}
      {tab === "finance" && <FinanceTab range={range} setRange={setRange} finance={finance} trends={trends}/>}
      {tab === "platform" && <PlatformTab engines={engines} compliance={compliance} trust={trust} categories={categories} permissions={permissions}/>}
    </>}
    </section>
  </main></AdminLayout>;
}

type ApiState = ReturnType<typeof useApi<any>>;

function OverviewTab({ range, setRange, home, trends, actions, activity, resolve, snooze, busy }: { range: Range; setRange: (r: Range) => void; home: ApiState; trends: ApiState; actions: ApiState; activity: ApiState; resolve: (id: string) => void; snooze: (id: string) => void; busy: boolean }) {
  return <div className={styles.workspace}><div className={styles.primaryColumn}>
    <Card><SectionTitle title="Priority action queue" description="Only work that needs an administrator decision is shown." action={<Link href="/admin/operations" className={styles.textLink}>Open Operations Board <ArrowRight size={13}/></Link>}/>{actions.error ? <SectionError title="Action queue unavailable" error={actions.error} requestId={actions.requestId} onRetry={actions.refetch}/> : <ActionQueue items={(actions.data?.items ?? []).slice(0, 6)} loading={actions.loading} onResolve={resolve} onSnooze={snooze} busy={busy}/>}</Card>
    <Card><SectionTitle title="Native activity trend" description="Jobs created by the customer app and fulfilled through the staff app." action={<RangeControl value={range} onChange={setRange}/>}/>{trends.error ? <SectionError title="Trend unavailable" error={trends.error} requestId={trends.requestId} onRetry={trends.refetch}/> : trends.loading ? <Skeleton height={245}/> : <Chart data={trends.data?.jobs_trend ?? []}/>}</Card>
  </div><div className={styles.secondaryColumn}>
    <Card><SectionTitle title="Home Services Summary" description="Live production gates from tenant setup, bookability, finance, and trust controls."/>{home.error ? <SectionError title="Readiness unavailable" error={home.error} requestId={home.requestId} onRetry={home.refetch}/> : home.loading ? <Skeleton height={270}/> : <div className={styles.readinessList}>{[
      ["Service Catalog", home.data?.service_catalog_health.status, "/admin/catalog-workspace"], ["Finance Rules", home.data?.pricing_rule_health.status, "/admin/home-services/finance?tab=monetization"], ["Provider Coverage Readiness", home.data?.provider_coverage_health.status, "/admin/home-services/providers"], ["Bookability & Trust Gates", home.data?.provider_bookability_health.status, "/admin/bookability/providers"], ["Completion Deductions", home.data?.completed_job_deduction_health, "/admin/home-services/finance?tab=provider-charges"],
    ].map(([label, status, href]) => <Link href={String(href)} key={String(label)} className={styles.readinessItem}><span className={status === "healthy" ? styles.stateGood : status === "warning" ? styles.stateWarn : styles.stateBad}>{status === "healthy" ? <CheckCircle2 size={15}/> : <AlertTriangle size={15}/>}</span><span><strong>{label}</strong><small>{String(status || "not configured").replaceAll("_", " ")}</small></span><ArrowRight size={13}/></Link>)}</div>}</Card>
    <Card><SectionTitle title="Recent Activity" description="Latest audited administrator and system events."/>{activity.loading ? <Skeleton height={180}/> : !(activity.data?.items.length) ? <p className={styles.muted}>No activity yet.</p> : <div className={styles.timeline}>{activity.data.items.slice(0, 7).map((event: any) => <div key={event.id}><span/><div><strong>{event.action.replace(/[._]/g, " ")}</strong><small>{event.actor_role?.replaceAll("_", " ") || "system"} · {event.time ? new Date(event.time).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : ""}</small></div></div>)}</div>}<Link href="/admin/audit-logs" className={styles.footerLink}>Open complete audit trail <ExternalLink size={12}/></Link></Card>
  </div></div>;
}

function OperationsTab({ data, live, actions, search, setSearch, visible, resolve, snooze, busy }: { data: ApiState; live: ApiState; actions: ApiState; search: string; setSearch: (s: string) => void; visible: any[]; resolve: (id: string) => void; snooze: (id: string) => void; busy: boolean }) {
  return <div className={styles.workspaceSingle}>{data.error ? <SectionError title="Operations summary unavailable" error={data.error} requestId={data.requestId} onRetry={data.refetch}/> : <div className={styles.fourGrid}><Kpi label="Live Jobs" value={data.data?.live_jobs ?? 0} note="In native execution" icon={<Wrench size={18}/>}/><Kpi label="Today's Bookings" value={data.data?.today_bookings ?? 0} note="Customer app confirmations" icon={<CalendarClock size={18}/>}/><Kpi label="Pending Provider Acceptance" value={data.data?.pending_provider_acceptance ?? 0} note="Awaiting assignment" icon={<UsersRound size={18}/>} tone={(data.data?.pending_provider_acceptance ?? 0) ? "warning" : "success"}/><Kpi label="SLA Breaches" value={data.data?.sla_breaches ?? 0} note="Complaint response breaches" icon={<BellRing size={18}/>} tone={(data.data?.sla_breaches ?? 0) ? "danger" : "success"}/></div>}
    <Card><SectionTitle title="Live operations board" description="Current native Home Services jobs; use the full workspace for bulk action." action={<div className={styles.inlineActions}><label className={styles.search}><Search size={14}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search job, provider, status"/></label><Link href="/admin/home-services/bookings-jobs"><Btn size="sm">Full workspace <ArrowRight size={13}/></Btn></Link></div>}/>{live.error ? <SectionError title="Live operations unavailable" error={live.error} requestId={live.requestId} onRetry={live.refetch}/> : live.loading ? <Skeleton height={280}/> : <DataTable headers={["Job", "Provider", "Status", "Assignment", "Updated"]} empty={!visible.length}>{visible.map(item => <tr key={item.id}><td><Link href={`/admin/home-services/bookings-jobs?job=${item.id}`} className={styles.entityLink}>{item.item}</Link></td><td>{item.tenant || "Unassigned"}</td><td><Badge variant={item.status === "completed" ? "success" : "info"}>{item.status.replaceAll("_", " ")}</Badge></td><td>{item.assigned_to ? "Assigned" : "Unassigned"}</td><td>{item.updated_at ? new Date(item.updated_at).toLocaleString("en-IN") : "—"}</td></tr>)}</DataTable>}</Card>
    <Card><SectionTitle title="Pending Admin Action Queue" description="Resolvable operational exceptions with durable snooze state."/>{actions.error ? <SectionError title="Action queue unavailable" error={actions.error} requestId={actions.requestId} onRetry={actions.refetch}/> : <ActionQueue items={actions.data?.items ?? []} loading={actions.loading} onResolve={resolve} onSnooze={snooze} busy={busy}/>}</Card></div>;
}

function ProvidersTab({ lifecycle, risk }: { lifecycle: ApiState; risk: ApiState }) {
  return <div className={styles.workspaceSingle}>{lifecycle.error ? <SectionError title="Provider lifecycle unavailable" error={lifecycle.error} requestId={lifecycle.requestId} onRetry={lifecycle.refetch}/> : <><div className={styles.fourGrid}><Kpi label="Pending Review" value={lifecycle.data?.pending_review ?? 0} note="New setup submissions" icon={<ClipboardCheck size={18}/>} tone={(lifecycle.data?.pending_review ?? 0) ? "warning" : "success"}/><Kpi label="Changes Requested" value={lifecycle.data?.changes_requested ?? 0} note="Provider revisions" icon={<History size={18}/>}/><Kpi label="Bookable" value={lifecycle.data?.bookable_tenants ?? 0} note="Visible to customers" icon={<CheckCircle2 size={18}/>} tone="success"/><Kpi label="Non-Bookable" value={lifecycle.data?.non_bookable_tenants ?? 0} note="Blocked by a real gate" icon={<AlertTriangle size={18}/>} tone={(lifecycle.data?.non_bookable_tenants ?? 0) ? "warning" : "success"}/></div><Card><SectionTitle title="Tenant Lifecycle" description="Setup and verified-profile governance."/><MetricRows rows={[{ label: "New tenant requests", value: lifecycle.data?.new_tenant_requests ?? 0, href: "/admin/home-services/providers?status=onboarding_pending" }, { label: "Approved this week", value: lifecycle.data?.approved_this_week ?? 0 }, { label: "Suspended", value: lifecycle.data?.suspended ?? 0, danger: (lifecycle.data?.suspended ?? 0) > 0 }, { label: "View All Tenants", value: <ArrowRight size={14}/>, href: "/admin/home-services/providers" }]}/></Card></>}
    <Card><SectionTitle title="At-Risk Tenants" description="Derived from bookability, complaint SLAs, credit balance, and deduction reconciliation — not a retired health formula." action={<Link href="/admin/home-services/providers"><Btn size="sm" variant="secondary">Provider directory <ArrowRight size={13}/></Btn></Link>}/>{risk.error ? <SectionError title="Provider attention list unavailable" error={risk.error} requestId={risk.requestId} onRetry={risk.refetch}/> : risk.loading ? <Skeleton height={260}/> : <DataTable headers={["Provider", "Priority", "Primary reason", "Credits", "Last activity"]} empty={!risk.data?.items.length}>{(risk.data?.items ?? []).map((provider: any) => <tr key={provider.tenant_id}><td><Link className={styles.entityLink} href={`/admin/home-services/providers/${provider.tenant_id}`}>{provider.tenant_name}</Link></td><td><Badge variant={provider.risk_level === "critical" ? "danger" : provider.risk_level === "high" ? "warning" : "muted"}>{provider.risk_level}</Badge></td><td>{provider.top_reason}</td><td>{Number(provider.credit_balance || 0).toLocaleString("en-IN")}</td><td>{provider.last_activity ? new Date(provider.last_activity).toLocaleDateString("en-IN") : "—"}</td></tr>)}</DataTable>}</Card></div>;
}

function FinanceTab({ range, setRange, finance, trends }: { range: Range; setRange: (r: Range) => void; finance: ApiState; trends: ApiState }) {
  return <div className={styles.workspaceSingle}><SectionTitle title="Home Services finance" description="Top-up revenue, direct provider service value, and completion-credit deductions remain separate." action={<div className={styles.inlineActions}><RangeControl value={range} onChange={setRange}/><Link href="/admin/home-services/finance"><Btn size="sm">Finance workspace <ArrowRight size={13}/></Btn></Link></div>}/>
    {finance.error ? <SectionError title="Finance snapshot unavailable" error={finance.error} requestId={finance.requestId} onRetry={finance.refetch}/> : <><div className={styles.fourGrid}><Kpi label="Platform Revenue" value={formatCurrency(finance.data?.platform_revenue ?? 0)} note="Net credited top-up receipts" icon={<Banknote size={18}/>} tone="success"/><Kpi label="Provider Direct Service Value" value={formatCurrency(finance.data?.provider_direct_service_value ?? 0)} note="Paid service invoice value" icon={<Building2 size={18}/>}/><Kpi label="Completed Job Deductions" value={formatCurrency(finance.data?.completed_job_deductions ?? 0)} note="Provider + customer charge credits" icon={<ClipboardCheck size={18}/>}/></div><Card><SectionTitle title="Finance controls" description="Canonical sources used by this dashboard."/><MetricRows rows={[{ label: "Usage credit top-ups", value: formatCurrency(finance.data?.usage_credit_topups ?? 0), href: "/admin/home-services/finance?tab=credits" }, { label: "Customer service credits issued", value: formatCurrency(finance.data?.customer_service_credits_issued ?? 0), href: "/admin/home-services/finance?tab=refunds" }, { label: "Missing completion deductions", value: finance.data?.failed_deductions ?? 0, danger: (finance.data?.failed_deductions ?? 0) > 0, href: "/admin/home-services/finance?tab=provider-charges" }]}/></Card></>}
    <div className={styles.twoGrid}>{trends.error ? <SectionError title="Revenue trend unavailable" error={trends.error} requestId={trends.requestId} onRetry={trends.refetch}/> : <><Card><SectionTitle title="Top-up revenue trend" description="Net successful credit purchases."/>{finance.loading || trends.loading ? <Skeleton height={245}/> : <Chart data={trends.data?.revenue_trend ?? []} currency/>}</Card><Card><SectionTitle title="Completion deductions trend" description="Append-only usage-credit ledger."/>{trends.loading ? <Skeleton height={245}/> : <Chart data={trends.data?.completed_job_deductions_trend ?? []} kind="line" color="var(--success)" currency/>}</Card></>}</div></div>;
}

function PlatformTab({ engines, compliance, trust, categories, permissions }: { engines: ApiState; compliance: ApiState; trust: ApiState; categories: ApiState; permissions: ReturnType<typeof usePermissions> }) {
  return <div className={styles.workspace}><div className={styles.primaryColumn}>
    <Card><SectionTitle title="System / Engine Health" description="Registration and live database connectivity; open Engines for persisted probes." action={<Link href="/admin/engines"><Btn size="sm" variant="secondary">Engine center <ArrowRight size={13}/></Btn></Link>}/>{engines.error ? <SectionError title="Engine health unavailable" error={engines.error} requestId={engines.requestId} onRetry={engines.refetch}/> : engines.loading ? <Skeleton height={320}/> : <div className={styles.engineGrid}>{(engines.data?.items ?? []).map((engine: any) => <div key={engine.name}><span className={engine.status === "healthy" ? styles.stateGood : styles.stateBad}>{engine.status === "healthy" ? <CheckCircle2 size={15}/> : <AlertTriangle size={15}/>}</span><strong>{engine.name}</strong><Badge variant={engine.status === "healthy" ? "success" : engine.status === "warning" ? "warning" : "danger"}>{engine.status.replaceAll("_", " ")}</Badge></div>)}</div>}</Card>
    <Card><SectionTitle title="Category performance" description="Enabled verticals only; current project scope is Home Services."/>{categories.error ? <SectionError title="Category performance unavailable" error={categories.error} requestId={categories.requestId} onRetry={categories.refetch}/> : categories.loading ? <Skeleton height={180}/> : <DataTable headers={["Vertical", "Tenants", "Bookings", "Completion", "Avg Rating", "Complaint Rate"]} empty={!categories.data?.items.length}>{(categories.data?.items ?? []).map((category: any) => <tr key={category.vertical_key}><td><strong>{category.category_name}</strong></td><td>{category.tenant_count}</td><td>{category.booking_count}</td><td>{category.completion_rate.toFixed(1)}%</td><td>{category.avg_rating.toFixed(1)}</td><td>{category.complaint_rate.toFixed(1)}%</td></tr>)}</DataTable>}</Card>
  </div><div className={styles.secondaryColumn}>
    <Card><SectionTitle title="Compliance & Security" description="Open requests and threat telemetry."/>{compliance.error ? <SectionError title="Compliance telemetry unavailable" error={compliance.error} requestId={compliance.requestId} onRetry={compliance.refetch}/> : compliance.loading ? <Skeleton height={180}/> : <MetricRows rows={[{ label: "DPDP requests pending", value: compliance.data?.dpdp_requests_pending ?? 0, href: "/admin/compliance" }, { label: "Open threats", value: compliance.data?.open_threats ?? 0, danger: (compliance.data?.open_threats ?? 0) > 0, href: "/admin/security?tab=threats" }, { label: "Failed logins · 24h", value: compliance.data?.failed_logins ?? 0, danger: (compliance.data?.failed_logins ?? 0) > 0, href: "/admin/security" }]}/>}</Card>
    <Card><SectionTitle title="Trust & Quality" description="Native jobs, reviews, complaints, and disputes."/>{trust.error ? <SectionError title="Trust signals unavailable" error={trust.error} requestId={trust.requestId} onRetry={trust.refetch}/> : trust.loading ? <Skeleton height={200}/> : <MetricRows rows={[{ label: "Avg Rating", value: (trust.data?.avg_rating ?? 0).toFixed(1) }, { label: "Complaint Rate", value: `${trust.data?.complaint_rate ?? 0}%` }, { label: "Dispute Rate", value: `${trust.data?.dispute_rate ?? 0}%` }, { label: "Providers Under Review", value: trust.data?.providers_under_review ?? 0, danger: (trust.data?.providers_under_review ?? 0) > 0, href: "/admin/trust-quality" }]}/>}</Card>
    <Card><SectionTitle title="Quick Links"/><div className={styles.quickLinks}>{([[
      "Tenant Approvals", "/admin/home-services/providers?status=pending_review", "tenant:read"], ["Live Operations", "/admin/home-services/bookings-jobs", "admin:jobs:read"], ["Finance Summary", "/admin/home-services/finance", "finance:hub:read"], ["Security Center", "/admin/security", "security:read"], ["Engine Health", "/admin/engines", SUPER_ADMIN_ONLY],
    ] as const).filter(link => link[2] === SUPER_ADMIN_ONLY ? permissions.role === "super_admin" : permissions.has(link[2])).map(link => <Link href={link[1]} key={link[0]}><span>{link[0]}</span><ArrowRight size={13}/></Link>)}</div></Card>
  </div></div>;
}
