"use client";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Users2, MapPin, CreditCard, RefreshCw,
  ChevronRight, Clock, AlertTriangle, FileClock, AlertOctagon, Receipt, MessageSquare,
  UserCheck, CheckCircle2, XCircle, Star, Truck,
} from "lucide-react";
import {
  providerServiceAreasApi, myStatusApi,
  type ProviderServiceArea,
  type TenantSecurityDepositStatus, type TenantCreditWalletDetail,
  type TenantStatusAuditLogEntry,
} from "../../../lib/api";
import {
  tenantComplaintsApi, bookingsJobsApi, hsReviewsApi,
  homeServicesTeamApi, homeServicesDirectPaymentsApi, providerStatusApi, hsCustomersApi,
  homeServicesSetupOverviewApi,
} from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { useSetupStatus } from "../../../hooks/useSetupStatus";
import { PageShell, PageHeader, Card, Button } from "@serviceos/design-system";
import { Badge, Skeleton } from "../../../components/shared/ui";
import { JobAlertPopup } from "../../../components/dashboard/JobAlertPopup";
import { useJobAlerts } from "../../../hooks/useJobAlerts";

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;
function safeStr(v: unknown, fb = "—"): string { const s = String(v ?? "").trim(); return s || fb; }
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
  const router = useRouter();
  const [access, setAccess] = useState<"checking" | "allowed" | "redirecting">("checking");

  useEffect(() => {
    homeServicesSetupOverviewApi.getRouting()
      .then(routing => {
        if (routing.next_destination === "TENANT_DASHBOARD") {
          setAccess("allowed");
          return;
        }
        const routeByDestination: Record<string, string> = {
          HOME_SERVICES_SETUP_OVERVIEW: "/tenant/home-services/setup/overview",
          HOME_SERVICES_UNDER_REVIEW: "/onboarding/application-status",
          HOME_SERVICES_CHANGES_REQUESTED: "/onboarding/application-status",
          HOME_SERVICES_ACTIVATION: "/onboarding/activation-center",
        };
        setAccess("redirecting");
        router.replace(routeByDestination[routing.next_destination] ?? "/tenant/home-services/setup/overview");
      })
      .catch(() => setAccess("allowed"));
  }, [router]);

  if (access !== "allowed") {
    return (
      <PageShell>
        <PageHeader title="Loading your workspace" description="Checking your Home Services setup status." />
        <Skeleton height={180}/>
      </PageShell>
    );
  }
  return <OperationalDashboard/>;
}

function OperationalDashboard() {
  const router = useRouter();
  const alerts = useJobAlerts();
  const [tenantName, setTenantName] = useState("Your Business");
  // Still needed for the Bookable/Not Bookable badge -- the setup banner,
  // Setup Readiness card and Setup% pill that used to read from this hook
  // were removed (2026-08-04): once a tenant's setup is actually done,
  // dashboard real estate goes to daily operations, not a checklist that
  // no longer applies. The full checklist still lives on the Profile
  // page's "Business Setup" section for anyone who still needs it.
  const setupStatus = useSetupStatus();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const n = localStorage.getItem("serviceos_tenant_name");
      if (n) setTenantName(n);
    }
  }, []);

  const areasApi = useApi<{ areas: ProviderServiceArea[]; total: number }>(useCallback(() => providerServiceAreasApi.list(), []), []);
  const depositApi = useApi<TenantSecurityDepositStatus>(useCallback(() => myStatusApi.getSecurityDeposit(), []), []);
  const walletApi = useApi<TenantCreditWalletDetail>(useCallback(() => myStatusApi.getCreditWallet(), []), []);
  const activityApi = useApi<{ logs: TenantStatusAuditLogEntry[] }>(useCallback(() => myStatusApi.getAuditLog(6), []), []);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const complaintsApi = useApi<any>(useCallback(() => tenantComplaintsApi.list({ status: "open" }), []), []);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const jobsApi = useApi<any>(useCallback(() => bookingsJobsApi.list({ page_size: 100 }), []), []);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // `page_size` is not a parameter this endpoint accepts -- it takes `limit`.
  // FastAPI ignores unknown query params, so this silently fell back to the
  // default of 10 and the dashboard's review panel was computed from the ten
  // most recent reviews while claiming to summarise a hundred.
  const reviewsApi = useApi<any>(useCallback(() => hsReviewsApi.list({ limit: 100 }), []), []);
  // Real data sources for the operational dashboard panels below -- every
  // one of these is a proven, mounted endpoint (see the dashboard redesign
  // research pass 2026-08-04): job pipeline/SLA/today's-jobs come from
  // bookingsJobsApi's own backend-computed `summary` and per-job
  // `stage`/`sla` fields (not re-derived client-side guesses), staff
  // capacity from the real team-directory summary, payment confirmations
  // from the direct-payments queue (previously 403'd for tenant_owner --
  // fixed in app/core/permissions.py alongside this), bookability from the
  // real per-offering status endpoint, and customer counts from the real
  // Home Services customer directory (which is the only source that
  // actually has a `repeat_status` field -- "repeat customers" would
  // otherwise have no backing data).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const teamSummaryApi = useApi<any>(useCallback(() => homeServicesTeamApi.list(), []), []);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingPaymentsApi = useApi<any>(useCallback(() => homeServicesDirectPaymentsApi.list({ status: "needs_action" }), []), []);
  const bookabilityApi = useApi(useCallback(() => providerStatusApi.get(), []), []);
  const offeringBookabilityApi = useApi(useCallback(() => providerStatusApi.getOfferingStatuses(), []), []);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hsCustomersDataApi = useApi<any>(useCallback(() => hsCustomersApi.list({ page_size: 200 }), []), []);

  const refreshAll = useCallback(() => {
    setupStatus.refetch(); areasApi.refetch(); depositApi.refetch();
    walletApi.refetch(); activityApi.refetch();
    complaintsApi.refetch(); jobsApi.refetch(); reviewsApi.refetch();
    teamSummaryApi.refetch(); pendingPaymentsApi.refetch(); bookabilityApi.refetch();
    offeringBookabilityApi.refetch(); hsCustomersDataApi.refetch();
  }, [setupStatus, areasApi, depositApi, walletApi, activityApi,
      complaintsApi, jobsApi, reviewsApi, teamSummaryApi, pendingPaymentsApi, bookabilityApi,
      offeringBookabilityApi, hsCustomersDataApi]);

  const isBookable = setupStatus.isBookable;

  const areasList = areasApi.data?.areas ?? [];
  const activeAreas = areasList.filter((a) => a.is_active);
  const primaryArea = areasList.find((a) => a.is_primary) ?? activeAreas[0];

  const deposit = depositApi.data;
  const wallet = walletApi.data;
  const activityLogs = activityApi.data?.logs ?? [];

  /** Every list endpoint here returns an `{ items, total }` envelope; `total`
   * is the authoritative count and must be preferred over `items.length`,
   * which only reflects the current page. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const envCount = (d: any): number =>
    safeNum(d?.total ?? (Array.isArray(d?.items) ? d.items.length : 0));

  const openComplaints = envCount(complaintsApi.data);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const jobRows: any[] = Array.isArray(jobsApi.data?.items) ? jobsApi.data.items : [];
  /** The backend already computes these aggregates from the full job set,
   * not just the current page (`jobRows` is page_size-limited to 100) --
   * `summary.*` is the authoritative source, not a client-side filter. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const jobsSummary: any = jobsApi.data?.summary ?? {};
  const jobsUnassigned = safeNum(jobsSummary.unassigned);
  const jobsAwaitingApproval = safeNum(jobsSummary.awaiting_approval);
  const jobsAtRisk = safeNum(jobsSummary.at_risk);

  /** Pipeline stage counts, grouped from the real per-job `stage_label`
   * field (backend-assigned, e.g. "New", "On the way", "Inspection") --
   * ordered by the same lifecycle sequence the backend's `next_action`
   * flow implies, not alphabetically. Stages with zero jobs still render
   * (0), so the bar always shows the full pipeline shape. */
  const PIPELINE_ORDER = ["New", "Awaiting assignment", "Scheduled", "On the way", "Inspection", "In progress", "Payment", "Completed"];
  const pipelineCounts = useMemo(() => {
    const counts = new Map<string, number>(PIPELINE_ORDER.map(s => [s, 0]));
    for (const j of jobRows) {
      const label: string = j?.stage_label
        ?? (j?.assignment_status === "unassigned" ? "Awaiting assignment" : "New");
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return PIPELINE_ORDER.map(label => ({ label, count: counts.get(label) ?? 0 }));
  }, [jobRows]);

  const todayIso = new Date().toISOString().slice(0, 10);
  const todaysJobs = useMemo(
    () => jobRows.filter(j => j?.scheduled_date === todayIso)
      .sort((a, b) => String(a?.scheduled_time_window ?? "").localeCompare(String(b?.scheduled_time_window ?? ""))),
    [jobRows, todayIso],
  );

  /**
   * Ten rows a page.
   *
   * A dashboard table is a summary, not the jobs list -- there is a "View all jobs" link
   * for that. Rendering every one of today's jobs pushed the panels beside it off screen
   * and made the page scroll for something that is meant to be glanceable.
   */
  const JOBS_PER_PAGE = 10;
  const [jobPage, setJobPage] = useState(0);
  const jobPageCount = Math.max(1, Math.ceil(todaysJobs.length / JOBS_PER_PAGE));
  // Clamped rather than trusted: the list refreshes on a timer, and a page that no longer
  // exists after jobs complete would otherwise render an empty table.
  const currentJobPage = Math.min(jobPage, jobPageCount - 1);
  const visibleJobs = todaysJobs.slice(
    currentJobPage * JOBS_PER_PAGE,
    currentJobPage * JOBS_PER_PAGE + JOBS_PER_PAGE,
  );

  const pendingPayments = safeNum(pendingPaymentsApi.data?.pagination?.total);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const teamSummary: any = teamSummaryApi.data?.summary ?? {};
  const bookability = bookabilityApi.data;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const offeringStatuses: any[] = Array.isArray(offeringBookabilityApi.data?.statuses) ? offeringBookabilityApi.data.statuses : [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hsCustomerRows: any[] = Array.isArray(hsCustomersDataApi.data?.items) ? hsCustomersDataApi.data.items : [];
  const activeCustomerCount = safeNum(hsCustomersDataApi.data?.total ?? hsCustomerRows.length);
  const repeatCustomerCount = hsCustomerRows.filter(c => c?.repeat_status && c.repeat_status !== "none").length;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const reviewRows: any[] = Array.isArray(reviewsApi.data?.items) ? reviewsApi.data.items : [];
  const ratings = reviewRows
    .map(r => safeNum(r?.overall_rating ?? r?.rating))
    .filter(n => n > 0);
  const avgRating = ratings.length
    ? (ratings.reduce((a, b) => a + b, 0) / ratings.length)
    : null;

  const pill = (v: string, tone: "success" | "warning" | "danger" = "success") => (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999,
      background: `var(--${tone}-bg)`, color: `var(--${tone}-text)`, border: `1px solid var(--${tone}-border)`,
    }}>{v}</span>
  );

  return (
    <PageShell>
      {/* Interrupts only for something that has not been shown before: a job that just
          arrived, or one that has gone past its slot. Both come from the server with
          their own tone, so the popup never has to guess how serious it is. */}
      {alerts.pending.length > 0 ? (
        <JobAlertPopup
          alerts={alerts.pending}
          newTotal={alerts.newTotal}
          delayedTotal={alerts.delayedTotal}
          onDismiss={alerts.dismiss}
          onOpenJob={jobId => { alerts.dismiss(); router.push(`/service-jobs/${jobId}`); }}
          onSeeAllDelayed={() => { alerts.dismiss(); router.push("/home-services/bookings-jobs"); }}
        />
      ) : null}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
        <PageHeader title="Home Services Dashboard" description="Manage today's bookings, staff capacity and service operations." />
        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={13} />} onClick={refreshAll}>
            Refresh
          </Button>
          <Button variant="secondary" size="sm" onClick={() => router.push("/home-services/bookings-jobs")}>
            View all jobs
          </Button>
          <Button variant="primary" size="sm" leftIcon={<Truck size={13} />} onClick={() => router.push("/home-services/dispatch")}>
            Dispatch board
          </Button>
        </div>
      </div>

      {/* ── Identity strip ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 24 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>{tenantName}</h1>
            {isBookable ? pill("Bookable", "success") : pill("Not Bookable", "danger")}
          </div>
          {primaryArea && (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 5, margin: 0 }}>
              <MapPin size={12} /> {safeStr(primaryArea.city)}, {safeStr(primaryArea.state)}
            </p>
          )}
        </div>
      </div>

      {/* ── Needs attention — real counts only, each linking to the page that
          resolves it. No item renders as a fabricated zero: every count is
          the backend's own aggregate (bookingsJobsApi's `summary`, the
          direct-payments queue's pagination total, or the complaints
          envelope), not a client-side guess. ── */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Needs attention</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
          {[
            { icon: <FileClock size={16} />, label: "Unassigned jobs", value: jobsUnassigned, href: "/home-services/bookings-jobs?status=unassigned", tone: jobsUnassigned > 0 ? "warning" : "success" },
            { icon: <Receipt size={16} />, label: "Estimates awaiting approval", value: jobsAwaitingApproval, href: "/home-services/bookings-jobs?status=estimate_approval", tone: jobsAwaitingApproval > 0 ? "warning" : "success" },
            { icon: <AlertOctagon size={16} />, label: "SLA at risk", value: jobsAtRisk, href: "/home-services/bookings-jobs?sla=AT_RISK", tone: jobsAtRisk > 0 ? "danger" : "success" },
            { icon: <CreditCard size={16} />, label: "Payment confirmations", value: pendingPayments, href: "/home-services/direct-payments", tone: pendingPayments > 0 ? "warning" : "success" },
            { icon: <MessageSquare size={16} />, label: "Open complaint", value: openComplaints, href: "/home-services/complaints", tone: openComplaints > 0 ? "danger" : "success" },
          ].map((n) => (
            <Link key={n.label} href={n.href} style={{ textDecoration: "none" }}>
              <Card style={{ padding: "14px 16px", cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: "var(--radius-md)", flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: `var(--${n.tone}-bg)`, color: `var(--${n.tone}-text)`,
                  }}>{n.icon}</div>
                  <div>
                    <p style={{ fontSize: 19, fontWeight: 800, color: "var(--text-primary)", margin: 0, lineHeight: 1.1 }}>
                      {(jobsApi.loading || complaintsApi.loading || pendingPaymentsApi.loading) ? <Skeleton width={24} height={19} /> : n.value}
                    </p>
                    <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{n.label}</p>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Job pipeline — real stage counts grouped from bookingsJobsApi's
          per-job `stage_label`, in lifecycle order. Zero-count stages still
          render so the bar always shows the shape of the whole pipeline. ── */}
      <Card style={{ marginBottom: 24 }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Job pipeline</p>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${pipelineCounts.length}, 1fr)`, gap: 10 }} className="pipeline-grid">
          <style>{`@media (max-width: 900px) { .pipeline-grid { grid-template-columns: repeat(4, 1fr) !important; } }`}</style>
          {pipelineCounts.map(s => (
            <div key={s.label} style={{
              padding: "10px 8px", borderRadius: "var(--radius-md)", textAlign: "center",
              background: s.count > 0 ? "var(--accent-muted)" : "var(--surface-sunken)",
              border: `1px solid ${s.count > 0 ? "var(--brand)" : "var(--border)"}`,
            }}>
              <p style={{ fontSize: 18, fontWeight: 800, margin: 0, color: s.count > 0 ? "var(--brand)" : "var(--text-tertiary)" }}>
                {jobsApi.loading ? <Skeleton width={20} height={18} /> : s.count}
              </p>
              <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "3px 0 0", lineHeight: 1.2 }}>{s.label}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Main grid: Today's Jobs | Staff capacity + Service bookability ── */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, marginBottom: 24 }} className="dash-grid">
        <style>{`@media (max-width: 1024px) { .dash-grid { grid-template-columns: 1fr !important; } }`}</style>

        {/* Today's Jobs -- real rows from bookingsJobsApi filtered to
            scheduled_date === today. No technician-name column: the real
            payload only carries `assigned_staff_id` (presence, not a
            name) on the list row -- showing a fabricated name here would
            be worse than an honest Assigned/Unassigned badge. */}
        <Card padding="none">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px 14px" }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
              <Clock size={16} color="var(--brand)" /> Today&apos;s Jobs
            </h3>
            <Link href="/home-services/bookings-jobs" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View all jobs</Link>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
                  {["Job", "Customer", "Service", "Time", "Technician", "Stage", "SLA", ""].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "8px 20px", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobsApi.loading ? (
                  <tr><td colSpan={8} style={{ padding: 20 }}><Skeleton height={16} /></td></tr>
                ) : todaysJobs.length === 0 ? (
                  <tr><td colSpan={8} style={{ padding: "24px 20px", fontSize: 13, color: "var(--text-tertiary)", textAlign: "center" }}>No jobs scheduled for today.</td></tr>
                ) : visibleJobs.map((j) => {
                  const slaStatus = j?.sla?.sla_status as string | undefined;
                  const slaTone = slaStatus === "BREACHED" ? "danger" : slaStatus === "AT_RISK" ? "warning" : "success";
                  return (
                    <tr key={j.service_job_id ?? j.job_number} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-primary)", fontWeight: 600, whiteSpace: "nowrap" }}>{safeStr(j.job_number)}</td>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-secondary)" }}>{safeStr(j.customer_alias)}</td>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-secondary)" }}>{safeStr(j.service_name)}</td>
                      <td style={{ padding: "10px 20px", fontSize: 13, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>{safeStr(j.scheduled_time_window)}</td>
                      <td style={{ padding: "10px 20px" }}>
                        {j.assigned_staff_id ? <Badge variant="success" size="sm">Assigned</Badge> : <Badge variant="warning" size="sm">Unassigned</Badge>}
                      </td>
                      <td style={{ padding: "10px 20px" }}><Badge variant="default" size="sm">{safeStr(j.stage_label)}</Badge></td>
                      <td style={{ padding: "10px 20px" }}>
                        {slaStatus ? <Badge variant={slaTone} size="sm">{slaStatus === "BREACHED" ? "Breached" : slaStatus === "AT_RISK" ? "At risk" : "On track"}</Badge> : "—"}
                      </td>
                      <td style={{ padding: "10px 20px" }}>
                        <Link href={`/home-services/bookings-jobs?job_id=${j.service_job_id}`} style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {jobPageCount > 1 ? (
              <div
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  gap: 12, padding: "10px 20px", borderTop: "1px solid var(--border)",
                }}
              >
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {/* The real range and the real total, so the table never understates how
                      much work today holds. */}
                  {`${currentJobPage * JOBS_PER_PAGE + 1}\u2013${currentJobPage * JOBS_PER_PAGE + visibleJobs.length} of ${todaysJobs.length}`}
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={currentJobPage === 0}
                    onClick={() => setJobPage(p => Math.max(0, p - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={currentJobPage >= jobPageCount - 1}
                    onClick={() => setJobPage(p => Math.min(jobPageCount - 1, p + 1))}
                  >
                    Next
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Staff capacity -- real team-directory summary: available_now,
              setup_incomplete and schedule_conflicts are all real
              backend-computed fields. */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              <UserCheck size={16} color="var(--brand)" /> Staff Capacity
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: teamSummary.schedule_conflicts > 0 || teamSummary.setup_incomplete > 0 ? 12 : 0 }}>
              {[
                { label: "Active", value: teamSummary.active },
                { label: "Available now", value: teamSummary.available_now },
                { label: "Technicians", value: teamSummary.technicians },
              ].map(s => (
                <div key={s.label} style={{ textAlign: "center", padding: "10px 6px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)" }}>
                  <p style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                    {teamSummaryApi.loading ? <Skeleton width={24} height={20} /> : safeNum(s.value)}
                  </p>
                  <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{s.label}</p>
                </div>
              ))}
            </div>
            {!teamSummaryApi.loading && safeNum(teamSummary.setup_incomplete) > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 8, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", fontSize: 12, color: "var(--warning-text)", marginBottom: 8 }}>
                <AlertTriangle size={13} style={{ flexShrink: 0 }} /> {teamSummary.setup_incomplete} team member{teamSummary.setup_incomplete === 1 ? "" : "s"} with incomplete setup
              </div>
            )}
            {!teamSummaryApi.loading && safeNum(teamSummary.schedule_conflicts) > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", fontSize: 12, color: "var(--danger-text)" }}>
                <AlertTriangle size={13} style={{ flexShrink: 0 }} /> {teamSummary.schedule_conflicts} schedule conflict{teamSummary.schedule_conflicts === 1 ? "" : "s"}
              </div>
            )}
            <Link href="/home-services/team" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 12 }}>View Team <ChevronRight size={12} /></Link>
          </Card>

          {/* Service bookability -- real data only. A true per-service
              breakdown (the design's "Bookable / Staff gap / Outside
              hours" per row) has no backing endpoint anywhere in this
              codebase (confirmed: /v1/provider/status/offerings exists and
              is real, but returns per-OFFERING evaluated bookability, not
              a staff-gap/hours classification) -- shown here honestly as
              whatever that real endpoint actually returns, plus the
              overall tenant-level bookability blockers, rather than
              inventing a richer breakdown the backend never computed. */}
          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
              {bookability?.is_bookable ? <CheckCircle2 size={16} color="var(--success)" /> : <XCircle size={16} color="var(--danger)" />} Service Bookability
            </h3>
            {bookabilityApi.loading ? <Skeleton height={20} /> : (
              <div style={{ marginBottom: 12 }}>
                <Badge variant={bookability?.is_bookable ? "success" : "danger"} size="sm">
                  {bookability?.is_bookable ? "Bookable" : "Not bookable"}
                </Badge>
                {!bookability?.is_bookable && (bookability?.bookability_blockers ?? []).map((b, i) => (
                  <p key={i} style={{ fontSize: 11.5, color: "var(--danger-text)", margin: "6px 0 0" }}>• {b.message}</p>
                ))}
              </div>
            )}
            {offeringBookabilityApi.loading ? <Skeleton height={40} /> : offeringStatuses.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No per-service bookability evaluation available yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {offeringStatuses.slice(0, 5).map((o) => (
                  <div key={o.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
                    <span style={{ color: "var(--text-secondary)" }}>{safeStr(o.offering_id)}</span>
                    <Badge variant={o.is_bookable ? "success" : "warning"} size="sm">{o.is_bookable ? "Bookable" : "Blocked"}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* ── Bottom row: Customers & Quality | Finance Snapshot | Recent Activity ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
        {/* Customers & quality */}
        <Card>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
            <Users2 size={16} color="var(--brand)" /> Customers & Quality
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
            {[
              { icon: <Users2 size={14} />, label: "Active customers", value: hsCustomersDataApi.loading ? null : activeCustomerCount },
              { icon: <RefreshCw size={14} />, label: "Repeat customers", value: hsCustomersDataApi.loading ? null : repeatCustomerCount },
              { icon: <MessageSquare size={14} />, label: "Open complaints", value: complaintsApi.loading ? null : openComplaints },
              { icon: <Star size={14} />, label: "Average rating", value: reviewsApi.loading ? null : (avgRating === null ? "—" : avgRating.toFixed(1)) },
            ].map(s => (
              <div key={s.label} style={{ textAlign: "center", padding: "10px 6px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)" }}>
                <div style={{ display: "flex", justifyContent: "center", color: "var(--text-tertiary)", marginBottom: 4 }}>{s.icon}</div>
                <p style={{ fontSize: 17, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                  {s.value === null ? <Skeleton width={20} height={17} /> : s.value}
                </p>
                <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{s.label}</p>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 14, marginTop: 12 }}>
            <Link href="/customers" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View customers</Link>
            <Link href="/home-services/reviews" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View reviews</Link>
            <Link href="/home-services/complaints" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>View complaints</Link>
          </div>
        </Card>

        {/* Finance snapshot -- direct-confirmations-pending now real (was
            silently 403ing for every tenant_owner; see the permissions.py
            fix alongside this rebuild), usage credit and security deposit
            unchanged (already-proven sources). No "completion deductions
            today" tile: no endpoint anywhere returns that figure, so it is
            omitted rather than invented. */}
        <Card>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 8 }}>
            <CreditCard size={16} color="var(--brand)" /> Finance Snapshot
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Direct Confirmations Pending</p>
              <div style={{ fontSize: 22, fontWeight: 700, color: pendingPayments > 0 ? "var(--warning-text)" : "var(--text-primary)", margin: "0 0 2px" }}>
                {pendingPaymentsApi.loading ? <Skeleton width={40} height={22} /> : pendingPayments}
              </div>
              <Link href="/home-services/direct-payments" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>Review Payments <ChevronRight size={12} /></Link>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Usage Credits</p>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                {walletApi.loading ? <Skeleton width={40} height={18} /> : `₹${safeNum(wallet?.balance)}`}
              </div>
              <Link href="/home-services/finance" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Ledger <ChevronRight size={12} /></Link>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Security Deposit</p>
              <div style={{ fontSize: 15, fontWeight: 700, color: deposit?.paid_amount ? "var(--success-text)" : "var(--text-primary)", margin: "0 0 4px" }}>
                {depositApi.loading ? <Skeleton width={60} height={18} /> : (deposit?.paid_amount ? `₹${safeNum(deposit.paid_amount)} Held` : `₹${safeNum(deposit?.required_amount)} Required`)}
              </div>
              <Link href="/packages" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2 }}>View Details <ChevronRight size={12} /></Link>
            </div>
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
          <Link href="/activity" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 2, marginTop: 14 }}>View All Activity <ChevronRight size={12} /></Link>
        </Card>
      </div>
    </PageShell>
  );
}
