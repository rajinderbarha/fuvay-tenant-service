"use client";
/**
 * Bookings & Jobs — unified provider pipeline.
 *
 * Replaces the separate /bookings and /jobs pages. Every customer home-
 * service request lands here as a Booking (bookingsApi, still awaiting
 * provider confirmation/conversion) and becomes a Job (serviceJobsApi) once
 * converted and assignable. Both live in one table so the provider never
 * has to context-switch between two screens for the same pipeline.
 *
 * Data sources (both real, no mock data):
 *  - bookingsApi.list({status}) — pending_confirmation / confirmed / cancelled
 *    bookings (the "converted" status bucket is intentionally excluded here:
 *    those records already appear as Jobs via serviceJobsApi, so including
 *    both would double-count the same underlying record).
 *  - serviceJobsApi.list() — canonical service_jobs once converted.
 *  - staffApi.list() — resolves assigned_staff_id to a display name/avatar.
 *
 * Stage model: booking.status and (job.status + job.assignment_status) are
 * mapped into one shared "stage" vocabulary (see STAGE_META) so the summary
 * cards, pipeline tabs, and row badges all speak the same language. Only
 * status values actually present in the codebase are mapped — see
 * deriveJobStage()/deriveBookingStage() for the full source list.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { PageHeader, Card, Button, Modal, Textarea } from "@serviceos/design-system";
import { Badge, Select, Input, SummaryCard,} from "../../../components/shared/ui";
import { bookingsApi, serviceJobsApi, staffApi, customersApi, catalogApi, providerOfferingsApi, getUserRole } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { Booking, ServiceJobRecord } from "../../../lib/api";
import {
  RefreshCw, Search, CheckCircle2, XCircle, ClipboardList, Users2,
  Clock, PlayCircle, CalendarClock, X,
} from "lucide-react";
import ReadOnlyBanner from "../../../components/shared/ReadOnlyBanner";

// ── Stage model ────────────────────────────────────────────────────────────

type StageKey =
  | "pending_confirmation" | "confirmed" | "unassigned" | "assigned"
  | "on_the_way" | "inspection" | "in_progress" | "work_done"
  | "completed" | "cancelled";

const MILESTONES = ["Booking", "Confirmed", "Assigned", "On the Way", "Inspection", "Work Done", "Completed"];

const STAGE_META: Record<StageKey, { label: string; helper: string; tone: "success" | "warning" | "danger" | "info" | "neutral"; milestone: number }> = {
  pending_confirmation: { label: "Pending Confirmation", helper: "Waiting for provider",         tone: "warning", milestone: 0 },
  confirmed:             { label: "Confirmed",            helper: "Ready to assign a technician",  tone: "info",    milestone: 1 },
  unassigned:            { label: "Unassigned",            helper: "Awaiting staff assignment",     tone: "warning", milestone: 2 },
  assigned:               { label: "Assigned",             helper: "Technician assigned",           tone: "info",    milestone: 2 },
  on_the_way:             { label: "On The Way",           helper: "Technician en route",           tone: "info",    milestone: 3 },
  inspection:             { label: "Inspection",           helper: "Inspecting the issue",          tone: "info",    milestone: 4 },
  in_progress:            { label: "In Progress",          helper: "Work in progress",              tone: "info",    milestone: 5 },
  work_done:              { label: "Work Done",            helper: "Awaiting final confirmation",   tone: "success", milestone: 5 },
  completed:              { label: "Completed",            helper: "Completed successfully",        tone: "success", milestone: 6 },
  cancelled:              { label: "Cancelled",            helper: "Cancelled",                     tone: "danger",  milestone: -1 },
};

function deriveBookingStage(status: string): StageKey {
  if (status === "confirmed") return "confirmed";
  if (status === "cancelled") return "cancelled";
  return "pending_confirmation";
}

// Maps the real service_jobs status + assignment_status enums (confirmed via
// the staff-side job execution pages and the provider assignment API) onto
// the shared stage vocabulary. Anything unrecognized falls back to
// "assigned" rather than throwing, matching the rest of this codebase's
// "never blank/crash on an unknown status string" convention.
function deriveJobStage(status: string, assignmentStatus: string): StageKey {
  if (assignmentStatus === "cancelled" || status === "cancelled") return "cancelled";
  if (status === "completed") return "completed";
  if (status === "work_done") return "work_done";
  if (status === "inspection_started" || status === "inspection_done") return "inspection";
  if (status === "on_the_way" || status === "reached_site") return "on_the_way";
  if (status === "service_started" || status === "in_progress" || status === "quote_required") return "in_progress";
  if (assignmentStatus === "unassigned" || assignmentStatus === "rejected") return "unassigned";
  return "assigned";
}

// ── Unified row model ────────────────────────────────────────────────────

type PipelineRow = {
  key: string;
  kind: "Booking" | "Job";
  number: string;
  href: string;
  customerId: string | null;
  serviceId: string;
  location: string;
  scheduleLabel: string;
  staffId: string | null;
  stage: StageKey;
  quotedPrice?: number;
  booking?: Booking;
  job?: ServiceJobRecord;
};

const shortId = (id?: string | null) => (id ? `${id.slice(0, 8)}…` : "—");

function formatSchedule(date?: string | null, window?: string | null, isoAt?: string | null): string {
  if (isoAt) {
    return new Date(isoAt).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  if (date) return `${date}${window ? ` · ${window}` : ""}`;
  return "Not scheduled yet";
}

function formatLocation(zipcode?: string | null, city?: string | null): string {
  if (zipcode && city) return `${zipcode}, ${city}`;
  return zipcode || city || "—";
}

const TABS: { key: "all" | StageKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending_confirmation", label: "Pending" },
  { key: "confirmed", label: "Confirmed" },
  { key: "unassigned", label: "Unassigned" },
  { key: "assigned", label: "Assigned" },
  { key: "on_the_way", label: "On the Way" },
  { key: "inspection", label: "Inspection" },
  { key: "in_progress", label: "In Progress" },
  { key: "work_done", label: "Work Done" },
  { key: "completed", label: "Completed" },
  { key: "cancelled", label: "Cancelled" },
];

export default function BookingsAndJobsPage() {
  const [tab, setTab] = useState<"all" | StageKey>("all");
  const [search, setSearch] = useState("");
  const [staffFilter, setStaffFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");

  const pending   = useApi(useCallback(() => bookingsApi.list({ status: "pending_confirmation", limit: "50" }), []));
  const confirmed = useApi(useCallback(() => bookingsApi.list({ status: "confirmed", limit: "50" }), []));
  const cancelledB = useApi(useCallback(() => bookingsApi.list({ status: "cancelled", limit: "50" }), []));
  const jobs      = useApi(useCallback(() => serviceJobsApi.list({ limit: 100 }), []));
  const staff     = useApi(useCallback(() => staffApi.list(), []));
  const customers = useApi(useCallback(() => customersApi.list({ limit: "200" }), []));
  const catalog   = useApi(useCallback(() => catalogApi.list(), []));
  const offerings = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));

  const staffNameById = useMemo(() => {
    const m = new Map<string, string>();
    (staff.data?.users ?? []).forEach(u => m.set(u.user_id, u.full_name));
    return m;
  }, [staff.data]);

  const customerNameById = useMemo(() => {
    const m = new Map<string, string>();
    (customers.data?.customers ?? []).forEach(c => m.set(c.id, c.name));
    return m;
  }, [customers.data]);

  // service_type_id (bookings) and offering_id (jobs) are two different
  // catalog concepts in this codebase -- resolved from two different real
  // endpoints, merged into one lookup keyed by whichever id a row carries.
  const serviceNameById = useMemo(() => {
    const m = new Map<string, string>();
    (catalog.data?.items ?? []).forEach(i => m.set(i.service_type_id, i.name));
    (offerings.data?.offerings ?? []).forEach(o => m.set(o.offering_id, o.provider_display_name || o.offering_name));
    return m;
  }, [catalog.data, offerings.data]);

  const loading = pending.loading || confirmed.loading || cancelledB.loading || jobs.loading;
  const anyError = pending.error || confirmed.error || cancelledB.error || jobs.error;

  const refetchAll = useCallback(() => {
    pending.refetch(); confirmed.refetch(); cancelledB.refetch(); jobs.refetch(); staff.refetch();
    customers.refetch(); catalog.refetch(); offerings.refetch();
  }, [pending, confirmed, cancelledB, jobs, staff, customers, catalog, offerings]);

  // Actions
  const confirmAction = useAction(useCallback((id: string) => bookingsApi.confirm(id), []));
  const rejectAction  = useAction(useCallback((id: string, reason: string) => bookingsApi.reject(id, reason), []));
  const convertAction = useAction(useCallback((id: string) => bookingsApi.convertToJob(id), []));

  const [rejectModal, setRejectModal] = useState(false);
  const [rejectId, setRejectId] = useState("");
  const [rejectMsg, setRejectMsg] = useState("");

  async function handleConfirm(id: string) {
    const res = await confirmAction.execute(id);
    if (res) refetchAll();
  }
  async function handleReject() {
    const res = await rejectAction.execute(rejectId, rejectMsg);
    if (res) { refetchAll(); setRejectModal(false); setRejectMsg(""); }
  }
  async function handleConvert(id: string) {
    const res = await convertAction.execute(id);
    if (res) refetchAll();
  }

  // ── Build the unified row set ──────────────────────────────────────────
  const rows: PipelineRow[] = useMemo(() => {
    const bookingRows: PipelineRow[] = [
      ...(pending.data?.bookings ?? []),
      ...(confirmed.data?.bookings ?? []),
      ...(cancelledB.data?.bookings ?? []),
    ].map(b => ({
      key: `booking-${b.booking_id}`,
      kind: "Booking" as const,
      number: b.booking_number,
      href: `/bookings/${b.booking_id}`,
      customerId: b.customer_id,
      serviceId: b.service_type_id,
      location: formatLocation(b.pincode, (b.address as { city?: string } | undefined)?.city),
      scheduleLabel: formatSchedule(b.preferred_date, b.preferred_slot, b.scheduled_at),
      staffId: null,
      stage: deriveBookingStage(b.status),
      quotedPrice: b.quoted_price,
      booking: b,
    }));

    const jobRows: PipelineRow[] = (jobs.data?.items ?? []).map(j => ({
      key: `job-${j.id}`,
      kind: "Job" as const,
      number: j.job_number,
      href: `/jobs/${j.id}`,
      customerId: j.customer_id,
      serviceId: j.offering_id,
      location: formatLocation(j.zipcode, j.city),
      scheduleLabel: formatSchedule(j.scheduled_date, j.scheduled_time_window, null),
      staffId: j.assigned_staff_id,
      stage: deriveJobStage(j.status, j.assignment_status),
      job: j,
    }));

    return [...bookingRows, ...jobRows];
  }, [pending.data, confirmed.data, cancelledB.data, jobs.data]);

  const areaOptions = useMemo(() => {
    const set = new Set<string>();
    rows.forEach(r => { if (r.location && r.location !== "—") set.add(r.location); });
    return Array.from(set).sort().map(v => ({ value: v, label: v }));
  }, [rows]);

  const staffOptions = useMemo(() =>
    (staff.data?.users ?? []).map(u => ({ value: u.user_id, label: u.full_name })),
    [staff.data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter(r => {
      if (tab !== "all" && r.stage !== tab) return false;
      if (staffFilter && r.staffId !== staffFilter) return false;
      if (areaFilter && r.location !== areaFilter) return false;
      if (dateFilter && !r.scheduleLabel.includes(dateFilter)) return false;
      if (!q) return true;
      const customerName = (r.customerId && customerNameById.get(r.customerId)) || "";
      const serviceName = serviceNameById.get(r.serviceId) || "";
      return (
        r.number.toLowerCase().includes(q) ||
        (r.customerId ?? "").toLowerCase().includes(q) ||
        customerName.toLowerCase().includes(q) ||
        serviceName.toLowerCase().includes(q) ||
        r.location.toLowerCase().includes(q)
      );
    });
  }, [rows, tab, staffFilter, areaFilter, dateFilter, search, customerNameById, serviceNameById]);

  // Client-side pagination over the merged, filtered pipeline -- the two
  // underlying APIs (bookings, jobs) paginate independently server-side, so
  // pagination on the unified view is applied after merging rather than
  // faking one shared server cursor across two different endpoints.
  const PAGE_SIZE = 20;
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pagedRows = useMemo(() => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [filtered, page]);
  useEffect(() => { setPage(1); }, [tab, staffFilter, areaFilter, dateFilter, search]);

  const clearFilters = () => { setTab("all"); setSearch(""); setStaffFilter(""); setAreaFilter(""); setDateFilter(""); };
  const hasFilters = tab !== "all" || !!search || !!staffFilter || !!areaFilter || !!dateFilter;

  // ── Summary counts ──────────────────────────────────────────────────────
  const today = new Date().toISOString().slice(0, 10);
  const summary = useMemo(() => ({
    total: rows.length,
    pendingConfirmation: rows.filter(r => r.stage === "pending_confirmation").length,
    confirmed: rows.filter(r => r.stage === "confirmed").length,
    unassigned: rows.filter(r => r.stage === "unassigned").length,
    inProgress: rows.filter(r => ["assigned", "on_the_way", "inspection", "in_progress"].includes(r.stage)).length,
    completedToday: rows.filter(r => r.stage === "completed" && (r.job?.updated_at ?? "").slice(0, 10) === today).length,
    cancelled: rows.filter(r => r.stage === "cancelled").length,
  }), [rows, today]);

  const stageCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of TABS) m[t.key] = t.key === "all" ? rows.length : rows.filter(r => r.stage === t.key).length;
    return m;
  }, [rows]);

  return (
    <TenantLayout activeNav="jobs">
      <ReadOnlyBanner role={getUserRole()} />
      <PageHeader
        title="Bookings & Jobs"
        description="All home service bookings and job stages in one unified pipeline"
        actions={<Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14} />} onClick={refetchAll}>Refresh</Button>}
      />

      {anyError && (
        <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--danger-bg)",
          border: "1px solid var(--danger-border)", marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{anyError}</p>
        </div>
      )}

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12, margin: "16px 0 20px" }}>
        <SummaryCard icon={<ClipboardList size={18} />} label="Total" value={summary.total}
          sub="Bookings + jobs" active={tab === "all"} onClick={() => setTab("all")} />
        <SummaryCard icon={<Clock size={18} />} label="Pending Confirmation" value={summary.pendingConfirmation}
          sub="Needs your response" tone="warning" active={tab === "pending_confirmation"} onClick={() => setTab("pending_confirmation")} />
        <SummaryCard icon={<CheckCircle2 size={18} />} label="Confirmed" value={summary.confirmed}
          sub="Ready to convert" tone="info" active={tab === "confirmed"} onClick={() => setTab("confirmed")} />
        <SummaryCard icon={<Users2 size={18} />} label="Unassigned" value={summary.unassigned}
          sub="Needs a technician" tone="warning" active={tab === "unassigned"} onClick={() => setTab("unassigned")} />
        <SummaryCard icon={<PlayCircle size={18} />} label="In Progress" value={summary.inProgress}
          sub="Active right now" tone="info" active={false} onClick={() => {}} />
        <SummaryCard icon={<CalendarClock size={18} />} label="Completed Today" value={summary.completedToday}
          sub="Finished today" tone="success" active={tab === "completed"} onClick={() => setTab("completed")} />
        <SummaryCard icon={<XCircle size={18} />} label="Cancelled" value={summary.cancelled}
          sub="No longer active" tone="danger" active={tab === "cancelled"} onClick={() => setTab("cancelled")} />
      </div>

      {/* Pipeline stage tabs */}
      <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 4, marginBottom: 16 }}
        role="tablist" aria-label="Pipeline stage">
        {TABS.map(t => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)} style={{
            display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 999, whiteSpace: "nowrap",
            border: tab === t.key ? "1px solid var(--brand)" : "1px solid var(--border)",
            background: tab === t.key ? "var(--accent-muted)" : "var(--surface)",
            color: tab === t.key ? "var(--brand)" : "var(--text-secondary)",
            fontSize: 13, fontWeight: tab === t.key ? 700 : 500, cursor: "pointer", fontFamily: "inherit",
          }}>
            {t.label}
            <span style={{ fontSize: 11, fontWeight: 700, padding: "1px 6px", borderRadius: 999,
              background: tab === t.key ? "var(--brand)" : "var(--surface-sunken)",
              color: tab === t.key ? "var(--text-on-brand)" : "var(--text-tertiary)" }}>
              {stageCounts[t.key] ?? 0}
            </span>
          </button>
        ))}
      </div>

      {/* Filters */}
      <Card padding="sm" style={{ marginBottom: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr auto", gap: 12, alignItems: "end" }}>
          <Input placeholder="Search booking/job ID, customer, area…" value={search} onChange={setSearch} icon={<Search />} />
          <Select label="" value={staffFilter} onChange={setStaffFilter} placeholder="All staff" options={staffOptions} />
          <Select label="" value={areaFilter} onChange={setAreaFilter} placeholder="All areas" options={areaOptions} />
          <Input type="date" placeholder="Date" value={dateFilter} onChange={setDateFilter} />
          {hasFilters && (
            <Button variant="ghost" size="sm" leftIcon={<X size={14} />} onClick={clearFilters}>Clear</Button>
          )}
        </div>
      </Card>

      {/* Unified pipeline table */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[...Array(5)].map((_, i) => <div key={i} style={{ height: 64, borderRadius: 12, background: "var(--surface-sunken)" }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card padding="lg" style={{ textAlign: "center" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 12, color: "var(--text-tertiary)" }}>
            <ClipboardList size={32} />
          </div>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
            {hasFilters ? "No bookings or jobs match your filters" : "Nothing in this stage yet"}
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
            {tab === "all"
              ? "New customer requests from the mobile app will appear here automatically."
              : `No records are currently in the "${STAGE_META[tab as StageKey]?.label ?? tab}" stage.`}
          </p>
          {hasFilters && <Button variant="secondary" size="sm" onClick={clearFilters}>Clear filters</Button>}
        </Card>
      ) : (
        <>
          <div className="ds-datatable-scroll" style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)" }}>
                  {["ID", "Customer", "Service", "Location", "Schedule", "Staff", "Timeline", "Actions"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 12, fontWeight: 600,
                      color: "var(--text-secondary)", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagedRows.map(r => (
                  <PipelineRowView key={r.key} row={r}
                    staffName={r.staffId ? staffNameById.get(r.staffId) ?? null : null}
                    customerName={r.customerId ? customerNameById.get(r.customerId) ?? null : null}
                    serviceName={serviceNameById.get(r.serviceId) ?? null}
                    confirmLoading={confirmAction.loading} convertLoading={convertAction.loading}
                    onConfirm={() => r.booking && handleConfirm(r.booking.booking_id)}
                    onReject={() => { if (r.booking) { setRejectId(r.booking.booking_id); setRejectModal(true); } }}
                    onConvert={() => r.booking && handleConvert(r.booking.booking_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Previous</Button>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page} of {pageCount}</span>
              <Button variant="ghost" size="sm" disabled={page >= pageCount} onClick={() => setPage(p => Math.min(pageCount, p + 1))}>Next</Button>
            </div>
          </div>
        </>
      )}

      <Modal
        open={rejectModal}
        onClose={() => setRejectModal(false)}
        title="Reject Booking"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setRejectModal(false)}>Cancel</Button>
          <Button variant="destructive" size="sm" loading={rejectAction.loading} onClick={handleReject}>
            Reject Booking
          </Button>
        </>}
      >
        <Textarea label="Reason for rejection" placeholder="Not available on this date, out of service area..."
          value={rejectMsg} onChange={e => setRejectMsg(e.target.value)} rows={3} required />
      </Modal>
    </TenantLayout>
  );
}

// ── Summary card ─────────────────────────────────────────────────────────


// ── Progress tracker ─────────────────────────────────────────────────────

// Compact form: a short segmented bar (filled = done) plus "N of 7 ·
// <Current stage> → <Next stage>" text — instead of spelling out all 7
// milestone labels inline, which reads as cluttered in a dense table row.
function ProgressTracker({ stage }: { stage: StageKey }) {
  const meta = STAGE_META[stage];
  if (stage === "cancelled") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 700, color: "var(--danger)" }}>
        <XCircle size={13} /> Cancelled
      </span>
    );
  }
  const current = meta.milestone;
  const total = MILESTONES.length;
  const next = current + 1 < total ? MILESTONES[current + 1] : null;

  return (
    <div style={{ minWidth: 150 }}>
      <div style={{ display: "flex", gap: 3 }} aria-label={`Progress: ${meta.label}, step ${current + 1} of ${total}`}>
        {MILESTONES.map((m, i) => (
          <span key={m} aria-hidden="true" style={{
            flex: 1, height: 5, borderRadius: 999,
            background: i < current ? "var(--brand)" : i === current ? "var(--brand)" : "var(--border)",
            opacity: i === current ? 0.55 : 1,
          }} />
        ))}
      </div>
      <p style={{ fontSize: 11, margin: "5px 0 0" }}>
        <span style={{ fontWeight: 700, color: "var(--brand)" }}>{current + 1} of {total} · {meta.label}</span>
        {next && <span style={{ color: "var(--text-tertiary)" }}> → next: {next}</span>}
      </p>
    </div>
  );
}

// ── Table row ────────────────────────────────────────────────────────────

function PipelineRowView({ row, staffName, customerName, serviceName, confirmLoading, convertLoading, onConfirm, onReject, onConvert }: {
  row: PipelineRow; staffName: string | null; customerName: string | null; serviceName: string | null;
  confirmLoading: boolean; convertLoading: boolean;
  onConfirm: () => void; onReject: () => void; onConvert: () => void;
}) {
  return (
    <tr style={{ borderBottom: "1px solid var(--border)" }}>
      <td style={{ padding: "12px 14px", verticalAlign: "top" }}>
        <a href={row.href} style={{ fontSize: 13, fontWeight: 700, color: "var(--text-link)", textDecoration: "none" }}>
          {row.number}
        </a>
        <div style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em",
          color: "var(--text-tertiary)", marginTop: 2 }}>{row.kind}</div>
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top", fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>
        {customerName ?? (row.customerId ? `#${shortId(row.customerId)}` : "—")}
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top", fontSize: 12, color: "var(--text-primary)" }}>
        {serviceName ?? shortId(row.serviceId)}
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top", fontSize: 12, color: "var(--text-secondary)" }}>
        {row.location}
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top", fontSize: 12, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
        {row.scheduleLabel}
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top" }}>
        {row.staffId ? (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--accent-muted)",
              color: "var(--accent)", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center",
              justifyContent: "center", flexShrink: 0 }}>
              {(staffName ?? "?").slice(0, 2).toUpperCase()}
            </span>
            <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{staffName ?? shortId(row.staffId)}</span>
          </div>
        ) : row.kind === "Job" ? (
          <Badge variant="warning" size="sm">Unassigned</Badge>
        ) : (
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>—</span>
        )}
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top" }}>
        <ProgressTracker stage={row.stage} />
      </td>
      <td style={{ padding: "12px 14px", verticalAlign: "top" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {row.kind === "Booking" && row.stage === "pending_confirmation" && (
            <>
              <Button variant="primary" size="sm" leftIcon={<CheckCircle2 size={13} />} loading={confirmLoading} onClick={onConfirm}>
                Confirm
              </Button>
              <Button variant="destructive" size="sm" leftIcon={<XCircle size={13} />} onClick={onReject}>
                Reject
              </Button>
            </>
          )}
          {row.kind === "Booking" && row.stage === "confirmed" && (
            <Button variant="primary" size="sm" loading={convertLoading} onClick={onConvert}>
              Convert to Job
            </Button>
          )}
          {row.kind === "Job" && row.stage === "unassigned" && (
            <Button variant="primary" size="sm" leftIcon={<Users2 size={13} />} onClick={() => window.location.href = row.href}>
              Assign
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => window.location.href = row.href}>View</Button>
        </div>
      </td>
    </tr>
  );
}
