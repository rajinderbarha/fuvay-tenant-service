"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle, ArrowRight, BriefcaseBusiness, CheckCircle2, CircleDollarSign,
  Clock3, CreditCard, MapPin, RefreshCw, ShieldAlert, Star, Users2, Wrench,
} from "lucide-react";
import { Alert, Button, Card, PageHeader, PageShell } from "@serviceos/design-system";
import { Badge, KpiGrid, Skeleton, SummaryCard } from "../../../components/shared/ui";
import { JobAlertPopup } from "../../../components/dashboard/JobAlertPopup";
import { useJobAlerts } from "../../../hooks/useJobAlerts";
import { useApi } from "../../../hooks/useApi";
import {
  homeServicesDashboardApi, homeServicesSetupOverviewApi,
  type HomeServicesDashboardAttentionItem, type HomeServicesDashboardData,
} from "../../../lib/api";

const destinationRoutes: Record<string, string> = {
  HOME_SERVICES_SETUP_OVERVIEW: "/tenant/home-services/setup/overview",
  HOME_SERVICES_UNDER_REVIEW: "/onboarding/application-status",
  HOME_SERVICES_CHANGES_REQUESTED: "/onboarding/application-status",
  HOME_SERVICES_ACTIVATION: "/onboarding/activation-center",
};
const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const integer = new Intl.NumberFormat("en-IN");
const count = (value: number | null | undefined) => integer.format(value ?? 0);
const humanize = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function timeAgo(value: string | null): string {
  if (!value) return "Time unavailable";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Time unavailable";
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}

function AttentionRow({ item, onOpen }: { item: HomeServicesDashboardAttentionItem; onOpen: () => void }) {
  const variant = item.severity === "danger" ? "danger" : item.severity === "warning" ? "warning" : "info";
  return <button type="button" onClick={onOpen} className="dashboard-row-button">
    <span className={`dashboard-attention-icon dashboard-attention-${variant}`}>
      {variant === "danger" ? <ShieldAlert size={17} /> : <AlertCircle size={17} />}
    </span>
    <span style={{ minWidth: 0, flex: 1 }}><span className="dashboard-row-title">{item.label}</span><span className="dashboard-row-detail">{item.oldest_age_hours == null ? "Action is required" : `Oldest item ${item.oldest_age_hours}h`}</span></span>
    <Badge variant={variant} size="sm">{count(item.count)}</Badge><ArrowRight size={15} color="var(--text-tertiary)" />
  </button>;
}

export default function DashboardPage() {
  const router = useRouter();
  const [access, setAccess] = useState<"checking" | "allowed" | "redirecting">("checking");
  useEffect(() => {
    homeServicesSetupOverviewApi.getRouting().then((routing) => {
      if (routing.next_destination === "TENANT_DASHBOARD") return setAccess("allowed");
      setAccess("redirecting");
      router.replace(destinationRoutes[routing.next_destination] ?? "/tenant/home-services/setup/overview");
    }).catch(() => setAccess("allowed"));
  }, [router]);
  if (access !== "allowed") return <PageShell><PageHeader eyebrow="Provider workspace" context="Overview" title="Loading your workspace" description="Checking your Home Services setup status." /><Skeleton height={180} /></PageShell>;
  return <OperationalDashboard />;
}

function OperationalDashboard() {
  const router = useRouter();
  const alerts = useJobAlerts();
  const fetchDashboard = useCallback(() => homeServicesDashboardApi.get(), []);
  const dashboard = useApi<HomeServicesDashboardData>(fetchDashboard, []);
  const data = dashboard.data;
  const bookabilityMessages = useMemo(() => {
    const messages = data?.bookability.blockers.map(
      blocker => blocker.message ?? humanize(blocker.code ?? "Setup requirement incomplete"),
    ) ?? [];
    return [...new Set(messages)];
  }, [data]);
  const location = useMemo(() => data
    ? [data.workspace.city, data.workspace.state, data.workspace.zipcode].filter(Boolean).join(", ") || "Service location not set"
    : "Home Services workspace", [data]);

  if (dashboard.loading && !data) return <PageShell><PageHeader eyebrow="Provider workspace" context="Overview" title="Operations dashboard" description="Loading live jobs, staff capacity, customers and finance." /><KpiGrid minCardWidth={210}>{[1, 2, 3, 4].map((key) => <Skeleton key={key} height={132} />)}</KpiGrid><Skeleton height={320} /></PageShell>;
  if (dashboard.error || !data) return <PageShell><PageHeader eyebrow="Provider workspace" context="Overview" title="Operations dashboard" description="Your Home Services command centre." /><Alert tone="danger" title="Dashboard could not be loaded">{dashboard.error ?? "The server returned no dashboard data."}{dashboard.requestId ? ` Request ID: ${dashboard.requestId}` : ""}</Alert><Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={dashboard.refetch}>Try again</Button></PageShell>;

  const summary = data.operational_summary;
  const quality = data.customers_quality;
  const finance = data.finance_snapshot;
  const maximumPipeline = Math.max(1, ...data.job_pipeline.map((stage) => stage.count));

  return <PageShell>
    <style jsx global>{`
      .dashboard-main-grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(300px,.8fr);gap:16px;align-items:start}.dashboard-split-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.dashboard-pipeline{display:grid;grid-template-columns:repeat(9,minmax(76px,1fr));gap:8px;overflow-x:auto;padding-bottom:4px}.dashboard-row-button{display:flex;width:100%;align-items:center;gap:11px;padding:11px 0;background:none;border:0;border-bottom:1px solid var(--border);cursor:pointer;text-align:left;font:inherit}.dashboard-row-button:last-child{border-bottom:0}.dashboard-attention-icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;flex-shrink:0}.dashboard-attention-danger{background:var(--danger-bg);color:var(--danger-text)}.dashboard-attention-warning{background:var(--warning-bg);color:var(--warning-text)}.dashboard-attention-info{background:var(--info-bg);color:var(--info-text)}.dashboard-row-title{display:block;color:var(--text-primary);font-size:13px;font-weight:650}.dashboard-row-detail{display:block;color:var(--text-tertiary);font-size:11px;margin-top:3px}.dashboard-metric-icon{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;flex-shrink:0}.dashboard-finance-tile{padding:12px;border-radius:10px;background:var(--surface-sunken)}.dashboard-finance-tile strong{display:block;color:var(--text-primary);font-size:18px;margin-top:8px}.dashboard-finance-tile span{display:block;color:var(--text-tertiary);font-size:10px;margin-top:3px}.dashboard-table-wrap{overflow-x:auto}.dashboard-table{width:100%;border-collapse:collapse;min-width:680px}.dashboard-table th{padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-tertiary);background:var(--surface-sunken);border-bottom:1px solid var(--border)}.dashboard-table td{padding:12px;font-size:12px;color:var(--text-secondary);border-bottom:1px solid var(--border)}.dashboard-table tbody tr{cursor:pointer}.dashboard-table tbody tr:hover{background:var(--surface-sunken)}.dashboard-table tbody tr:last-child td{border-bottom:0}@media(max-width:1050px){.dashboard-main-grid{grid-template-columns:1fr}.dashboard-pipeline{grid-template-columns:repeat(9,minmax(96px,1fr))}}@media(max-width:700px){.dashboard-split-grid{grid-template-columns:1fr}}
    `}</style>
    <PageHeader eyebrow="Provider workspace" context="Overview" title={`${data.workspace.business_name} operations`} description="Live Home Services jobs, technician capacity, customer quality and finance in one workspace." actions={<div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><Button variant="secondary" leftIcon={<Wrench size={16} />} onClick={() => router.push("/home-services/dispatch")}>Open dispatch</Button><Button variant="secondary" leftIcon={<RefreshCw size={16} />} loading={dashboard.loading} onClick={dashboard.refetch}>Refresh</Button></div>} />

    <JobAlertPopup alerts={alerts.pending} newTotal={alerts.newTotal} delayedTotal={alerts.delayedTotal} onDismiss={alerts.dismiss} onOpenJob={(jobId) => { alerts.dismiss(); router.push(`/home-services/bookings-jobs?job_id=${jobId}`); }} onSeeAllDelayed={() => { alerts.dismiss(); router.push("/home-services/bookings-jobs?sla=AT_RISK"); }} />

    <Card padding="sm"><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}><div className="dashboard-metric-icon" style={{ width: 42, height: 42, background: "var(--accent-muted)", color: "var(--accent)" }}><BriefcaseBusiness size={19} /></div><div><div style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 14 }}>{data.workspace.business_name}</div><div style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--text-tertiary)", fontSize: 11, marginTop: 3 }}><MapPin size={12} />{location}</div></div></div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}><Badge variant={data.bookability.is_bookable ? "success" : "danger"} dot>{data.bookability.is_bookable ? "Accepting bookings" : "Bookings blocked"}</Badge><span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Updated {timeAgo(data.generated_at)}</span></div>
    </div></Card>
    {data.failed_modules.length > 0 && <Alert tone="warning" title="Some live modules are temporarily unavailable">The core dashboard is available. Refresh to retry: {data.failed_modules.map(humanize).join(", ")}.</Alert>}
    {!data.bookability.is_bookable && bookabilityMessages.length > 0 && <Alert tone="danger" title="Customers cannot book this workspace">{bookabilityMessages.join(" · ")}</Alert>}

    <KpiGrid minCardWidth={210}>
      <SummaryCard icon={<BriefcaseBusiness />} label="Active jobs" value={count(summary.active_jobs)} sub="Across the live job pipeline" accent onClick={() => router.push("/home-services/bookings-jobs")} />
      <SummaryCard icon={<Clock3 />} label="Jobs today" value={count(summary.jobs_today)} sub="Scheduled for today" tone="success" onClick={() => router.push("/home-services/bookings-jobs?date=today")} />
      <SummaryCard icon={<Users2 />} label="Available now" value={count(summary.available_technicians)} sub={`${count(data.staff_capacity.ready)} roster-ready · ${count(data.staff_capacity.assigned_now)} assigned`} tone="success" onClick={() => router.push("/home-services/availability")} />
      <SummaryCard icon={<ShieldAlert />} label="Needs attention" value={count(summary.attention_items)} sub="Operational actions outstanding" tone={summary.attention_items > 0 ? "warning" : "success"} onClick={() => router.push("/operations/exceptions")} />
    </KpiGrid>

    <div className="dashboard-main-grid"><div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card title="Today’s jobs" actions={<Button variant="link" onClick={() => router.push("/home-services/bookings-jobs")}>View all jobs</Button>} padding="none">
        {data.todays_jobs.length === 0 ? <div style={{ padding: 30, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No jobs are scheduled for today.</div> : <div className="dashboard-table-wrap"><TableSurface className="dashboard-table"><thead><tr><th>Job</th><th>Customer</th><th>Service</th><th>Time</th><th>Technician</th><th>Status</th></tr></thead><tbody>{data.todays_jobs.map((job) => <tr key={job.job_id} onClick={() => router.push(`/home-services/bookings-jobs?job_id=${job.job_id}`)}><td style={{ color: "var(--text-primary)", fontWeight: 650 }}>{job.job_number}</td><td>{job.customer_name}</td><td>{job.service_name}</td><td>{job.scheduled_time ?? "Not set"}</td><td>{job.technician_name ?? "Unassigned"}</td><td><Badge variant={job.pipeline_group === "completed" ? "success" : job.pipeline_group === "awaiting_assignment" ? "warning" : "info"} size="sm">{humanize(job.pipeline_group)}</Badge></td></tr>)}</tbody></TableSurface></div>}
      </Card>
      <Card title="Job pipeline" actions={<Button variant="link" onClick={() => router.push("/home-services/bookings-jobs")}>Manage pipeline</Button>}><div className="dashboard-pipeline">{data.job_pipeline.map((stage) => <div key={stage.key}><div style={{ display: "flex", justifyContent: "space-between", gap: 6, color: "var(--text-secondary)", fontSize: 10, minHeight: 28 }}><span>{stage.label}</span><strong style={{ color: "var(--text-primary)" }}>{count(stage.count)}</strong></div><div style={{ height: 5, borderRadius: 999, background: "var(--surface-sunken)", overflow: "hidden" }}><div style={{ width: `${Math.max(stage.count > 0 ? 8 : 0, (stage.count / maximumPipeline) * 100)}%`, height: "100%", borderRadius: 999, background: "var(--accent)" }} /></div></div>)}</div></Card>
    </div><div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card title="Action centre" actions={<Badge variant={data.attention_queue.length ? "warning" : "success"}>{data.attention_queue.length}</Badge>}>{data.attention_queue.length ? data.attention_queue.map((item) => <AttentionRow key={item.key} item={item} onOpen={() => router.push(item.destination)} />) : <div style={{ padding: "16px 4px", display: "flex", alignItems: "center", gap: 10, color: "var(--success-text)", fontSize: 13 }}><CheckCircle2 size={19} />No operational actions are waiting.</div>}</Card>
      <Card title="Staff capacity" actions={<Button variant="link" onClick={() => router.push("/home-services/team")}>Manage team</Button>}><div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}>{([['Ready', data.staff_capacity.ready], ['Assigned', data.staff_capacity.assigned_now], ['Available', data.staff_capacity.available_now]] as const).map(([label, value]) => <div key={label} style={{ padding: 10, borderRadius: 10, background: "var(--surface-sunken)" }}><strong style={{ display: "block", color: "var(--text-primary)", fontSize: 18 }}>{count(value)}</strong><span style={{ color: "var(--text-tertiary)", fontSize: 10 }}>{label}</span></div>)}</div><div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 9 }}>{data.service_bookability.slice(0, 5).map((service) => <div key={service.offering_id} style={{ minWidth: 0, fontSize: 11 }}><div style={{ display: "flex", alignItems: "center", gap: 8 }}><span style={{ flex: 1, minWidth: 0, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{service.name}</span><Badge size="sm" variant={service.bookable ? "success" : "warning"}>{service.bookable ? "Bookable" : "Blocked"}</Badge></div>{!service.bookable && service.blocking_reason && <div title={service.blocking_reason} style={{ color: "var(--text-tertiary)", fontSize: 10, lineHeight: 1.35, marginTop: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{service.blocking_reason}</div>}</div>)}{data.service_bookability.length === 0 && <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>No published offerings found.</span>}</div></Card>
    </div></div>

    <div className="dashboard-split-grid">
      <Card title="Customers & quality" actions={<Button variant="link" onClick={() => router.push("/customers")}>Open customers</Button>}><div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }}>{([['Active', quality.active_customers, <Users2 size={15} key="a" />], ['Repeat', quality.repeat_customers, <RefreshCw size={15} key="r" />], ['Complaints', quality.open_complaints, <AlertCircle size={15} key="c" />], ['Rating', quality.average_rating == null ? '—' : quality.average_rating.toFixed(1), <Star size={15} key="s" />]] as const).map(([label, value, icon]) => <div key={label} style={{ padding: 11, borderRadius: 10, background: "var(--surface-sunken)" }}><span style={{ color: "var(--accent)" }}>{icon}</span><strong style={{ color: "var(--text-primary)", display: "block", fontSize: 18, marginTop: 8 }}>{typeof value === "number" ? count(value) : value}</strong><span style={{ color: "var(--text-tertiary)", fontSize: 10 }}>{label}</span></div>)}</div></Card>
      <Card title="Finance today" actions={<Button variant="link" onClick={() => router.push("/home-services/finance")}>Open finance</Button>}><div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 10 }}><div className="dashboard-finance-tile"><CreditCard size={16} color="var(--accent)" /><strong>{finance.usage_credit_balance == null ? "—" : money.format(finance.usage_credit_balance)}</strong><span>Usage credits</span></div><div className="dashboard-finance-tile"><CircleDollarSign size={16} color="var(--accent)" /><strong>{money.format(finance.completion_deductions_today_amount ?? 0)}</strong><span>Completion deductions</span></div><div className="dashboard-finance-tile"><strong>{count(finance.direct_payments_pending)}</strong><span>Payments pending</span></div><div className="dashboard-finance-tile"><strong>{count(finance.entitled_seats)}</strong><span>Technician seats</span></div></div></Card>
    </div>

    <Card title="Recent activity" actions={<span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Latest job events</span>}>{data.recent_activity.length ? <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 9 }}>{data.recent_activity.map((event, index) => <button key={`${event.job_id ?? "event"}-${event.occurred_at ?? index}`} type="button" onClick={() => event.job_id && router.push(`/home-services/bookings-jobs?job_id=${event.job_id}`)} style={{ padding: 11, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-sunken)", textAlign: "left", cursor: event.job_id ? "pointer" : "default" }}><strong style={{ color: "var(--text-primary)", display: "block", fontSize: 11 }}>{humanize(event.event_type)}</strong><span style={{ color: "var(--text-tertiary)", display: "block", fontSize: 10, marginTop: 5 }}>{timeAgo(event.occurred_at)}</span></button>)}</div> : <div style={{ color: "var(--text-tertiary)", fontSize: 12 }}>No job activity has been recorded yet.</div>}</Card>
  </PageShell>;
}
