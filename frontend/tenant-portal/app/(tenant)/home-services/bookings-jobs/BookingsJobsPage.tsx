"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Activity, AlertTriangle, CheckCircle2, ChevronRight, Clock3, Download,
  Columns3, ExternalLink, Filter, LayoutList, MapPin, RefreshCw, Search, ShieldAlert,
  SlidersHorizontal, Truck, UserX, Users, X,
} from "lucide-react";
import {
  Alert, Button, Card, Input, KpiGrid, Modal, PageHeader, PageShell, Pagination,
  Select, Skeleton, StatusBadge, SummaryCard,
} from "@serviceos/design-system";
import {
  bookingsJobsApi, type BJAddress, type BJDetail, type BJItem, type BJListResponse,
} from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";
import { BookingsLifecycleBoard } from "../../../../components/bookings/BookingsLifecycleBoard";

const PAGE_PATH = "/home-services/bookings-jobs";
const PAGE_SIZES = [25, 50, 100];
const LIVE_REFRESH_MS = 15_000;
const LIFECYCLE_STAGES = ["new", "assignment", "scheduled", "on_the_way", "inspection", "estimate_approval", "in_progress", "payment", "completed"];
const PROVIDER_ACTIONS = new Set(["assign_technician", "confirm_schedule", "schedule", "reschedule", "create_estimate", "send_estimate", "confirm_payment"]);

function todayISO(offsetDays = 0): string {
  const d = new Date(); d.setDate(d.getDate() + offsetDays);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function dateRange(preset: string, from: string, to: string) {
  if (from || to) return { date_from: from || undefined, date_to: to || undefined };
  if (preset === "today") return { date_from: todayISO(), date_to: todayISO() };
  if (preset === "tomorrow") return { date_from: todayISO(1), date_to: todayISO(1) };
  if (preset === "week") return { date_from: todayISO(), date_to: todayISO(6) };
  return {};
}
function cleanPage(value: string | null) { const n = Number(value ?? "1"); return Number.isInteger(n) && n > 0 ? n : 1; }
function cleanPageSize(value: string | null) { const n = Number(value ?? "25"); return PAGE_SIZES.includes(n) ? n : 25; }
function formatDate(value: string | null) { return value ? new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "Not scheduled"; }
function formatMoney(value: unknown) { const n = Number(value); return Number.isFinite(n) ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(n) : "—"; }
function csvCell(value: unknown) { return `"${String(value ?? "").replace(/"/g, '""')}"`; }
function paymentLabel(row: BJItem) { return row.stage === "payment" ? "Awaiting confirmation" : row.stage === "completed" ? "Recorded" : "Not due"; }

export default function BookingsJobsPage() { return <Suspense fallback={<PageSkeleton />}><BookingsJobsWorkspace /></Suspense>; }
function PageSkeleton() { return <PageShell><Skeleton height={650} /></PageShell>; }

function BookingsJobsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const stage = searchParams.get("stage") ?? "";
  const datePreset = searchParams.get("date") ?? "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";
  const offeringId = searchParams.get("service") ?? "";
  const jobTypeId = searchParams.get("job_type") ?? "";
  const technicianId = searchParams.get("technician") ?? "";
  const assignment = searchParams.get("assignment") ?? "";
  const sla = searchParams.get("sla") ?? "";
  const complaint = searchParams.get("complaint") ?? "";
  const sort = searchParams.get("sort") ?? "created_at:desc";
  const selectedJobId = searchParams.get("job_id");
  const page = cleanPage(searchParams.get("page"));
  const pageSize = cleanPageSize(searchParams.get("page_size"));
  const [searchDraft, setSearchDraft] = useState(search);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<"cards" | "board">("cards");
  useEffect(() => setSearchDraft(search), [search]);

  const updateParams = useCallback((updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => value ? next.set(key, value) : next.delete(key));
    router.push(next.size ? `${PAGE_PATH}?${next}` : PAGE_PATH);
  }, [router, searchParams]);
  const updateFilter = useCallback((key: string, value: string) => updateParams({ [key]: value || null, page: null, job_id: null }), [updateParams]);
  const clearFilters = useCallback(() => {
    const next = new URLSearchParams(searchParams.toString());
    ["search", "stage", "date", "date_from", "date_to", "service", "job_type", "technician", "assignment", "sla", "complaint", "sort", "page", "job_id"].forEach(key => next.delete(key));
    if (pageSize !== 25) next.set("page_size", String(pageSize));
    router.push(next.size ? `${PAGE_PATH}?${next}` : PAGE_PATH);
  }, [pageSize, router, searchParams]);

  const { date_from, date_to } = dateRange(datePreset, dateFrom, dateTo);
  const [sortBy, sortDir] = sort.split(":") as [string, string];
  const listDeps = [search, stage, date_from, date_to, offeringId, jobTypeId, technicianId, assignment, sla, complaint, sortBy, sortDir, page, pageSize];
  const list = useApi<BJListResponse>(useCallback(() => bookingsJobsApi.list({
    search: search || undefined, stage: stage || undefined, date_from, date_to,
    offering_id: offeringId || undefined, job_type_id: jobTypeId || undefined,
    assigned_staff_id: technicianId || undefined, assignment_status: assignment || undefined,
    sla: sla || undefined, has_complaint: complaint === "yes" ? true : complaint === "no" ? false : undefined,
    sort_by: sortBy, sort_dir: sortDir, limit: pageSize, offset: (page - 1) * pageSize,
  }), listDeps), listDeps);
  const detail = useApi<BJDetail | null>(useCallback(() => selectedJobId ? bookingsJobsApi.detail(selectedJobId) : Promise.resolve(null), [selectedJobId]), [selectedJobId]);
  const advancedFilterCount = [offeringId, jobTypeId, technicianId, assignment, sla, complaint, dateFrom || dateTo, sort !== "created_at:desc" ? sort : ""].filter(Boolean).length;
  const hasAnyFilter = Boolean(search || stage || datePreset || advancedFilterCount);
  const items = list.data?.items ?? [];
  const summary = list.data?.summary;

  useEffect(() => {
    const total = list.data?.total;
    if (total == null || page === 1) return;
    const lastPage = Math.max(1, Math.ceil(total / pageSize));
    if (page > lastPage) updateParams({ page: String(lastPage), job_id: null });
  }, [list.data?.total, page, pageSize, updateParams]);

  // A technician can advance the job from the staff app while this workspace
  // remains open. Keep the list and open drawer on the same lifecycle snapshot
  // so a payment-ready job cannot remain displayed under "Awaiting estimate".
  useEffect(() => {
    const refreshVisibleData = () => {
      if (document.visibilityState !== "visible") return;
      list.refetch();
      if (selectedJobId) detail.refetch();
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refreshVisibleData();
    };
    const timer = window.setInterval(refreshVisibleData, LIVE_REFRESH_MS);
    window.addEventListener("focus", refreshVisibleData);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshVisibleData);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [detail.refetch, list.refetch, selectedJobId]);

  function submitSearch(event: React.FormEvent) { event.preventDefault(); updateFilter("search", searchDraft.trim()); }
  function exportCurrentPage() {
    if (!items.length) return;
    const headers = ["Job", "Booking", "Customer", "Service", "Job type", "Schedule", "Technician", "Stage", "SLA", "Payment", "Complaints"];
    const rows = items.map(row => [row.job_number, row.booking_number, row.customer_alias, row.service_name, row.job_type_label, [row.scheduled_date, row.scheduled_time_window].filter(Boolean).join(" "), row.assigned_staff_name || "Unassigned", row.stage_label, row.sla?.sla_status, paymentLabel(row), row.open_complaint_count]);
    const blob = new Blob([[headers, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `bookings-jobs-page-${page}-${todayISO()}.csv`; a.click(); URL.revokeObjectURL(url);
  }

  return <><PageShell>
    <style>{`
      .bj-filter-grid{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px}.bj-drawer{width:min(470px,100vw)}.bj-view-switch{display:flex;gap:3px;padding:3px;border:1px solid var(--border);border-radius:12px;background:var(--surface-sunken)}.bj-view-switch button{display:grid;place-items:center;width:34px;height:34px;border:0;border-radius:9px;background:transparent;color:var(--text-tertiary);cursor:pointer}.bj-view-switch button[aria-pressed=true]{background:var(--text-primary);color:var(--surface);box-shadow:var(--shadow-sm)}.bj-card-list{display:flex;flex-direction:column;gap:10px;padding:16px}.bj-job-card{width:100%;padding:14px 16px;border:1px solid var(--border);border-radius:14px;background:var(--surface);color:var(--text-primary);text-align:left;transition:border-color .15s,background .15s}.bj-job-card:hover{border-color:var(--border-strong);background:var(--surface-sunken)}.bj-job-card[aria-current=true]{border-color:var(--brand);box-shadow:inset 3px 0 var(--brand)}.bj-card-top{display:flex;align-items:center;gap:12px}.bj-card-icon{display:grid;place-items:center;width:38px;height:38px;flex:none;border-radius:11px;background:var(--surface-sunken);color:var(--brand)}.bj-card-title{display:flex;min-width:0;flex:1;flex-direction:column;gap:3px}.bj-card-title>span:first-child{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.bj-card-title strong{font-size:15px}.bj-card-id{color:var(--text-tertiary);font:400 11px/1.3 "IBM Plex Mono",var(--font-family-mono)}.bj-card-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(140px,100%),1fr));gap:10px;margin-top:12px;padding-top:11px;border-top:1px solid var(--border)}.bj-card-field{display:flex;min-width:0;flex-direction:column;gap:3px}.bj-card-field small{color:var(--text-tertiary);font:500 10px/1 "IBM Plex Mono",var(--font-family-mono);letter-spacing:.06em;text-transform:uppercase}.bj-card-field span{overflow:hidden;color:var(--text-secondary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.bj-board{display:flex;gap:14px;overflow-x:auto;padding:16px 16px 20px;scrollbar-width:thin}.bj-board-column{display:flex;flex:0 0 270px;min-height:120px;flex-direction:column;gap:10px;padding:11px;border:1px solid var(--border);border-radius:14px;background:var(--surface-sunken)}.bj-board-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:0 3px}.bj-board-title{display:flex;align-items:center;gap:8px;color:var(--text-primary);font-size:12px;font-weight:650}.bj-board-dot{width:9px;height:9px;border-radius:50%;background:var(--text-tertiary)}.bj-board-dot[data-tone=brand]{background:var(--brand)}.bj-board-dot[data-tone=warning]{background:var(--warning)}.bj-board-count{padding:3px 8px;border:1px solid var(--border);border-radius:999px;background:var(--surface);color:var(--text-tertiary);font:500 11px/1 "IBM Plex Mono",var(--font-family-mono)}.bj-board-cards{display:flex;min-height:40px;flex-direction:column;gap:9px}.bj-board-empty{padding:16px 8px;text-align:center;color:var(--text-tertiary);font-size:11px}.bj-board-card{display:flex;flex-direction:column;gap:8px;padding:11px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--text-primary);text-align:left;cursor:pointer;transition:border-color .15s,transform .15s}.bj-board-card:hover{border-color:var(--border-strong);transform:translateY(-1px)}.bj-board-card[aria-current=true]{border-color:var(--brand)}.bj-board-card-top,.bj-board-card-foot{display:flex;align-items:center;justify-content:space-between;gap:8px}.bj-board-card-top strong{font-size:13px}.bj-board-service{font-size:12px;font-weight:650;color:var(--text-secondary)}.bj-board-customer{font-size:11px;color:var(--text-tertiary)}.bj-board-card-foot{padding-top:6px;border-top:1px solid var(--border);font-size:10.5px;color:var(--text-tertiary)}.bj-board-card-foot span:first-child[data-unassigned=true]{color:var(--danger-text);font-weight:650}.bj-board-time{font-family:"IBM Plex Mono",var(--font-family-mono);font-size:10px}@media(max-width:1100px){.bj-filter-grid{grid-template-columns:repeat(2,minmax(150px,1fr))}}@media(max-width:680px){.bj-filter-grid{grid-template-columns:1fr}.bj-header-actions{width:100%}.bj-card-top{align-items:flex-start}.bj-card-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.bj-board-column{flex-basis:min(82vw,270px)}}
    `}</style>
    <style>{`
      .bj-card-open{display:inline-flex;align-items:center;gap:4px;height:36px;padding:0 12px;border:1px solid var(--border);border-radius:10px;color:var(--text-primary);font-size:11.5px;font-weight:650}
      .bj-card-fields{grid-template-columns:repeat(6,minmax(0,1fr))}
      @media(max-width:1100px){.bj-card-fields{grid-template-columns:repeat(3,minmax(0,1fr))}}
      @media(max-width:680px){.bj-card-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.bj-card-open{padding:0 8px}}
    `}</style>
    <PageHeader eyebrow="" title="Bookings & jobs" description="One view from booking through assignment, execution, payment and closure." actions={<div className="bj-header-actions" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={15} />} onClick={list.refetch} loading={list.loading}>Refresh</Button>
      <Button variant="secondary" size="sm" leftIcon={<Download size={15} />} onClick={exportCurrentPage} disabled={!items.length}>Export</Button>
      <Button variant="primary" size="sm" rightIcon={<ChevronRight size={15} />} onClick={() => router.push("/home-services/dispatch")}>Dispatch board</Button>
    </div>} />
    {list.error && <Alert tone="danger">{list.error}</Alert>}
    {list.loading && !summary ? <KpiSkeleton /> : summary && <KpiGrid minCardWidth={155}>
      <SummaryCard label="Active jobs" value={summary.total_active} sub="Open lifecycle" icon={<Activity />} accent onClick={() => updateFilter("stage", "")} active={!stage} />
      <SummaryCard label="Unassigned" value={summary.unassigned} sub="Needs dispatch" icon={<UserX />} tone={summary.unassigned ? "warning" : undefined} onClick={() => updateFilter("stage", "new")} active={stage === "new"} />
      <SummaryCard label="In progress" value={summary.in_progress} sub="Work underway" icon={<Clock3 />} tone="info" onClick={() => updateFilter("stage", "in_progress")} active={stage === "in_progress"} />
      <SummaryCard label="Awaiting approval" value={summary.awaiting_approval} sub="Estimate decision" icon={<Users />} tone={summary.awaiting_approval ? "warning" : undefined} onClick={() => updateFilter("stage", "estimate_approval")} active={stage === "estimate_approval"} />
      <SummaryCard label="At risk" value={summary.at_risk} sub="SLA attention" icon={<ShieldAlert />} tone={summary.at_risk ? "danger" : undefined} onClick={() => updateFilter("sla", "AT_RISK")} active={sla === "AT_RISK"} />
      <SummaryCard label="Completed today" value={summary.completed_today} sub="Closed successfully" icon={<CheckCircle2 />} tone="success" onClick={() => updateFilter("stage", "completed")} active={stage === "completed"} />
    </KpiGrid>}
    <Card padding="none">
      <div style={{ padding: 16, borderBottom: "1px solid var(--border)", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <form onSubmit={submitSearch} style={{ display: "flex", flex: "1 1 360px", minWidth: 240 }}><div style={{ position: "relative", width: "100%" }}>
          <Search size={16} style={{ position: "absolute", left: 12, top: 11, color: "var(--text-tertiary)" }} />
          <input aria-label="Search bookings and jobs" value={searchDraft} onChange={e => setSearchDraft(e.target.value)} placeholder="Search job, booking, customer or technician" style={{ width: "100%", height: 42, padding: "0 38px 0 36px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", font: "inherit", fontSize: 14 }} />
          {searchDraft && <button type="button" aria-label="Clear search" onClick={() => { setSearchDraft(""); updateFilter("search", ""); }} style={iconButtonStyle}><X size={14} /></button>}
        </div></form>
        <select aria-label="Date preset" value={datePreset} onChange={e => updateParams({ date: e.target.value || null, date_from: null, date_to: null, page: null, job_id: null })} style={selectStyle}><option value="">All dates</option><option value="today">Today</option><option value="tomorrow">Tomorrow</option><option value="week">Next 7 days</option></select>
        <button type="button" onClick={() => setShowFilters(v => !v)} style={{ ...toolbarButtonStyle, borderColor: showFilters || advancedFilterCount ? "var(--accent)" : "var(--border)", color: showFilters || advancedFilterCount ? "var(--accent)" : "var(--text-secondary)" }}><SlidersHorizontal size={15} />Filters {advancedFilterCount > 0 && <span style={filterCountStyle}>{advancedFilterCount}</span>}</button>
        {hasAnyFilter && <button type="button" onClick={clearFilters} style={toolbarButtonStyle}><X size={14} />Clear</button>}
        <div className="bj-view-switch" aria-label="Bookings view">
          <button type="button" aria-label="Card view" aria-pressed={viewMode === "cards"} onClick={() => setViewMode("cards")}><LayoutList size={16} /></button>
          <button type="button" aria-label="Board view" aria-pressed={viewMode === "board"} onClick={() => setViewMode("board")}><Columns3 size={16} /></button>
        </div>
      </div>
      {showFilters && <AdvancedFilters data={list.data} values={{ offeringId, jobTypeId, technicianId, assignment, sla, complaint, dateFrom, dateTo, sort }} onChange={updateFilter} onDateChange={(key, value) => updateParams({ [key]: value || null, date: null, page: null, job_id: null })} />}
      {list.loading && !list.data ? <div style={{ padding: 16, display: "grid", gap: 8 }}>{Array.from({ length: 7 }, (_, i) => <Skeleton key={i} height={94} />)}</div> : items.length === 0 ? <EmptyResults filtered={hasAnyFilter} onClear={clearFilters} /> : viewMode === "cards" ? <div className="bj-card-list">{items.map(row => <JobCard key={row.service_job_id} row={row} selected={selectedJobId === row.service_job_id} onOpen={() => updateParams({ job_id: row.service_job_id })} />)}</div> : <BookingsLifecycleBoard items={items} selectedJobId={selectedJobId} onOpen={jobId => updateParams({ job_id: jobId })} />}
      <Pagination page={page} pageSize={pageSize} total={list.data?.total ?? 0} alwaysShow
        pageSizes={PAGE_SIZES} onPageSize={size => updateParams({ page_size: String(size), page: null, job_id: null })}
        onPage={p => updateParams({ page: String(p), job_id: null })} itemLabel="jobs" />
    </Card>
  </PageShell>{selectedJobId && <JobPreview jobId={selectedJobId} detail={detail.data} loading={detail.loading} error={detail.error} onClose={() => updateParams({ job_id: null })} onChanged={() => { detail.refetch(); list.refetch(); }} />}</>;
}

function KpiSkeleton() { return <KpiGrid minCardWidth={155}>{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} height={112} />)}</KpiGrid>; }

function AdvancedFilters({ data, values, onChange, onDateChange }: { data: BJListResponse | null; values: Record<string, string>; onChange: (key: string, value: string) => void; onDateChange: (key: string, value: string) => void }) {
  return <div style={{ padding: 16, background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}><div className="bj-filter-grid">
    <FilterSelect label="Service" value={values.offeringId} onChange={v => onChange("service", v)}><option value="">All services</option>{(data?.available_filters.services ?? []).map(x => <option key={x.offering_id} value={x.offering_id}>{x.name}</option>)}</FilterSelect>
    <FilterSelect label="Job type" value={values.jobTypeId} onChange={v => onChange("job_type", v)}><option value="">All job types</option>{(data?.available_filters.job_types ?? []).map(x => <option key={x.job_type_id} value={x.job_type_id}>{x.label}</option>)}</FilterSelect>
    <FilterSelect label="Technician" value={values.technicianId} onChange={v => onChange("technician", v)}><option value="">All technicians</option>{(data?.available_filters.technicians ?? []).map(x => <option key={x.staff_member_id} value={x.staff_member_id}>{x.name}</option>)}</FilterSelect>
    <FilterSelect label="Assignment" value={values.assignment} onChange={v => onChange("assignment", v)}><option value="">Any assignment</option><option value="assigned">Assigned</option><option value="unassigned">Unassigned</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option></FilterSelect>
    <FilterSelect label="SLA" value={values.sla} onChange={v => onChange("sla", v)}><option value="">Any SLA</option><option value="ON_TRACK">On track</option><option value="AT_RISK">At risk</option><option value="BREACHED">Breached</option></FilterSelect>
    <FilterSelect label="Complaints" value={values.complaint} onChange={v => onChange("complaint", v)}><option value="">Any complaint state</option><option value="yes">Has open complaint</option><option value="no">No open complaint</option></FilterSelect>
    <FilterSelect label="Sort" value={values.sort} onChange={v => onChange("sort", v)}><option value="created_at:desc">Newest created</option><option value="created_at:asc">Oldest created</option><option value="scheduled_date:asc">Schedule soonest</option><option value="updated_at:desc">Recently updated</option><option value="job_number:asc">Job number</option></FilterSelect>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}><DateFilter label="From" value={values.dateFrom} onChange={v => onDateChange("date_from", v)} /><DateFilter label="To" value={values.dateTo} onChange={v => onDateChange("date_to", v)} /></div>
  </div></div>;
}
function FilterSelect({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) { return <label style={filterLabelStyle}><span>{label}</span><select value={value} onChange={e => onChange(e.target.value)} style={{ ...selectStyle, width: "100%" }}>{children}</select></label>; }
function DateFilter({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label style={filterLabelStyle}><span>{label}</span><input type="date" value={value} onChange={e => onChange(e.target.value)} style={{ ...selectStyle, width: "100%" }} /></label>; }

function JobCard({ row, selected, onOpen }: { row: BJItem; selected: boolean; onOpen: () => void }) {
  return <button type="button" className="bj-job-card" aria-current={selected} onClick={onOpen}>
    <span className="bj-card-top">
      <span className="bj-card-icon"><Truck size={17} /></span>
      <span className="bj-card-title"><span><strong>{row.job_number}</strong><StatusBadge status={row.stage} size="sm" /></span><span className="bj-card-id">{row.booking_number}</span></span>
      <span className="bj-card-open">Open <ChevronRight size={13} /></span>
    </span>
    <span className="bj-card-fields">
      <span className="bj-card-field"><small>Customer</small><span>{row.customer_alias ?? "Private customer"}</span></span>
      <span className="bj-card-field"><small>Service</small><span>{row.service_name ?? "Service unavailable"} ({row.job_type_label ?? "Unresolved"})</span></span>
      <span className="bj-card-field"><small>Technician</small><span>{row.assigned_staff_name || "Unassigned"}</span></span>
      <span className="bj-card-field"><small>Schedule</small><span>{formatDate(row.scheduled_date)} {row.scheduled_time_window ?? ""}</span></span>
      <span className="bj-card-field"><small>SLA</small><SlaLabel status={row.sla?.sla_status ?? "NOT_APPLICABLE"} remaining={row.sla?.minutes_remaining} overdue={row.sla?.minutes_overdue} /></span>
      <span className="bj-card-field"><small>Payment</small><span>{paymentLabel(row)}</span></span>
    </span>
  </button>;
}
function SlaLabel({ status, remaining, overdue }: { status: string; remaining?: number | null; overdue?: number | null }) { if (status === "NOT_APPLICABLE") return <span style={secondaryCellStyle}>—</span>; const danger = status === "BREACHED", warning = status === "AT_RISK"; return <span style={{ fontSize: 12, fontWeight: 700, color: danger ? "var(--danger-text)" : warning ? "var(--warning-text)" : "var(--success-text)" }}>{danger ? `${overdue ?? 0}m overdue` : warning ? `${remaining ?? 0}m left` : "On track"}</span>; }
function EmptyResults({ filtered, onClear }: { filtered: boolean; onClear: () => void }) { return <div style={{ padding: "58px 24px", textAlign: "center" }}><div style={{ width: 48, height: 48, borderRadius: 14, background: "var(--accent-muted)", color: "var(--accent)", display: "grid", placeItems: "center", margin: "0 auto 14px" }}><Filter size={21} /></div><h3 style={{ margin: 0, color: "var(--text-primary)", fontSize: 16 }}>{filtered ? "No jobs match these filters" : "No bookings or jobs yet"}</h3><p style={{ margin: "6px auto 16px", color: "var(--text-secondary)", fontSize: 13, maxWidth: 430 }}>{filtered ? "Clear or broaden the filters to return to the full operational queue." : "Confirmed customer bookings will appear here automatically with their job workflow."}</p>{filtered && <Button variant="secondary" size="sm" onClick={onClear}>Clear filters</Button>}</div>; }

function JobPreview({ jobId, detail, loading, error, onClose, onChanged }: { jobId: string; detail: BJDetail | null; loading: boolean; error: string | null; onClose: () => void; onChanged: () => void }) {
  const router = useRouter(); const [confirmOpen, setConfirmOpen] = useState(false); const [cancelOpen, setCancelOpen] = useState(false); const [address, setAddress] = useState<BJAddress | null>(null); const [addressLoading, setAddressLoading] = useState(false); const [addressError, setAddressError] = useState<string | null>(null);
  async function revealAddress() { setAddressLoading(true); setAddressError(null); try { setAddress(await bookingsJobsApi.address(jobId)); } catch (e) { setAddressError(e instanceof Error ? e.message : "Could not load the service address."); } finally { setAddressLoading(false); } }
  const nextAction = detail?.stage.next_action; const providerOwnsAction = nextAction ? PROVIDER_ACTIONS.has(nextAction.action_key) : false; const resolvedId = String(detail?.job.id ?? jobId);
  const dispatchUrl = `/home-services/dispatch?${new URLSearchParams({ ...(detail?.job.scheduled_date ? { date: detail.job.scheduled_date } : {}), job_id: resolvedId }).toString()}`;
  function actionButton() {
    if (!detail || !nextAction || !providerOwnsAction) return null;
    if (nextAction.action_key === "assign_technician") return <Button variant="primary" size="sm" leftIcon={<Truck size={14} />} onClick={() => router.push(dispatchUrl)}>Assign in dispatch</Button>;
    if (["create_estimate", "send_estimate"].includes(nextAction.action_key)) return <Button variant="primary" size="sm" rightIcon={<ExternalLink size={13} />} onClick={() => router.push(`/service-jobs/${resolvedId}/quotes`)}>Open estimate</Button>;
    if (nextAction.action_key === "confirm_payment") return detail.invoice ? <Button variant="primary" size="sm" onClick={() => setConfirmOpen(true)}>Confirm direct payment</Button> : <Alert tone="warning">The technician must submit the completion amount before payment can be confirmed.</Alert>;
    return <Button variant="primary" size="sm" rightIcon={<ChevronRight size={13} />} onClick={() => router.push(dispatchUrl)}>Open job workspace</Button>;
  }
  return <><div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 1090, background: "rgba(0,0,0,.46)", backdropFilter: "blur(2px)" }} /><aside className="bj-drawer" aria-label="Job preview" style={{ position: "fixed", right: 0, top: 0, bottom: 0, zIndex: 1100, overflowY: "auto", background: "var(--surface)", borderLeft: "1px solid var(--border)", boxShadow: "-18px 0 55px rgba(0,0,0,.28)" }}>
    <div style={{ position: "sticky", top: 0, zIndex: 2, padding: "18px 20px", background: "var(--surface)", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", gap: 12 }}><div><div style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".06em", color: "var(--text-tertiary)", textTransform: "uppercase" }}>{detail?.job.job_number ?? "Job preview"}</div><h2 style={{ margin: "3px 0 0", fontSize: 20, color: "var(--text-primary)" }}>{detail?.service_name ?? "Loading job"}</h2></div><button type="button" onClick={onClose} aria-label="Close job preview" style={{ ...toolbarButtonStyle, width: 36, height: 36, padding: 0, justifyContent: "center" }}><X size={17} /></button></div>
    <div style={{ padding: 20, display: "grid", gap: 14 }}>{loading || !detail ? error ? <Alert tone="danger">{error}</Alert> : <><Skeleton height={70} /><Skeleton height={180} /><Skeleton height={240} /></> : <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}><StatusBadge status={detail.stage.stage} /><SlaLabel status={detail.sla.sla_status} remaining={detail.sla.minutes_remaining} overdue={detail.sla.minutes_overdue} /></div>
      <Card padding="sm"><PanelTitle title="Customer & visit" /><Field label="Customer" value={String(detail.booking.customer_alias ?? "Private customer")} />{detail.customer_health && <Field label="Customer health" value={`${Math.round(detail.customer_health.score)}/100 · ${detail.customer_health.band.replace(/_/g, " ")}`} />}<Field label="Locality" value={String(detail.booking.locality ?? "Unavailable")} />{address ? <AddressView address={address} /> : <Button variant="secondary" size="sm" leftIcon={<MapPin size={13} />} onClick={revealAddress} loading={addressLoading} style={{ marginTop: 10 }}>View service address</Button>}{addressError && <div style={{ marginTop: 8 }}><Alert tone="danger">{addressError}</Alert></div>}</Card>
      <Card padding="sm"><PanelTitle title="Service context" /><Field label="Job type" value={detail.job_type_label ?? "Unresolved"} /><Field label="Schedule" value={detail.job.scheduled_date ? `${formatDate(detail.job.scheduled_date)} · ${detail.job.scheduled_time_window ?? "Time pending"}` : "Not scheduled"} /><Field label="Visit fee" value={detail.visit_fee ? formatMoney(detail.visit_fee) : "—"} /><Field label="Estimate" value={detail.quote ? `${formatMoney(detail.quote.customer_payable_amount)} · ${String(detail.quote.status ?? "created").replace(/_/g, " ")}` : "No estimate yet"} /><Field label="Payment" value={detail.invoice ? String(detail.invoice.payment_status ?? "Pending").replace(/_/g, " ") : "No invoice yet"} /></Card>
      <Card padding="sm"><PanelTitle title={detail.workflow_stages.length ? "Workflow" : "Lifecycle"} />{detail.workflow_stages.length ? <Workflow stages={detail.workflow_stages} /> : <Lifecycle current={detail.stage.stage} />}</Card>
      <Card padding="sm" style={{ background: "var(--accent-muted)" }}><div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".05em", fontWeight: 700 }}>Next required action</div><div style={{ margin: "5px 0 11px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{nextAction?.label ?? "No action · workflow complete"}</div>{nextAction && !providerOwnsAction && <div style={{ marginBottom: 10, fontSize: 12, color: "var(--text-secondary)" }}>This step belongs to the assigned technician in the native staff app. Monitor it here; the provider workspace does not duplicate field execution controls.</div>}{actionButton()}</Card>
      {detail.open_complaint_count > 0 && <button type="button" onClick={() => router.push(`/home-services/complaints?q=${encodeURIComponent(String(detail.job.job_number))}`)} style={{ ...toolbarButtonStyle, width: "100%", justifyContent: "space-between", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}><span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}><AlertTriangle size={15} />{detail.open_complaint_count} open complaint{detail.open_complaint_count === 1 ? "" : "s"}</span><ChevronRight size={15} /></button>}
      <div style={{ fontSize: 11, lineHeight: 1.55, color: "var(--text-tertiary)" }}>{detail.direct_payment_notice}</div><Button variant="secondary" size="sm" rightIcon={<ChevronRight size={13} />} onClick={() => router.push(dispatchUrl)} style={{ width: "100%" }}>Manage in dispatch</Button>
      {!detail.stage.is_terminal && <Button variant="destructive" size="sm" leftIcon={<AlertTriangle size={13} />} onClick={() => setCancelOpen(true)} style={{ width: "100%" }}>Cancel job</Button>}
      {confirmOpen && <ConfirmPaymentModal jobId={jobId} invoiceAmount={detail.invoice?.customer_payable_amount} onClose={() => setConfirmOpen(false)} onSaved={() => { setConfirmOpen(false); onChanged(); }} />}
      {cancelOpen && <CancelJobModal jobId={jobId} onClose={() => setCancelOpen(false)} onSaved={() => { setCancelOpen(false); onChanged(); }} />}
    </>}</div>
  </aside></>;
}

function PanelTitle({ title }: { title: string }) { return <div style={{ marginBottom: 9, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".06em", fontWeight: 700 }}>{title}</div>; }
function Field({ label, value }: { label: string; value: string }) { return <div style={{ display: "flex", justifyContent: "space-between", gap: 18, padding: "6px 0", fontSize: 12.5 }}><span style={{ color: "var(--text-tertiary)" }}>{label}</span><span style={{ color: "var(--text-primary)", textAlign: "right", fontWeight: 500 }}>{value}</span></div>; }
function AddressView({ address }: { address: BJAddress }) { if (!address.granted) return <div style={{ marginTop: 10 }}><Alert tone="warning">Exact address is unavailable for this job state. {address.locality ?? ""}</Alert></div>; const s = address.address_snapshot; const text = typeof s === "string" ? s : s ? Object.values(s).filter(v => typeof v === "string" && v).join(", ") : ""; return <div style={{ marginTop: 10, padding: 10, borderRadius: 9, background: "var(--surface-sunken)", fontSize: 12, lineHeight: 1.5, color: "var(--text-secondary)" }}><div style={{ display: "flex", gap: 7, color: "var(--text-primary)", fontWeight: 700, marginBottom: 3 }}><MapPin size={14} />Service address</div>{[text, address.city, address.zipcode].filter(Boolean).join(", ") || "Address snapshot unavailable"}</div>; }
function Workflow({ stages }: { stages: BJDetail["workflow_stages"] }) { return <div style={{ display: "grid", gap: 3 }}>{stages.map((step, i) => <div key={step.step_key} style={{ display: "grid", gridTemplateColumns: "24px 1fr auto", gap: 8, alignItems: "center", minHeight: 34 }}><div style={{ width: 24, height: 24, borderRadius: 999, display: "grid", placeItems: "center", fontSize: 10, fontWeight: 800, background: step.state === "current" ? "var(--accent)" : step.state === "completed" ? "var(--success-bg)" : "var(--surface-sunken)", color: step.state === "current" ? "white" : step.state === "completed" ? "var(--success-text)" : "var(--text-tertiary)", border: "1px solid var(--border)" }}>{step.state === "completed" ? "✓" : i + 1}</div><span style={{ fontSize: 12.5, fontWeight: step.state === "current" ? 700 : 500, color: step.state === "upcoming" ? "var(--text-tertiary)" : "var(--text-primary)", textDecoration: step.state === "skipped" ? "line-through" : undefined }}>{step.label}</span><span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{step.requires_photo && step.state !== "completed" ? "Photo" : step.state === "skipped" ? "Skipped" : ""}</span></div>)}</div>; }
function Lifecycle({ current }: { current: string }) { const currentIndex = LIFECYCLE_STAGES.indexOf(current); return <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>{LIFECYCLE_STAGES.map((stage, i) => <span key={stage} style={{ padding: "4px 8px", borderRadius: 999, fontSize: 10.5, fontWeight: stage === current ? 700 : 500, background: stage === current ? "var(--accent)" : i < currentIndex ? "var(--success-bg)" : "var(--surface-sunken)", color: stage === current ? "white" : i < currentIndex ? "var(--success-text)" : "var(--text-tertiary)" }}>{stage.replace(/_/g, " ")}</span>)}</div>; }
function ConfirmPaymentModal({ jobId, invoiceAmount, onClose, onSaved }: { jobId: string; invoiceAmount?: number | string; onClose: () => void; onSaved: () => void }) { const [paymentMode, setPaymentMode] = useState("onsite_cash"), [amount, setAmount] = useState(invoiceAmount ? String(invoiceAmount) : ""); const payment = useAction((body: { payment_mode: string; collected_amount: number }) => bookingsJobsApi.confirmPayment(jobId, body), { onSuccess: onSaved }); async function submit(e: React.FormEvent) { e.preventDefault(); const n = Number(amount); if (n > 0) await payment.execute({ payment_mode: paymentMode, collected_amount: n }); } return <Modal open onClose={onClose} title="Confirm direct payment"><form onSubmit={submit} style={{ display: "grid", gap: 14 }}><p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.55 }}>Record the amount paid directly to your business. This does not charge the customer or create a platform settlement.</p>{payment.error && <Alert tone="danger">{payment.error}</Alert>}<Select label="Payment mode" value={paymentMode} onChange={e => setPaymentMode(e.target.value)} options={[{ value: "onsite_cash", label: "Cash" }, { value: "onsite_upi", label: "UPI" }, { value: "onsite_card", label: "Card at service location" }, { value: "bank_transfer", label: "Bank transfer" }]} /><Input label="Amount collected" type="number" min={0.01} step={0.01} value={amount} onChange={e => setAmount(e.target.value)} required /><div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Button type="button" variant="secondary" onClick={onClose} disabled={payment.loading}>Cancel</Button><Button type="submit" variant="primary" loading={payment.loading} disabled={Number(amount) <= 0}>Confirm payment</Button></div></form></Modal>; }

function CancelJobModal({ jobId, onClose, onSaved }: { jobId: string; onClose: () => void; onSaved: () => void }) { const [reason, setReason] = useState(""); const action = useAction((value: string) => bookingsJobsApi.cancelJob(jobId, value), { onSuccess: onSaved }); async function submit(e: React.FormEvent) { e.preventDefault(); if (reason.trim().length >= 5) await action.execute(reason.trim()); } return <Modal open onClose={onClose} title="Cancel job"><form onSubmit={submit} style={{ display: "grid", gap: 14 }}><Alert tone="warning" title="This affects provider health">The cancellation is recorded against this provider and the customer will see the job as cancelled.</Alert>{action.error && <Alert tone="danger">{action.error}</Alert>}<label style={{ display: "grid", gap: 6, color: "var(--text-secondary)", fontSize: 12, fontWeight: 600 }}>Cancellation reason<textarea rows={4} value={reason} onChange={e => setReason(e.target.value)} placeholder="Explain why your business cannot complete this job" required minLength={5} style={{ width: "100%", resize: "vertical", padding: 10, borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", font: "inherit" }} /></label><div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><Button type="button" variant="secondary" onClick={onClose} disabled={action.loading}>Keep job</Button><Button type="submit" variant="destructive" loading={action.loading} disabled={reason.trim().length < 5}>Confirm cancellation</Button></div></form></Modal>; }

const selectStyle: React.CSSProperties = { height: 42, padding: "0 12px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", font: "inherit", fontSize: 13 };
const toolbarButtonStyle: React.CSSProperties = { minHeight: 42, padding: "0 14px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-secondary)", font: "inherit", fontSize: 13, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 7, cursor: "pointer" };
const iconButtonStyle: React.CSSProperties = { position: "absolute", right: 8, top: 7, width: 25, height: 25, border: 0, borderRadius: 7, background: "transparent", color: "var(--text-tertiary)", display: "grid", placeItems: "center", cursor: "pointer" };
const filterLabelStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 5, color: "var(--text-secondary)", fontSize: 11.5, fontWeight: 600 };
const filterCountStyle: React.CSSProperties = { minWidth: 19, height: 19, borderRadius: 999, background: "var(--accent)", color: "white", fontSize: 10, display: "inline-grid", placeItems: "center", padding: "0 5px" };
const secondaryCellStyle: React.CSSProperties = { marginTop: 3, fontSize: 11, color: "var(--text-tertiary)" };
