"use client";
import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { AdminLayout }   from "../../../components/layout/AdminLayout";
import { Card, Badge, JobStatusBadge, Btn, Select, SectionHeader,
         Input, Skeleton, Modal } from "../../../components/shared/ui";
import { Search, RefreshCw, Download, Filter, X, AlertTriangle,
         Clock, Users, CheckCircle, TrendingUp, Activity, Wrench } from "lucide-react";
import { jobsApi, staffApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { Job, SlaAlert, StaffMember, OpsSummary } from "../../../lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface FilterState {
  q: string;
  status: string;
  job_type: string;
  sla_status: string;
  unassigned: boolean;
  date_from: string;
  date_to: string;
  sort_by: string;
  sort_dir: string;
}

const DEFAULT_FILTERS: FilterState = {
  q: "", status: "", job_type: "", sla_status: "",
  unassigned: false, date_from: "", date_to: "",
  sort_by: "created_at", sort_dir: "desc",
};

// ── Summary Card ───────────────────────────────────────────────────────────────
function SummaryCard({ label, value, icon: Icon, color, onClick, active }: {
  label: string; value: number | undefined; icon: React.ElementType;
  color: string; onClick?: () => void; active?: boolean;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: active ? `var(--surface-sunken)` : "var(--surface)",
        border: `1.5px solid ${active ? color : "var(--border)"}`,
        borderRadius: 12, padding: "16px 20px", cursor: onClick ? "pointer" : "default",
        display: "flex", alignItems: "center", gap: 14, transition: "all 0.15s",
        boxShadow: active ? `0 0 0 3px ${color}22` : "none", flex: 1, minWidth: 140,
      }}>
      <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}18`,
        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={18} color={color}/>
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
          {value ?? <span style={{ fontSize: 14, opacity: 0.5 }}>…</span>}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3, fontWeight: 500,
          textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      </div>
    </div>
  );
}

// ── Quick Filter Chip ──────────────────────────────────────────────────────────
function Chip({ label, active, color = "var(--primary)", onClick }: {
  label: string; active: boolean; color?: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      padding: "5px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600, border: "none",
      cursor: "pointer", transition: "all 0.12s",
      background: active ? color : "var(--surface-sunken)",
      color: active ? "#fff" : "var(--text-secondary)",
    }}>{label}</button>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function OperationsPage() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [reassignJob, setReassignJob] = useState<Job | null>(null);
  const [selectedStaff, setSelectedStaff] = useState("");
  const [reassignNote, setReassignNote] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── API params ──────────────────────────────────────────────────────────────
  const apiParams = useMemo(() => ({
    q: filters.q || undefined,
    status: filters.status || undefined,
    job_type: filters.job_type || undefined,
    sla_status: filters.sla_status || undefined,
    unassigned: filters.unassigned ? "true" : undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    sort_by: filters.sort_by,
    sort_dir: filters.sort_dir,
    page: String(page),
    page_size: "50",
    limit: "50",
  }), [filters, page]);

  const summary = useApi(useCallback(() => jobsApi.adminSummary(), []));
  const jobs    = useApi(useCallback(() => jobsApi.adminList(apiParams), [apiParams]));
  const sla     = useApi(useCallback(() => jobsApi.slaAlerts(), []));

  const staffList = useApi(useCallback(
    () => reassignJob?.tenant_id
      ? staffApi.listByTenant(reassignJob.tenant_id)
      : Promise.resolve({ staff: [], total: 0 }),
    [reassignJob?.tenant_id]
  ));
  const reassignAction = useAction(
    useCallback((jobId: string, staffId: string, reason: string) =>
      jobsApi.reassign(jobId, staffId, reason), [])
  );

  // ── Auto-refresh ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(() => { jobs.refetch(); summary.refetch(); sla.refetch(); }, 30000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh]);

  function refetchAll() { jobs.refetch(); summary.refetch(); sla.refetch(); }

  function setFilter<K extends keyof FilterState>(k: K, v: FilterState[K]) {
    setFilters(f => ({ ...f, [k]: v }));
    setPage(1);
  }

  function clearFilters() { setFilters(DEFAULT_FILTERS); setPage(1); }

  const hasActiveFilters = filters.q || filters.status || filters.job_type ||
    filters.sla_status || filters.unassigned || filters.date_from || filters.date_to;

  // ── Quick filter chips ──────────────────────────────────────────────────────
  function toggleSlaFilter() {
    setFilter("sla_status", filters.sla_status === "breached" ? "" : "breached");
  }
  function toggleUnassigned() { setFilter("unassigned", !filters.unassigned); }
  function toggleRework() {
    setFilter("status", filters.status === "rework_required" ? "" : "rework_required");
  }

  // ── Reassign ────────────────────────────────────────────────────────────────
  async function handleReassign() {
    if (!reassignJob || !selectedStaff) return;
    const jobId = reassignJob.job_id ?? reassignJob.id;
    const res = await reassignAction.execute(jobId, selectedStaff, reassignNote.trim());
    if (res) {
      setReassignJob(null); setSelectedStaff(""); setReassignNote("");
      refetchAll();
    }
  }

  // ── Export ──────────────────────────────────────────────────────────────────
  function handleExport() {
    const allJobs: Job[] = jobs.data?.jobs ?? [];
    if (!allJobs.length) return;
    const headers = ["Job#","Tenant","Customer","Type","Status","Staff","City","SLA","Commission","Created"];
    const rows = allJobs.map(j => [
      j.job_number, j.tenant_name ?? "", j.customer_name ?? "",
      j.job_type ?? "", j.status, j.staff_name ?? j.assigned_staff ?? "",
      j.city ?? "", j.sla_minutes ? `${j.sla_minutes}m` : "",
      j.commission_amount != null ? String(j.commission_amount) : "",
      j.created_at,
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `ops-board-${new Date().toISOString().slice(0,10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  }

  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;
  const sum: OpsSummary | null = summary.data ?? null;
  const allJobs: Job[] = jobs.data?.jobs ?? [];
  const activeStaff: StaffMember[] = (staffList.data?.staff ?? []).filter(s => s.status === "active");

  return (
    <AdminLayout activeNav="operations">
      <SectionHeader
        title="Operations Board"
        subtitle="Platform-wide real-time job monitoring"
        actions={<>
          <Chip label={autoRefresh ? "Auto ✓" : "Auto-refresh"} active={autoRefresh}
            onClick={() => setAutoRefresh(v => !v)}/>
          <Btn variant="secondary" size="sm" onClick={refetchAll}>
            <RefreshCw size={14}/> Refresh
          </Btn>
          <Btn variant="secondary" size="sm" onClick={handleExport} disabled={!allJobs.length}>
            <Download size={14}/> Export
          </Btn>
        </>}
      />

      <div style={{ marginBottom: 16, padding: "11px 16px", borderRadius: 10, background: "var(--info-bg)",
        border: "1px solid var(--info-border)", fontSize: 12, color: "var(--info-text)",
        display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <span>
          This board shows <strong>Field Ops (legacy)</strong> jobs, a separate lifecycle from Home Services bookings.
          {!allJobs.length && !jobs.loading && " It is empty because no legacy Field Ops jobs exist in this environment — this is expected, not broken."}
        </span>
        <a href="/admin/home-services/service-jobs" style={{ fontSize: 12, fontWeight: 700, color: "var(--info-text)",
          textDecoration: "underline", whiteSpace: "nowrap" }}>
          View real Home Services Jobs →
        </a>
      </div>

      {/* ── Summary Cards ─────────────────────────────────────────────────── */}
      <div style={{ display:"flex", gap:12, flexWrap:"wrap", marginBottom:20 }}>
        <SummaryCard label="Total Active" value={sum?.total_active}
          icon={Activity} color="#6366f1"/>
        <SummaryCard label="In Progress" value={sum?.in_progress}
          icon={TrendingUp} color="#22c55e"
          active={filters.status === "work_started"}
          onClick={() => setFilter("status", filters.status === "work_started" ? "" : "work_started")}/>
        <SummaryCard label="SLA Breached" value={sum?.sla_breached}
          icon={AlertTriangle} color="#ef4444"
          active={filters.sla_status === "breached"}
          onClick={toggleSlaFilter}/>
        <SummaryCard label="Unassigned" value={sum?.unassigned}
          icon={Users} color="#f59e0b"
          active={filters.unassigned}
          onClick={toggleUnassigned}/>
        <SummaryCard label="Rework" value={sum?.rework_required}
          icon={Wrench} color="#8b5cf6"
          active={filters.status === "rework_required"}
          onClick={toggleRework}/>
        <SummaryCard label="Completed Today" value={sum?.completed_today}
          icon={CheckCircle} color="#10b981"/>
      </div>

      {/* ── SLA Alert Banner ──────────────────────────────────────────────── */}
      {!sla.loading && (sla.data?.length ?? 0) > 0 && (
        <div style={{ marginBottom:16, display:"flex", flexDirection:"column", gap:8 }}>
          {(sla.data ?? []).slice(0, 3).map(a => (
            <div key={a.job_id} style={{
              display:"flex", alignItems:"center", gap:14, padding:"10px 16px",
              borderRadius:10, background: a.severity === "critical" ? "var(--danger-bg)" : "var(--warning-bg)",
              border:`1px solid ${a.severity === "critical" ? "var(--danger-border)" : "var(--warning-border)"}` }}>
              <span style={{ fontSize:16 }}>{a.severity === "critical" ? "🔴" : "🟡"}</span>
              <div style={{ flex:1 }}>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                  {a.job_number} · {a.tenant_name} — {a.status.replace(/_/g," ")}
                </p>
                <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"2px 0 0" }}>
                  SLA breached by {a.minutes_overdue}m · Severity: {a.severity.toUpperCase()}
                </p>
              </div>
              <Btn variant="secondary" size="sm"
                onClick={() => window.location.href = `/admin/operations/${a.job_id}`}>View</Btn>
            </div>
          ))}
          {(sla.data?.length ?? 0) > 3 && (
            <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"4px 0 0 4px" }}>
              +{(sla.data?.length ?? 0) - 3} more SLA alerts — use SLA Breached filter to see all
            </p>
          )}
        </div>
      )}

      {/* ── Filter Bar ────────────────────────────────────────────────────── */}
      <Card padding={14} style={{ marginBottom:16 }}>
        {/* Quick chips */}
        <div style={{ display:"flex", gap:8, marginBottom:12, flexWrap:"wrap" }}>
          <Chip label="SLA Breached" active={filters.sla_status === "breached"}
            color="#ef4444" onClick={toggleSlaFilter}/>
          <Chip label="Unassigned" active={filters.unassigned}
            color="#f59e0b" onClick={toggleUnassigned}/>
          <Chip label="Rework" active={filters.status === "rework_required"}
            color="#8b5cf6" onClick={toggleRework}/>
          <Chip label="In Progress" active={filters.status === "work_started"}
            color="#22c55e" onClick={() => setFilter("status", filters.status === "work_started" ? "" : "work_started")}/>
          <Chip label="Disputed" active={filters.status === "disputed"}
            color="#6366f1" onClick={() => setFilter("status", filters.status === "disputed" ? "" : "disputed")}/>
          {hasActiveFilters && (
            <button onClick={clearFilters} style={{
              padding:"5px 10px", borderRadius:20, fontSize:12, fontWeight:600,
              border:"none", cursor:"pointer", background:"var(--danger-bg)",
              color:"var(--danger-text)", display:"flex", alignItems:"center", gap:4 }}>
              <X size={11}/> Clear all
            </button>
          )}
        </div>
        {/* Main filter row */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr auto auto auto auto", gap:10, alignItems:"end" }}>
          <Input placeholder="Search job#, customer, tenant, city…" value={filters.q}
            onChange={v => setFilter("q", v)} icon={<Search size={14}/>}/>
          <Select label="" value={filters.status} onChange={v => setFilter("status", v)}
            placeholder="All statuses" options={[
              { value:"pending_assignment", label:"Pending Assignment" },
              { value:"assigned",           label:"Assigned"           },
              { value:"accepted",           label:"Accepted"           },
              { value:"en_route",           label:"En Route"           },
              { value:"arrived",            label:"Arrived"            },
              { value:"work_started",       label:"In Progress"        },
              { value:"parts_required",     label:"Parts Required"     },
              { value:"quality_check",      label:"Quality Check"      },
              { value:"rework_required",    label:"Rework Required"    },
              { value:"pending_sign_off",   label:"Pending Sign-off"   },
              { value:"invoice_generated",  label:"Invoice Generated"  },
              { value:"payment_pending",    label:"Payment Pending"    },
              { value:"completed",          label:"Completed"          },
              { value:"cancelled",          label:"Cancelled"          },
            ]}/>
          <Select label="" value={filters.job_type} onChange={v => setFilter("job_type", v)}
            placeholder="All types" options={[
              { value:"repair",       label:"Repair"       },
              { value:"service",      label:"Service"      },
              { value:"consultation", label:"Consultation" },
            ]}/>
          <Btn variant={showAdvanced ? "primary" : "secondary"} size="sm"
            onClick={() => setShowAdvanced(v => !v)}>
            <Filter size={13}/> {showAdvanced ? "Hide" : "Filters"}
          </Btn>
          <Select label="" value={`${filters.sort_by}:${filters.sort_dir}`}
            onChange={v => { const [by,dir] = v.split(":"); setFilter("sort_by", by); setFilter("sort_dir", dir); }}
            placeholder="Sort" options={[
              { value:"created_at:desc",       label:"Newest first"       },
              { value:"created_at:asc",        label:"Oldest first"       },
              { value:"minutes_in_status:desc", label:"Longest in status"  },
              { value:"scheduled_at:asc",      label:"Scheduled (early)"  },
            ]}/>
        </div>
        {/* Advanced filters */}
        {showAdvanced && (
          <div style={{ marginTop:14, paddingTop:14, borderTop:"1px solid var(--border)",
            display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
            <div>
              <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                SLA Status
              </label>
              <Select label="" value={filters.sla_status} onChange={v => setFilter("sla_status", v)}
                placeholder="Any SLA status" options={[
                  { value:"breached", label:"SLA Breached" },
                  { value:"at_risk",  label:"At Risk"      },
                ]}/>
            </div>
            <div>
              <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                Created From
              </label>
              <input type="date" value={filters.date_from}
                onChange={e => setFilter("date_from", e.target.value)}
                style={{ width:"100%", height:38, padding:"0 10px", fontSize:13,
                  borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", fontFamily:"inherit", outline:"none", boxSizing:"border-box" }}/>
            </div>
            <div>
              <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                Created To
              </label>
              <input type="date" value={filters.date_to}
                onChange={e => setFilter("date_to", e.target.value)}
                style={{ width:"100%", height:38, padding:"0 10px", fontSize:13,
                  borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", fontFamily:"inherit", outline:"none", boxSizing:"border-box" }}/>
            </div>
          </div>
        )}
      </Card>

      {/* ── Error State ───────────────────────────────────────────────────── */}
      {jobs.error && (
        <div style={{ padding:"14px 18px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0, fontWeight:500 }}>
            {jobs.error}
          </p>
        </div>
      )}

      {/* ── Jobs Table ────────────────────────────────────────────────────── */}
      <Card padding={0} style={{ overflow:"hidden" }}>
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", minWidth:1100 }}>
            <thead>
              <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                {[
                  "Job #", "Tenant", "Customer", "Type", "Status",
                  "Staff", "SLA", "Location", "Revenue", ""
                ].map(h => (
                  <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontSize:11,
                    fontWeight:700, color:"var(--text-tertiary)",
                    letterSpacing:"0.06em", textTransform:"uppercase", whiteSpace:"nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.loading ? (
                [...Array(8)].map((_, i) => (
                  <tr key={i}><td colSpan={10} style={{ padding:"10px 14px" }}><Skeleton height={18}/></td></tr>
                ))
              ) : allJobs.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding:"60px 20px", textAlign:"center" }}>
                    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:12 }}>
                      <Activity size={36} style={{ opacity:0.2 }}/>
                      <p style={{ fontSize:14, color:"var(--text-tertiary)", margin:0, fontWeight:500 }}>
                        {hasActiveFilters ? "No jobs match your filters" : "No jobs yet"}
                      </p>
                      {hasActiveFilters && (
                        <Btn variant="secondary" size="sm" onClick={clearFilters}>Clear filters</Btn>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                allJobs.map((j, i) => {
                  const breached  = j.sla_breached;
                  const atRisk    = j.sla_breach && !j.sla_breached;
                  const disputed  = j.status === "disputed";
                  const rework    = j.status === "rework_required";
                  const rowBg = breached || disputed ? "var(--danger-bg)"
                    : (atRisk || rework) ? "var(--warning-bg)" : "transparent";
                  const rev = j.final_price ?? j.quoted_price;
                  return (
                    <JobRow key={j.job_id ?? j.id} j={j} index={i} total={allJobs.length}
                      rowBg={rowBg} rev={rev} fmt={fmt}
                      onView={() => window.location.href = `/admin/operations/${j.job_id ?? j.id}`}
                      onReassign={() => { setReassignJob(j); setSelectedStaff(""); setReassignNote(""); }}/>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        {!jobs.loading && allJobs.length > 0 && (
          <div style={{ padding:"12px 16px", borderTop:"1px solid var(--border)",
            display:"flex", alignItems:"center", justifyContent:"space-between" }}>
            <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
              {allJobs.length} jobs on this page
            </span>
            <div style={{ display:"flex", gap:8 }}>
              <Btn variant="secondary" size="sm" disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}>← Prev</Btn>
              <span style={{ fontSize:12, color:"var(--text-secondary)", padding:"0 8px",
                display:"flex", alignItems:"center" }}>Page {page}</span>
              <Btn variant="secondary" size="sm" disabled={!jobs.data?.has_next}
                onClick={() => setPage(p => p + 1)}>Next →</Btn>
            </div>
          </div>
        )}
      </Card>

      {/* ── Reassign Modal ────────────────────────────────────────────────── */}
      <Modal open={!!reassignJob} onClose={() => setReassignJob(null)} title="Reassign Staff">
        {reassignJob && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ padding:"10px 14px", borderRadius:8, background:"var(--surface-sunken)",
              border:"1px solid var(--border)" }}>
              <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>
                {reassignJob.job_number} — {reassignJob.tenant_name}
              </p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                Status: {reassignJob.status.replace(/_/g," ")}
                {reassignJob.sla_breached && " · SLA Breached"}
              </p>
            </div>
            <div>
              <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
                display:"block", marginBottom:6 }}>Assign to Staff *</label>
              {staffList.loading ? <Skeleton height={38}/> : activeStaff.length === 0 ? (
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>
                  No active staff found for this tenant.
                </p>
              ) : (
                <select value={selectedStaff} onChange={e => setSelectedStaff(e.target.value)}
                  style={{ width:"100%", height:38, padding:"0 10px", fontSize:13, fontFamily:"inherit",
                    borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                    color:"var(--text-primary)", outline:"none" }}>
                  <option value="">Select staff member…</option>
                  {activeStaff.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.full_name}{s.rating != null ? ` ★${s.rating.toFixed(1)}` : ""}{s.jobs_today != null ? ` · ${s.jobs_today} jobs today` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)",
                display:"block", marginBottom:6 }}>Reason</label>
              <textarea value={reassignNote} onChange={e => setReassignNote(e.target.value)}
                placeholder="e.g. Original staff unavailable…" rows={3}
                style={{ width:"100%", padding:"8px 10px", fontSize:13, fontFamily:"inherit",
                  borderRadius:8, border:"1px solid var(--border)", background:"var(--surface)",
                  color:"var(--text-primary)", outline:"none", resize:"vertical", boxSizing:"border-box" }}/>
            </div>
            {reassignAction.error && (
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{reassignAction.error}</p>
            )}
            <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
              <Btn variant="secondary" size="sm" onClick={() => setReassignJob(null)}>Cancel</Btn>
              <Btn variant="primary" size="sm" loading={reassignAction.loading}
                disabled={!selectedStaff} onClick={handleReassign}>
                Reassign Job
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}

// ── JobRow component (hooks at top level, not inside map) ──────────────────────
function JobRow({ j, index, total, rowBg, rev, fmt, onView, onReassign }: {
  j: Job; index: number; total: number;
  rowBg: string; rev: number | undefined;
  fmt: (n: number) => string;
  onView: () => void; onReassign: () => void;
}) {
  const [hov, setHov] = React.useState(false);
  const slaLabel = j.sla_breached ? "Breached" : j.sla_breach ? "At Risk" : null;
  const slaColor = j.sla_breached ? "var(--danger-text)" : "var(--warning-text)";
  return (
    <tr
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={onView}
      style={{
        borderBottom: index < total - 1 ? "1px solid var(--border)" : "none",
        background: hov ? "var(--surface-sunken)" : rowBg,
        cursor: "pointer", transition: "background 0.1s",
      }}>
      <td style={{ padding:"11px 14px", fontSize:12, fontWeight:700, color:"var(--text-link)", whiteSpace:"nowrap" }}>
        {j.job_number}
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-primary)", maxWidth:130 }}>
        <span style={{ display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {j.tenant_name ?? "—"}
        </span>
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-secondary)", maxWidth:120 }}>
        <span style={{ display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {j.customer_name ?? "—"}
        </span>
      </td>
      <td style={{ padding:"11px 14px" }}>
        <span style={{ fontSize:11, fontWeight:600, padding:"2px 7px", borderRadius:5,
          background:"var(--surface-sunken)", color:"var(--text-secondary)",
          textTransform:"capitalize" }}>{j.job_type ?? "—"}</span>
      </td>
      <td style={{ padding:"11px 14px" }}>
        <JobStatusBadge status={j.status}/>
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-secondary)", maxWidth:110 }}>
        {j.staff_name ?? j.assigned_staff ? (
          <span style={{ display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
            {j.staff_name ?? j.assigned_staff}
          </span>
        ) : (
          <span style={{ color:"var(--warning-text)", fontWeight:600, fontSize:11 }}>Unassigned</span>
        )}
      </td>
      <td style={{ padding:"11px 14px", whiteSpace:"nowrap" }}>
        {slaLabel ? (
          <span style={{ fontSize:11, fontWeight:700, color:slaColor }}>
            {slaLabel}
            {j.sla_breach_level && <span style={{ opacity:0.7 }}> · {j.sla_breach_level}</span>}
          </span>
        ) : j.sla_minutes ? (
          <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
            {j.minutes_in_status ?? 0}m / {j.sla_minutes}m
          </span>
        ) : (
          <span style={{ color:"var(--text-tertiary)", fontSize:12 }}>—</span>
        )}
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>
        {j.city ?? j.zipcode ?? "—"}
      </td>
      <td style={{ padding:"11px 14px", fontSize:12, fontWeight:600, color:"var(--success-text)", whiteSpace:"nowrap" }}>
        {rev != null ? fmt(rev) : "—"}
      </td>
      <td style={{ padding:"11px 14px" }} onClick={e => e.stopPropagation()}>
        <div style={{ display:"flex", gap:6 }}>
          <Btn variant="ghost" size="sm" onClick={onView}>View</Btn>
          {!j.assigned_staff_id && (
            <Btn variant="secondary" size="sm" onClick={onReassign}>Assign</Btn>
          )}
        </div>
      </td>
    </tr>
  );
}
