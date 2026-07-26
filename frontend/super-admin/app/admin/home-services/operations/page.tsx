"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn } from "../../../../components/shared/ui";
import {
  homeServicesOperationsApi, type UnifiedOperationRow, type UnifiedOperationsMetrics,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import {
  Search, Download, RefreshCw, X, Briefcase, FileText, UserX, Activity,
  Clock, AlertTriangle, ExternalLink, Phone,
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

        {/* Right detail panel */}
        {selected && (
          <div role="complementary" aria-label="Operation details" style={{ width: 340, flexShrink: 0 }}>
            <Card style={{ position: "sticky", top: 12, padding: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <p style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{selected.work_id}</p>
                  {selected.booking_number && <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>Booking {selected.booking_number}</p>}
                </div>
                <button onClick={() => setSelected(null)} aria-label="Close details" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}><X size={16}/></button>
              </div>
              <Badge variant={STAGE_BADGE[selected.current_stage] ?? "muted"} size="sm">{STAGE_LABEL[selected.current_stage] ?? selected.current_stage}</Badge>

              <div style={{ marginTop: 14, fontSize: 13 }}>
                <p style={{ fontWeight: 600, margin: "0 0 2px" }}>{selected.customer_name ?? "Unknown customer"}</p>
                {selected.customer_contact_summary && (
                  <p style={{ color: "var(--text-tertiary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 4 }}>
                    <Phone size={11}/> {selected.customer_contact_summary}
                  </p>
                )}
                <p style={{ color: "var(--text-secondary)", margin: "0 0 8px" }}>{selected.master_service ?? "—"}{selected.job_type ? ` · ${selected.job_type}` : ""}</p>
                <p style={{ color: "var(--text-secondary)", margin: "0 0 4px" }}>
                  Tenant: {selected.tenant_name ?? <em>Unassigned</em>}
                </p>
                <p style={{ color: "var(--text-secondary)", margin: "0 0 4px" }}>
                  Technician: {selected.technician_name ?? <em>Unassigned</em>}
                </p>
              </div>

              {selected.current_stage === "AWAITING_APPROVAL" && (
                <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: "var(--radius-md)",
                  background: "var(--warning-bg, rgba(234,179,8,0.1))", border: "1px solid var(--warning-border, rgba(234,179,8,0.3))" }}>
                  <p style={{ fontSize: 12, fontWeight: 600, margin: 0, color: "var(--warning-text)" }}>
                    Work cannot start until estimate approval.
                  </p>
                </div>
              )}

              <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
                <p style={{ margin: "0 0 2px" }}>Schedule: {fmtDate(selected.schedule.date)} {selected.schedule.window ?? ""}</p>
                <p style={{ margin: 0 }}>SLA: <Badge variant={SLA_BADGE[selected.sla_state]} size="sm">{selected.sla_state.replace("_", " ")}</Badge></p>
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
                {selected.job_id && (
                  <Btn variant="secondary" size="sm" onClick={() => window.open(`/admin/home-services/service-jobs/${selected.job_id}`, "_blank")}>
                    Open Full Details
                  </Btn>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
