"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Skeleton, Input } from "../../../../components/shared/ui";
import {
  homeServicesOperationsApi, type UnifiedOperationRow, type UnifiedOperationsMetrics,
  finalRecordsAdminApi, adminExecutionApi, adminBookingsApi, adminReviewApi, adminHomeServiceBookingApi,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Search, Download, RefreshCw, X, Briefcase, FileText, UserX, Activity,
  Clock, AlertTriangle, ExternalLink, Phone, Star, Pencil, SlidersHorizontal,
  ChevronLeft, ChevronRight,
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
const TAB_KEYS = new Set<TabKey>(TABS.map(tab => tab.key));

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
const STAGE_KEYS = Object.keys(STAGE_LABEL);
const SLA_BADGE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  ON_TRACK: "success", AT_RISK: "warning", BREACHED: "danger", NOT_APPLICABLE: "muted",
};

function fmtDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

const filterLabelStyle: React.CSSProperties = {
  display: "flex", flexDirection: "column", gap: 5, minWidth: 0,
  fontSize: 11, fontWeight: 650, color: "var(--text-tertiary)",
};
const filterControlStyle: React.CSSProperties = {
  width: "100%", height: 36, padding: "0 10px", boxSizing: "border-box",
  borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", fontSize: 12, fontFamily: "inherit",
};

function FilterChip({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <span style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 9px",
      borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
      {label}<button type="button" aria-label={`Clear ${label}`} onClick={onClear}
        style={{ border: 0, background: "none", color: "var(--text-tertiary)", cursor: "pointer", padding: 0, display: "flex" }}><X size={11}/></button>
    </span>
  );
}

function DebouncedFilterInput({ value, onCommit, placeholder }: { value: string; onCommit: (value: string) => void; placeholder: string }) {
  const [input, setInput] = useState(value);
  useEffect(() => setInput(value), [value]);
  useEffect(() => {
    const timer = setTimeout(() => { if (input !== value) onCommit(input.trim()); }, 350);
    return () => clearTimeout(timer);
  }, [input, value, onCommit]);
  return <input value={input} onChange={event => setInput(event.target.value)} placeholder={placeholder} style={filterControlStyle}/>;
}

function ProviderFilter({ tenantId, tenantName, onChange }: {
  tenantId: string; tenantName: string; onChange: (id: string | null, name: string | null) => void;
}) {
  const [query, setQuery] = useState(tenantName);
  const [open, setOpen] = useState(false);
  useEffect(() => setQuery(tenantName), [tenantName]);
  const matches = useApi(useCallback(
    () => adminBookingsApi.tenantSearch(query.trim()), [query]), [query], { enabled: open && query.trim().length >= 2 });
  return (
    <label style={{ ...filterLabelStyle, position: "relative" }}>Provider
      <input value={query} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onChange={event => { setQuery(event.target.value); setOpen(true); if (!event.target.value) onChange(null, null); }}
        placeholder="Search provider" style={filterControlStyle}/>
      {open && query.trim().length >= 2 && (
        <div style={{ position: "absolute", zIndex: 20, left: 0, right: 0, top: 58, maxHeight: 220, overflowY: "auto",
          border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", boxShadow: "var(--shadow-lg)" }}>
          {matches.loading ? <div style={{ padding: 10, fontSize: 12, color: "var(--text-tertiary)" }}>Searching…</div>
            : (matches.data?.tenants ?? []).length === 0 ? <div style={{ padding: 10, fontSize: 12, color: "var(--text-tertiary)" }}>No providers found</div>
            : matches.data!.tenants.map(tenant => (
              <button type="button" key={tenant.id} onMouseDown={event => event.preventDefault()}
                onClick={() => { onChange(tenant.id, tenant.name); setQuery(tenant.name); setOpen(false); }}
                style={{ width: "100%", padding: "9px 10px", textAlign: "left", border: 0, borderBottom: "1px solid var(--border)", background: "transparent", color: "var(--text-primary)", cursor: "pointer", fontSize: 12 }}>
                <strong>{tenant.name || tenant.id.slice(0, 8)}</strong>{tenant.city ? <span style={{ color: "var(--text-tertiary)" }}> · {tenant.city}</span> : null}
              </button>
            ))}
        </div>
      )}
      {tenantId && <span style={{ position: "absolute", right: 8, top: 32, fontSize: 10, color: "var(--success-text)" }}>Selected</span>}
    </label>
  );
}

export default function HomeServicesOperationsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const rawView = params.get("view") as TabKey | null;
  const view: TabKey = rawView && TAB_KEYS.has(rawView) ? rawView : "all";
  const search = params.get("search") || "";
  const rawStage = params.get("stage") || "";
  const stage = !rawStage || STAGE_KEYS.includes(rawStage) ? rawStage : "";
  const assignment = ["assigned", "unassigned"].includes(params.get("assignment") || "") ? params.get("assignment") || "" : "";
  const city = params.get("city") || "";
  const dateFrom = params.get("date_from") || "";
  const dateTo = params.get("date_to") || "";
  const tenantId = params.get("tenant_id") || "";
  const tenantName = params.get("tenant_name") || "";
  const rawPage = Number(params.get("page") || "1");
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const rawPageSize = Number(params.get("page_size") || "25");
  const pageSize = [10, 25, 50, 100].includes(rawPageSize) ? rawPageSize : 25;
  const [searchInput, setSearchInput] = useState(search);
  const [selected, setSelected] = useState<UnifiedOperationRow | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(Boolean(assignment || city || dateFrom || dateTo || tenantId || stage));
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const updateParams = useCallback((updates: Record<string, string | null>, resetPage = true) => {
    const next = new URLSearchParams(params.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value) next.set(key, value); else next.delete(key);
    });
    if (resetPage && !(Object.keys(updates).length === 1 && "page" in updates)) next.delete("page");
    const query = next.toString();
    router.push(query ? `${pathname}?${query}` : pathname);
  }, [params, pathname, router]);

  function setParam(key: string, value: string | null) {
    updateParams({ [key]: value });
  }

  // Debounced search -> URL param
  useEffect(() => {
    const t = setTimeout(() => { if (searchInput !== search) updateParams({ search: searchInput.trim() || null }); }, 400);
    return () => clearTimeout(t);
  }, [searchInput, search, updateParams]);

  const listApi = useApi(useCallback(() => homeServicesOperationsApi.list({
    view, search: search || undefined, stage: stage || undefined,
    assignment: assignment || undefined, city: city || undefined,
    tenant_id: tenantId || undefined, date_from: dateFrom || undefined,
    date_to: dateTo || undefined, page, page_size: pageSize,
  }), [view, search, stage, assignment, city, tenantId, dateFrom, dateTo, page, pageSize]),
  [view, search, stage, assignment, city, tenantId, dateFrom, dateTo, page, pageSize]);

  // The KPI tiles are served from a short-lived cache (counting every job is a
  // full table pass). `forceMetrics` bumps on Refresh so the admin's explicit
  // ask bypasses that cache; ordinary navigation reads it.
  const [forceMetrics, setForceMetrics] = useState(0);
  const metricsApi = useApi(
    useCallback(() => homeServicesOperationsApi.summary(tenantId || undefined, forceMetrics > 0),
      [tenantId, forceMetrics]),
    [tenantId, forceMetrics]);

  const records = listApi.data?.records ?? [];
  const pagination = listApi.data?.pagination;
  const metrics = metricsApi.data as UnifiedOperationsMetrics | null;

  const activeFilterCount = [search, stage, assignment, city, tenantId, dateFrom, dateTo].filter(Boolean).length;

  async function exportCsv() {
    setExporting(true); setExportError(null);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = (typeof window !== "undefined" ? localStorage.getItem("serviceos_admin_token") : null) ?? "";
    const path = homeServicesOperationsApi.exportUrl({ view, search: search || undefined, stage: stage || undefined,
      assignment: assignment || undefined, city: city || undefined, tenant_id: tenantId || undefined,
      date_from: dateFrom || undefined, date_to: dateTo || undefined });
    try {
      const response = await fetch(path.startsWith("http") ? path : `${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      const truncated = response.headers.get("x-export-truncated") === "true";
      const exportTotal = response.headers.get("x-export-total");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `home-services-operations-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      if (truncated) setExportError(`Exported the first 5,000 of ${exportTotal ?? "all matching"} records. Narrow the filters for a complete file.`);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  const METRIC_TILES: { key: string; label: string; value: number | undefined; icon: React.ReactNode; onClick: () => void; tooltip: string }[] = [
    { key: "active", label: "Active", value: metrics?.active, icon: <Briefcase size={16}/>, tooltip: "Every request/job not yet completed or closed",
      onClick: () => updateParams({ view: "active", stage: null }) },
    { key: "new_requests", label: "New Requests", value: metrics?.new_requests, icon: <FileText size={16}/>, tooltip: "Booking drafts not yet confirmed into a job",
      onClick: () => updateParams({ view: "requests", stage: null }) },
    { key: "unassigned", label: "Unassigned", value: metrics?.unassigned, icon: <UserX size={16}/>, tooltip: "Jobs with no technician assigned yet",
      onClick: () => updateParams({ view: null, stage: "UNASSIGNED" }) },
    { key: "in_progress", label: "In Progress", value: metrics?.in_progress, icon: <Activity size={16}/>, tooltip: "Work has started, not yet done",
      onClick: () => updateParams({ view: null, stage: "IN_PROGRESS" }) },
    { key: "awaiting_approval", label: "Awaiting Approval", value: metrics?.awaiting_approval, icon: <Clock size={16}/>, tooltip: "Estimate sent, waiting on customer approval",
      onClick: () => updateParams({ view: "approval", stage: null }) },
    { key: "at_risk", label: "At Risk", value: metrics?.at_risk, icon: <AlertTriangle size={16}/>, tooltip: "SLA breached or an operational exception",
      onClick: () => updateParams({ view: "exceptions", stage: null }) },
  ];

  return (
    <AdminLayout activeNav="home-services-operations">
      <div style={{ padding: "0 4px", display: "flex", gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 18, flexWrap: "wrap" }}>
            <div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Operations / Home Services</p>
              <h1 style={{ fontSize: 24, fontWeight: 750, margin: "0 0 4px", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>Bookings & Jobs</h1>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                One canonical workspace from customer request through job completion.
              </p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => { listApi.refetch(); setForceMetrics(n => n + 1); }}><RefreshCw size={14} style={{ marginRight: 5 }}/>Refresh</Btn>
              <Btn variant="secondary" size="sm" onClick={exportCsv} loading={exporting}><Download size={14} style={{ marginRight: 5 }}/>Export CSV</Btn>
            </div>
          </div>
          {exportError && <div role="alert" style={{ marginBottom: 12, fontSize: 12, color: "var(--danger-text)" }}>{exportError}</div>}

          {/* Metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(138px, 1fr))", gap: 10, marginBottom: 18 }}>
            {METRIC_TILES.map(t => (
              <button key={t.key} onClick={t.onClick} title={t.tooltip}
                style={{ textAlign: "left", padding: "12px 14px", borderRadius: "var(--radius-lg)",
                  border: "1px solid var(--border)", background: "linear-gradient(145deg, var(--surface), var(--surface-sunken))", cursor: "pointer",
                  boxShadow: "var(--shadow-xs)" }}>
                <div style={{ color: "var(--brand)", marginBottom: 8 }}>{t.icon}</div>
                <div style={{ fontSize: 22, fontWeight: 750, color: "var(--text-primary)", lineHeight: 1 }}>
                  {metricsApi.loading ? "—" : t.value ?? 0}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{t.label}</div>
              </button>
            ))}
          </div>
          {/* Say how old the tiles are rather than letting them imply they are
              live — they are computed at most once a minute. */}
          {metrics?.computed_at && (
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "-10px 0 14px" }}>
              Counts as of {new Date(metrics.computed_at).toLocaleTimeString("en-IN",
                { hour: "2-digit", minute: "2-digit" })}
              {metrics.freshness === "stale" && " · refreshing…"}
            </div>
          )}
          {metricsApi.error && (
            <div role="alert" style={{ fontSize: 11, color: "var(--danger-text)", margin: "-10px 0 14px" }}>
              Counts unavailable: {metricsApi.error}
            </div>
          )}

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
          <Card style={{ padding: 12, marginBottom: 14 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: "1 1 240px" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
                placeholder="Booking, job, customer, tenant…" aria-label="Search operations"
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
            </div>
            <Btn variant={filtersOpen ? "secondary" : "ghost"} size="sm" onClick={() => setFiltersOpen(v => !v)}>
              <SlidersHorizontal size={14} style={{ marginRight: 5 }}/>Filters{activeFilterCount ? ` (${activeFilterCount})` : ""}
            </Btn>
            {activeFilterCount > 0 && (
              <Btn variant="ghost" size="sm" onClick={() => {
                setSearchInput("");
                updateParams({ search: null, stage: null, assignment: null, city: null, tenant_id: null,
                  tenant_name: null, date_from: null, date_to: null });
              }}>Clear all</Btn>
            )}
          </div>
          {filtersOpen && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(165px, 1fr))", gap: 10, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <label style={filterLabelStyle}>Stage
                <select value={stage} onChange={e => setParam("stage", e.target.value || null)} style={filterControlStyle}>
                  <option value="">All stages</option>
                  {STAGE_KEYS.map(key => <option key={key} value={key}>{STAGE_LABEL[key]}</option>)}
                </select>
              </label>
              <label style={filterLabelStyle}>Assignment
                <select value={assignment} onChange={e => setParam("assignment", e.target.value || null)} style={filterControlStyle}>
                  <option value="">Any assignment</option><option value="unassigned">Unassigned</option><option value="assigned">Assigned</option>
                </select>
              </label>
              <ProviderFilter tenantId={tenantId} tenantName={tenantName} onChange={(id, name) => updateParams({ tenant_id: id, tenant_name: name })}/>
              <label style={filterLabelStyle}>City
                <DebouncedFilterInput value={city} onCommit={value => updateParams({ city: value || null })} placeholder="Any city"/>
              </label>
              <label style={filterLabelStyle}>Created from
                <input type="date" value={dateFrom} max={dateTo || undefined} onChange={e => setParam("date_from", e.target.value || null)} style={filterControlStyle}/>
              </label>
              <label style={filterLabelStyle}>Created to
                <input type="date" value={dateTo} min={dateFrom || undefined} onChange={e => setParam("date_to", e.target.value || null)} style={filterControlStyle}/>
              </label>
            </div>
          )}
          </Card>
          {(search || stage || assignment || city || tenantId || dateFrom || dateTo) && (
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
              {assignment && <FilterChip label={`Assignment: ${assignment}`} onClear={() => setParam("assignment", null)}/>}
              {city && <FilterChip label={`City: ${city}`} onClear={() => setParam("city", null)}/>}
              {tenantId && <FilterChip label={`Provider: ${tenantName || tenantId.slice(0, 8)}`} onClear={() => updateParams({ tenant_id: null, tenant_name: null })}/>}
              {(dateFrom || dateTo) && <FilterChip label={`Created: ${dateFrom || "Any"} – ${dateTo || "Today"}`} onClear={() => updateParams({ date_from: null, date_to: null })}/>}
            </div>
          )}

          {listApi.data?.unknown_statuses?.length ? (
            <div role="alert" style={{ padding: "10px 12px", marginBottom: 12, borderRadius: 8, border: "1px solid var(--warning-border)", background: "var(--warning-bg)", color: "var(--warning-text)", fontSize: 12 }}>
              {listApi.data.unknown_statuses.length} unmapped workflow status{listApi.data.unknown_statuses.length === 1 ? "" : "es"} need configuration review.
            </div>
          ) : null}

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
            {pagination && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "11px 14px", borderTop: "1px solid var(--border)", flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    {pagination.total === 0 ? "No records" : `${(pagination.page - 1) * pagination.page_size + 1}–${Math.min(pagination.page * pagination.page_size, pagination.total)} of ${pagination.total.toLocaleString("en-IN")}`}
                  </span>
                  <label style={{ fontSize: 11, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 6 }}>
                    Rows
                    <select value={pageSize} onChange={event => updateParams({ page_size: event.target.value, page: null })}
                      style={{ ...filterControlStyle, width: 66, height: 30 }}>
                      {[10, 25, 50, 100].map(size => <option key={size}>{size}</option>)}
                    </select>
                  </label>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", marginRight: 4 }}>Page {pagination.page} of {pagination.total_pages}</span>
                  <Btn variant="ghost" size="sm" disabled={page <= 1} onClick={() => setParam("page", "1")} aria-label="First page"><ChevronLeft size={13}/><ChevronLeft size={13} style={{ marginLeft: -8 }}/></Btn>
                  <Btn variant="ghost" size="sm" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}><ChevronLeft size={13}/>Previous</Btn>
                  <Btn variant="ghost" size="sm" disabled={page >= pagination.total_pages} onClick={() => setParam("page", String(page + 1))}>Next<ChevronRight size={13}/></Btn>
                  <Btn variant="ghost" size="sm" disabled={page >= pagination.total_pages} onClick={() => setParam("page", String(pagination.total_pages))} aria-label="Last page"><ChevronRight size={13}/><ChevronRight size={13} style={{ marginLeft: -8 }}/></Btn>
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
    [row.job_id]), [row.job_id]);
  const execTimeline = useApi(useCallback(
    () => row.job_id ? adminExecutionApi.getJobTimeline(row.job_id) : Promise.resolve([]),
    [row.job_id]), [row.job_id]);
  const jobNotes = useApi(useCallback(
    () => row.job_id ? adminExecutionApi.getJobNotes(row.job_id) : Promise.resolve([]),
    [row.job_id]), [row.job_id]);
  const draft = useApi(useCallback(
    () => !row.job_id && row.draft_id ? adminHomeServiceBookingApi.getDraft(row.draft_id) : Promise.resolve(null),
    [row.job_id, row.draft_id]), [row.job_id, row.draft_id]);
  const draftEvents = useApi(useCallback(
    () => !row.job_id && row.draft_id ? adminHomeServiceBookingApi.getDraftEvents(row.draft_id) : Promise.resolve(null),
    [row.job_id, row.draft_id]), [row.job_id, row.draft_id]);

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
  const priceSnapshot = (j?.booking?.price_snapshot ?? (row.amount_summary.source !== "none" ? row.amount_summary : null)) as Record<string, unknown> | null | undefined;
  const events = execTimeline.data ?? [];
  const bookingEvents = draftEvents.data?.events ?? [];
  const loadingDetail = row.job_id ? (job.loading || execTimeline.loading) : (draft.loading || draftEvents.loading);

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
    : bookingEvents.map(ev => ({ key: ev.id, when: ev.created_at, label: ev.message || ev.event_type.replace(/_/g, " ") }));

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
              {!row.job_id && draft.data?.issue_summary && (
                <div style={{ margin: "0 0 10px", padding: "9px 10px", borderRadius: 8, background: "var(--surface-sunken)", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  <strong style={{ color: "var(--text-primary)" }}>Customer issue: </strong>{draft.data.issue_summary}
                </div>
              )}
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
