"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Skeleton, Input } from "../../../../components/shared/ui";
import {
  homeServicesOperationsApi, type UnifiedOperationRow, type UnifiedOperationsMetrics,
  finalRecordsAdminApi, adminExecutionApi, adminBookingsApi, adminReviewApi,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Search, Download, RefreshCw, X, Briefcase, FileText, UserX, Activity,
  Clock, AlertTriangle, ExternalLink, Phone, Star, Pencil,
} from "lucide-react";

// HOME-SERVICES-OPERATIONS: unified Bookings & Jobs workspace. Reads the
// canonical service_bookings/service_jobs projection only (backend
// operations_service.py) -- the legacy /admin/bookings page's
// bookings/field_ops.jobs pipeline is intentionally never merged in.

const TABS = [
  { key: "all", label: "All Work" },
  { key: "requests", label: "Requests" },
  { key: "active", label: "Active Jobs" },
  { key: "approval", label: "Awaiting Approval" },
  { key: "exceptions", label: "Exceptions" },
  { key: "completed", label: "Completed" },
] as const;
type TabKey = typeof TABS[number]["key"];

const STAGE_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  REQUEST: "muted", MATCHING: "info", UNASSIGNED: "warning", ASSIGNED: "info",
  SCHEDULED: "info", ON_THE_WAY: "info", INSPECTION: "info", AWAITING_ESTIMATE: "warning",
  AWAITING_APPROVAL: "warning", READY_TO_START: "info", IN_PROGRESS: "info",
  WORK_DONE: "success", COMPLETED: "success", AT_RISK: "danger", CLOSED: "muted", UNKNOWN: "muted",
};
const STAGE_LABEL: Record<string, string> = {
  REQUEST: "Request", MATCHING: "Provider matching", UNASSIGNED: "Unassigned",
  ASSIGNED: "Assigned", SCHEDULED: "Scheduled", ON_THE_WAY: "On the way",
  INSPECTION: "Inspection", AWAITING_ESTIMATE: "Awaiting estimate",
  AWAITING_APPROVAL: "Awaiting approval", READY_TO_START: "Ready to start",
  IN_PROGRESS: "Work in progress", WORK_DONE: "Work done", COMPLETED: "Completed",
  AT_RISK: "At risk", CLOSED: "Closed", UNKNOWN: "Unknown",
};
const SLA_BADGE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  ON_TRACK: "success", AT_RISK: "warning", BREACHED: "danger", NOT_APPLICABLE: "muted",
};

function fmtDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export default function HomeServicesOperationsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const view = (params.get("view") as TabKey) || "all";
  const search = params.get("search") || "";
  const stage = params.get("stage") || "";
  const page = Number(params.get("page") || "1");
  const [searchInput, setSearchInput] = useState(search);
  const [selected, setSelected] = useState<UnifiedOperationRow | null>(null);

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    router.push(`${pathname}?${next.toString()}`);
  }

  // Debounced search -> URL param
  useEffect(() => {
    const t = setTimeout(() => { if (searchInput !== search) setParam("search", searchInput || null); }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const listApi = useApi(useCallback(() => homeServicesOperationsApi.list({
    view, search: search || undefined, stage: stage || undefined, page, page_size: 10,
  }), [view, search, stage, page]), [view, search, stage, page]);

  const metricsApi = useApi(useCallback(() => homeServicesOperationsApi.summary(), []), []);

  const records = listApi.data?.records ?? [];
  const pagination = listApi.data?.pagination;
  const metrics = metricsApi.data as UnifiedOperationsMetrics | null;

  function exportCsv() {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = (typeof window !== "undefined" ? localStorage.getItem("serviceos_admin_token") : null) ?? "";
    const path = homeServicesOperationsApi.exportUrl({ view, search: search || undefined, stage: stage || undefined });
    fetch(path.startsWith("http") ? path : `${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `home-services-operations-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
      })
      .catch(err => console.error("Export failed:", err));
  }

  const METRIC_TILES: { key: string; label: string; value: number | undefined; icon: React.ReactNode; onClick: () => void; tooltip: string }[] = [
    { key: "active", label: "Active", value: metrics?.active, icon: <Briefcase size={16}/>, tooltip: "Every request/job not yet completed or closed",
      onClick: () => { setParam("view", "active"); setParam("stage", null); } },
    { key: "new_requests", label: "New Requests", value: metrics?.new_requests, icon: <FileText size={16}/>, tooltip: "Booking drafts not yet confirmed into a job",
      onClick: () => { setParam("view", "requests"); setParam("stage", null); } },
    { key: "unassigned", label: "Unassigned", value: metrics?.unassigned, icon: <UserX size={16}/>, tooltip: "Jobs with no technician assigned yet",
      onClick: () => { setParam("view", "all"); setParam("stage", "UNASSIGNED"); } },
    { key: "in_progress", label: "In Progress", value: metrics?.in_progress, icon: <Activity size={16}/>, tooltip: "Work has started, not yet done",
      onClick: () => { setParam("view", "all"); setParam("stage", "IN_PROGRESS"); } },
    { key: "awaiting_approval", label: "Awaiting Approval", value: metrics?.awaiting_approval, icon: <Clock size={16}/>, tooltip: "Estimate sent, waiting on customer approval",
      onClick: () => { setParam("view", "approval"); setParam("stage", null); } },
    { key: "at_risk", label: "At Risk", value: metrics?.at_risk, icon: <AlertTriangle size={16}/>, tooltip: "SLA breached or an operational exception",
      onClick: () => { setParam("view", "exceptions"); setParam("stage", null); } },
  ];

  return (
    <AdminLayout activeNav="home-services-operations">
      <div style={{ padding: "0 4px", display: "flex", gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Operations / Home Services</p>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Bookings & Jobs</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 18px" }}>
            Track every request from booking to completion in one workspace.
          </p>

          {/* Metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(120px, 1fr))", gap: 10, marginBottom: 18 }}>
            {METRIC_TILES.map(t => (
              <button key={t.key} onClick={t.onClick} title={t.tooltip}
                style={{ textAlign: "left", padding: "12px 14px", borderRadius: "var(--radius-lg)",
                  border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer" }}>
                <div style={{ color: "var(--text-tertiary)", marginBottom: 6 }}>{t.icon}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>
                  {metricsApi.loading ? "—" : t.value ?? 0}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{t.label}</div>
              </button>
            ))}
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: 14, borderBottom: "1px solid var(--border)", overflowX: "auto" }} role="tablist">
            {TABS.map(t => (
              <button key={t.key} role="tab" aria-selected={view === t.key}
                onClick={() => setParam("view", t.key === "all" ? null : t.key)}
                style={{ padding: "8px 14px", fontSize: 13, fontWeight: 600, border: "none", background: "none",
                  borderBottom: `2px solid ${view === t.key ? "var(--brand)" : "transparent"}`,
                  color: view === t.key ? "var(--text-primary)" : "var(--text-secondary)", cursor: "pointer", whiteSpace: "nowrap" }}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Filter bar */}
          <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: "1 1 240px" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
                placeholder="Booking, job, customer, tenant…" aria-label="Search operations"
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
            </div>
            <Btn variant="ghost" size="sm" onClick={() => listApi.refetch()}><RefreshCw size={14}/></Btn>
            <Btn variant="ghost" size="sm" onClick={exportCsv}><Download size={14} style={{ marginRight: 4 }}/>Export</Btn>
          </div>
          {(search || stage) && (
            <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
              {search && (
                <span style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 9px",
                  borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
                  Search: {search} <X size={11} style={{ cursor: "pointer" }} onClick={() => { setSearchInput(""); setParam("search", null); }}/>
                </span>
              )}
              {stage && (
                <span style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 9px",
                  borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
                  Stage: {STAGE_LABEL[stage] ?? stage} <X size={11} style={{ cursor: "pointer" }} onClick={() => setParam("stage", null)}/>
                </span>
              )}
            </div>
          )}

          {/* Table */}
          <Card style={{ padding: 0, overflow: "hidden" }}>
            {listApi.error ? (
              <div style={{ padding: 32, textAlign: "center" }}>
                <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{listApi.error}</p>
                <Btn variant="ghost" size="sm" onClick={() => listApi.refetch()}>Retry</Btn>
              </div>
            ) : listApi.loading ? (
              <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading operations…</div>
            ) : records.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center" }}>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 4px" }}>No records match this view.</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Try clearing filters or switching tabs.</p>
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                      {["Work ID", "Customer & Service", "Tenant", "Current Stage", "Assignment", "Schedule / SLA", "Location", "Updated", ""].map(h => (
                        <th key={h} scope="col" style={{ padding: "9px 12px", textAlign: "left", fontSize: 11, fontWeight: 700,
                          color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(row => (
                      <tr key={row.work_id} onClick={() => setSelected(row)}
                        style={{ borderBottom: "1px solid var(--border)", cursor: "pointer" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                        <td style={{ padding: "9px 12px" }}>
                          <div style={{ fontWeight: 700, color: "var(--primary)" }}>{row.work_id}</div>
                          {row.booking_number && <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Booking {row.booking_number}</div>}
                        </td>
                        <td style={{ padding: "9px 12px" }}>
                          <div>{row.customer_name ?? "—"}</div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.master_service ?? "—"}{row.job_type ? ` · ${row.job_type}` : ""}</div>
                        </td>
                        <td style={{ padding: "9px 12px" }}>{row.tenant_name ?? <span style={{ color: "var(--text-tertiary)" }}>Unassigned</span>}</td>
                        <td style={{ padding: "9px 12px" }}>
                          <Badge variant={STAGE_BADGE[row.current_stage] ?? "muted"} size="sm">{STAGE_LABEL[row.current_stage] ?? row.current_stage}</Badge>
                        </td>
                        <td style={{ padding: "9px 12px" }}>
                          {row.technician_name ?? (row.assignment_status === "unassigned"
                            ? <span style={{ color: "var(--warning-text)" }}>Unassigned</span> : "—")}
                        </td>
                        <td style={{ padding: "9px 12px" }}>
                          <div>{fmtDate(row.schedule.date)}</div>
                          <Badge variant={SLA_BADGE[row.sla_state]} size="sm">{row.sla_state.replace("_", " ")}</Badge>
                        </td>
                        <td style={{ padding: "9px 12px", color: "var(--text-secondary)" }}>{row.location_summary}</td>
                        <td style={{ padding: "9px 12px", color: "var(--text-tertiary)", fontSize: 12 }}>{fmtDate(row.updated_at)}</td>
                        <td style={{ padding: "9px 12px" }}>
                          <button onClick={e => { e.stopPropagation(); setSelected(row); }}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
                            <ExternalLink size={14}/>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {pagination && pagination.total_pages > 1 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderTop: "1px solid var(--border)" }}>
                <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  Page {pagination.page} of {pagination.total_pages} · {pagination.total} records
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <Btn variant="ghost" size="sm" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>Prev</Btn>
                  <Btn variant="ghost" size="sm" disabled={page >= pagination.total_pages} onClick={() => setParam("page", String(page + 1))}>Next</Btn>
                </div>
              </div>
            )}
          </Card>
        </div>

        {selected && <WorkDetailDrawer row={selected} onClose={() => setSelected(null)} />}
      </div>
    </AdminLayout>
  );
}

// ── Work detail drawer ──────────────────────────────────────────────────────
// Real full detail, not a stub link-out: for JOB-type rows this fetches the
// canonical job record (SLA + booking price snapshot), the real execution
// timeline (status-change events, not a fabricated fixed set of steps), and
// job notes -- the same data the /admin/home-services/service-jobs/{id} page
// itself reads, just surfaced inline. For REQUEST-type rows (no job yet)
// it falls back to the booking's own timeline/notes. Anything the reference
// design showed with no real backing field (a numbered "estimate version",
// a literal countdown timer ticking client-side) is rendered from whatever
// real data exists instead -- e.g. minutes_remaining is shown as a static
// value from the last fetch, not animated, since nothing here polls a clock.

function fmtDateTime(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function fmtMoneyLoose(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return `₹${n.toLocaleString("en-IN")}`;
}

const EXECUTION_EVENT_LABEL: Record<string, string> = {
  status_change: "Status changed", booking_confirmed: "Booking confirmed",
  technician_assigned: "Technician assigned", inspection_completed: "Inspection completed",
  estimate_sent: "Estimate sent", estimate_approved: "Estimate approved",
  work_started: "Work started", work_completed: "Work completed",
};

function WorkDetailDrawer({ row, onClose }: { row: UnifiedOperationRow; onClose: () => void }) {
  const job = useApi(useCallback(
    () => row.job_id ? finalRecordsAdminApi.getJob(row.job_id) : Promise.resolve(null),
    [row.job_id]));
  const execTimeline = useApi(useCallback(
    () => row.job_id ? adminExecutionApi.getJobTimeline(row.job_id) : Promise.resolve([]),
    [row.job_id]));
  const jobNotes = useApi(useCallback(
    () => row.job_id ? adminExecutionApi.getJobNotes(row.job_id) : Promise.resolve([]),
    [row.job_id]));
  const bookingTimeline = useApi(useCallback(
    () => !row.job_id && row.booking_id ? adminBookingsApi.getTimeline(row.booking_id) : Promise.resolve(null),
    [row.job_id, row.booking_id]));

  const j = job.data;
  const isCompleted = j?.status === "completed";
  // Rating only shows once the job is genuinely done -- fetched by job_id
  // (real column on customer_reviews, newly exposed as a filter on this
  // endpoint) rather than duplicating review data/moderation UI here.
  const review = useApi(useCallback(
    () => row.job_id && isCompleted ? adminReviewApi.list({ job_id: row.job_id, page_size: "1" }) : Promise.resolve(null),
    [row.job_id, isCompleted]
  ), [row.job_id, isCompleted]);
  const reviewRow = review.data?.items?.[0];
  const enableRatingAction = useAction(useCallback((id: string) => adminReviewApi.approve(id), []));
  const editReviewAction = useAction(useCallback(
    (id: string, updates: { overall_rating?: number; review_title?: string; review_text?: string }) =>
      adminReviewApi.edit(id, updates), []));
  const [editingReview, setEditingReview] = useState(false);
  const [editRating, setEditRating] = useState(0);
  const [editTitle, setEditTitle] = useState("");
  const [editText, setEditText] = useState("");
  const sla = j?.sla;
  const priceSnapshot = j?.booking?.price_snapshot as Record<string, unknown> | null | undefined;
  const events = execTimeline.data ?? [];
  const bookingEvents = bookingTimeline.data?.timeline ?? [];
  const loadingDetail = row.job_id ? (job.loading || execTimeline.loading) : bookingTimeline.loading;

  const allPriceRows = priceSnapshot
    ? Object.entries(priceSnapshot).filter(([, v]) => v !== null && v !== undefined && v !== "" && typeof v !== "object")
    : [];
  // Long free-text fields (a customer-facing message duplicated under two
  // keys in the real snapshot, e.g. "note" and "customer_message") render as
  // a single highlighted quote instead of two identical key/value rows.
  const noteEntry = allPriceRows.find(([, v]) => typeof v === "string" && v.length > 24);
  const priceNote = noteEntry?.[1] as string | undefined;
  const EXCLUDED_GRID_KEYS = new Set([noteEntry?.[0], "customer_total", "display_price"].filter(Boolean));
  const cleanPriceRows = allPriceRows.filter(([k, v]) =>
    !EXCLUDED_GRID_KEYS.has(k) && !(typeof v === "string" && v === priceNote));
  const customerTotal = priceSnapshot?.customer_total ?? priceSnapshot?.display_price ?? null;
  const timelineItems = row.job_id
    ? events.map(ev => ({ key: ev.id, when: ev.created_at, label: EXECUTION_EVENT_LABEL[ev.event_type] ?? (ev.new_status ? `→ ${ev.new_status.replace(/_/g, " ")}` : ev.event_type) }))
    : bookingEvents.map((ev, i) => ({ key: String(i), when: ev.occurred_at, label: `→ ${ev.to_status.replace(/_/g, " ")}${ev.reason ? ` (${ev.reason})` : ""}` }));

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 899 }} />
      <div role="dialog" aria-label="Work item details" style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: 840, maxWidth: "94vw",
        background: "var(--surface)", borderLeft: "1px solid var(--border)",
        boxShadow: "-8px 0 32px rgba(0,0,0,0.25)", zIndex: 900,
        display: "flex", flexDirection: "column",
        animation: "slideInWorkDrawer 0.2s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <style>{`@keyframes slideInWorkDrawer { from { transform: translateX(100%) } to { transform: translateX(0) } }`}</style>

        {/* Header */}
        <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
            <div style={{ width: 44, height: 44, borderRadius: 10, background: "var(--brand)", display: "flex",
              alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Briefcase size={18} color="white"/>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <p style={{ fontSize: 17, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>{row.work_id}</p>
                <Badge variant={STAGE_BADGE[row.current_stage] ?? "muted"} size="sm">{STAGE_LABEL[row.current_stage] ?? row.current_stage}</Badge>
              </div>
              {row.booking_number && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "3px 0 0" }}>Booking {row.booking_number}</p>}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close details" style={{ background: "none", border: "1px solid var(--border)", borderRadius: 8,
            width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "var(--text-tertiary)", flexShrink: 0 }}>
            <X size={16}/>
          </button>
        </div>

        {row.current_stage === "AWAITING_APPROVAL" && (
          <div style={{ margin: "16px 24px 0", padding: "10px 14px", borderRadius: "var(--radius-md)",
            background: "var(--warning-bg, rgba(234,179,8,0.1))", border: "1px solid var(--warning-border, rgba(234,179,8,0.3))",
            display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <AlertTriangle size={14} style={{ color: "var(--warning-text)", flexShrink: 0 }}/>
            <p style={{ fontSize: 12, fontWeight: 600, margin: 0, color: "var(--warning-text)" }}>
              Work cannot start until estimate approval.
            </p>
          </div>
        )}

        {/* Body: 2-column grid */}
        <div style={{ flex: 1, overflowY: "auto", padding: 24, display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 20 }}>
          {/* Left column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18, minWidth: 0 }}>
            <Card padding={16}>
              <h3 style={{ fontSize: 11, fontWeight: 700, margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>Customer & Service</h3>
              <p style={{ fontWeight: 700, margin: "0 0 3px", fontSize: 14, color: "var(--text-primary)" }}>{row.customer_name ?? "Unknown customer"}</p>
              {row.customer_contact_summary && (
                <p style={{ color: "var(--text-tertiary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 5, fontSize: 12 }}>
                  <Phone size={11}/> {row.customer_contact_summary}
                </p>
              )}
              <p style={{ color: "var(--text-secondary)", margin: "0 0 10px", fontSize: 13 }}>{row.master_service ?? "—"}{row.job_type ? ` · ${row.job_type}` : ""}</p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 13, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
                <div>
                  <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>Tenant</div>
                  <div style={{ fontWeight: 600 }}>{row.tenant_name ?? <em style={{ fontWeight: 400 }}>Unassigned</em>}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>Technician</div>
                  <div style={{ fontWeight: 600 }}>{row.technician_name ?? <em style={{ fontWeight: 400 }}>Unassigned</em>}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>Location</div>
                  <div style={{ fontWeight: 600 }}>{row.location_summary || "—"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>Updated</div>
                  <div style={{ fontWeight: 600 }}>{fmtDate(row.updated_at)}</div>
                </div>
              </div>
            </Card>

            {/* Timeline -- real execution/booking status-change events, not a fixed fabricated step list */}
            <Card padding={16}>
              <h3 style={{ fontSize: 11, fontWeight: 700, margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>Timeline</h3>
              {loadingDetail ? <Skeleton height={90} /> : timelineItems.length === 0 ? (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No status-change events recorded yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {timelineItems.map((it, i) => (
                    <div key={it.key} style={{ display: "flex", gap: 10, paddingBottom: i < timelineItems.length - 1 ? 12 : 0 }}>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--brand)", marginTop: 4 }}/>
                        {i < timelineItems.length - 1 && <span style={{ width: 1, flex: 1, background: "var(--border)", marginTop: 2 }}/>}
                      </div>
                      <div style={{ paddingBottom: 2 }}>
                        <p style={{ margin: 0, fontSize: 13, color: "var(--text-primary)" }}>{it.label}</p>
                        <p style={{ margin: "1px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{fmtDateTime(it.when)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Notes -- only for job-type rows; jobNotes.data stays empty for requests */}
            {row.job_id && (jobNotes.data ?? []).length > 0 && (
              <Card padding={16}>
                <h3 style={{ fontSize: 11, fontWeight: 700, margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>Notes</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {(jobNotes.data ?? []).map(n => (
                    <div key={n.id} style={{ fontSize: 12, padding: "10px 12px", background: "var(--surface-sunken)", borderRadius: 8 }}>
                      <p style={{ margin: "0 0 4px" }}>{n.note_text}</p>
                      <p style={{ margin: 0, color: "var(--text-tertiary)" }}>{n.note_type} · {fmtDateTime(n.created_at)}</p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18, minWidth: 0 }}>
            <Card padding={16}>
              <h3 style={{ fontSize: 11, fontWeight: 700, margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>SLA & Schedule</h3>
              <p style={{ fontSize: 13, margin: "0 0 10px", color: "var(--text-secondary)" }}>{fmtDate(row.schedule.date)}{row.schedule.window ? ` · ${row.schedule.window}` : ""}</p>
              <Badge variant={SLA_BADGE[sla?.sla_status ?? row.sla_state]} size="sm">{(sla?.sla_status ?? row.sla_state).replace("_", " ")}</Badge>
              {sla?.minutes_remaining != null && (
                <p style={{ fontSize: 12, color: "var(--warning-text)", margin: "8px 0 0", fontWeight: 600 }}>{sla.minutes_remaining} min remaining</p>
              )}
              {sla?.minutes_overdue != null && (
                <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "8px 0 0", fontWeight: 600 }}>Breached {sla.minutes_overdue} min overdue</p>
              )}
            </Card>

            {/* Estimate / price snapshot -- only rendered when the booking actually carries one */}
            {(cleanPriceRows.length > 0 || customerTotal != null) && (
              <Card padding={16}>
                <h3 style={{ fontSize: 11, fontWeight: 700, margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>Price / Estimate</h3>

                {customerTotal != null && (
                  <div style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>Customer Total</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>{fmtMoneyLoose(customerTotal) ?? String(customerTotal)}</div>
                  </div>
                )}

                {priceNote && (
                  <div style={{ marginBottom: 14, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)" }}>
                    <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>{priceNote}</p>
                  </div>
                )}

                {cleanPriceRows.length > 0 && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", rowGap: 10, columnGap: 12, fontSize: 12 }}>
                    {cleanPriceRows.map(([k, v]) => (
                      <div key={k}>
                        <div style={{ color: "var(--text-tertiary)", textTransform: "capitalize", fontSize: 10, marginBottom: 2 }}>{k.replace(/_/g, " ")}</div>
                        <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{fmtMoneyLoose(v) ?? String(v)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            )}

            {/* Customer review -- only real once the job is completed (see
                review hook above). Admin can enable (approve) a pending
                review, or directly edit its rating/text -- e.g. to correct
                an abusive/mistaken entry -- without needing the customer to
                resubmit. */}
            {isCompleted && (
              <Card padding={16}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3 style={{ fontSize: 11, fontWeight: 700, margin: 0, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-tertiary)" }}>
                    Customer Review
                  </h3>
                  {reviewRow && !editingReview && (
                    <Btn variant="ghost" size="sm" icon={<Pencil size={12} />}
                      onClick={() => {
                        setEditRating(reviewRow.overall_rating);
                        setEditTitle(reviewRow.review_title ?? "");
                        setEditText(reviewRow.review_text ?? "");
                        setEditingReview(true);
                      }}>
                      Edit
                    </Btn>
                  )}
                </div>

                {!reviewRow ? (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No review submitted for this job yet.</p>
                ) : editingReview ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      {[1, 2, 3, 4, 5].map(n => (
                        <button key={n} onClick={() => setEditRating(n)} type="button"
                          style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                          <Star size={20} fill={n <= editRating ? "var(--warning-text, #b45309)" : "none"}
                            color={n <= editRating ? "var(--warning-text, #b45309)" : "var(--text-tertiary)"} />
                        </button>
                      ))}
                    </div>
                    <Input value={editTitle} onChange={setEditTitle} placeholder="Review title" />
                    <textarea value={editText} onChange={e => setEditText(e.target.value)} rows={3}
                      placeholder="Review text"
                      style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box", resize: "vertical" }} />
                    <div style={{ display: "flex", gap: 8 }}>
                      <Btn variant="primary" size="sm" loading={editReviewAction.loading}
                        onClick={async () => {
                          const result = await editReviewAction.execute(reviewRow.id, {
                            overall_rating: editRating, review_title: editTitle, review_text: editText,
                          });
                          if (result) { setEditingReview(false); review.refetch(); }
                        }}>
                        Save Changes
                      </Btn>
                      <Btn variant="ghost" size="sm" onClick={() => setEditingReview(false)}>Cancel</Btn>
                    </div>
                    {editReviewAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{editReviewAction.error}</p>}
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ display: "flex", gap: 2 }}>
                        {[1, 2, 3, 4, 5].map(n => (
                          <Star key={n} size={15} fill={n <= reviewRow.overall_rating ? "var(--warning-text, #b45309)" : "none"}
                            color={n <= reviewRow.overall_rating ? "var(--warning-text, #b45309)" : "var(--text-tertiary)"} />
                        ))}
                      </div>
                      <Badge variant={reviewRow.status === "approved" ? "success" : reviewRow.status === "rejected" || reviewRow.status === "hidden" ? "danger" : "default"}>
                        {reviewRow.status}
                      </Badge>
                    </div>
                    {reviewRow.review_title && <p style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>{reviewRow.review_title}</p>}
                    {reviewRow.review_text && <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{reviewRow.review_text}</p>}
                    {reviewRow.status !== "approved" && (
                      <Btn variant="secondary" size="sm" loading={enableRatingAction.loading}
                        onClick={async () => { if (await enableRatingAction.execute(reviewRow.id)) review.refetch(); }}>
                        Enable Rating
                      </Btn>
                    )}
                    {enableRatingAction.error && <p style={{ fontSize: 11, color: "var(--danger-text)", margin: 0 }}>{enableRatingAction.error}</p>}
                  </div>
                )}
              </Card>
            )}
          </div>
        </div>

        {/* Footer actions */}
        <div style={{ padding: "14px 24px", borderTop: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap", flexShrink: 0 }}>
          {row.job_id && (
            <Btn variant="secondary" size="sm" icon={<ExternalLink size={13}/>}
              onClick={() => window.open(`/admin/home-services/service-jobs/${row.job_id}`, "_blank")}>
              Open Full Details
            </Btn>
          )}
        </div>
      </div>
    </>
  );
}
