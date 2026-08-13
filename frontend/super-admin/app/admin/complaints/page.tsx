"use client";
import { useCallback, useState, useEffect, useRef } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { useApi, useAction } from "../../../hooks/useApi";
import { complaintsApi, adminComplaintPolicyApi, ComplaintPolicyRecord } from "../../../lib/api";
import { Btn, SectionHeader } from "../../../components/shared/ui";
import { AlertOctagon, Download, RefreshCw, Radio } from "lucide-react";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";

// ── Types ──────────────────────────────────────────────────────────────────────
interface ComplaintItem {
  id: string;
  complaint_number: string;
  status: string;
  priority: string;
  severity: string;
  sla_status: string;
  complaint_type: string;
  record_type: string;
  title: string;
  description: string;
  tenant_name: string;
  customer_name: string;
  customer_email: string;
  message_count: number;
  proposal_count: number;
  settlement_status: string | null;
  tenant_first_response_due_at: string | null;
  created_at: string;
  resolved_at: string | null;
}

interface ComplaintSummary {
  total: number;
  open: number;
  active: number;
  sla_breached: number;
  high_priority: number;
  pending_admin: number;
  in_ai_settlement: number;
  resolved: number;
  settled: number;
  new_today: number;
  new_this_week: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function slaLabel(s: string | null): { label: string; varBg: string; varColor: string } | null {
  if (!s) return null;
  const map: Record<string, { label: string; varBg: string; varColor: string }> = {
    on_time:   { label: "On Time",   varBg: "var(--success-bg)",  varColor: "var(--success-text)" },
    at_risk:   { label: "At Risk",   varBg: "var(--warning-bg)",  varColor: "var(--warning-text)" },
    breached:  { label: "Breached",  varBg: "var(--danger-bg)",   varColor: "var(--danger-text)"  },
    escalated: { label: "Escalated", varBg: "var(--accent-muted)",varColor: "var(--accent)"       },
  };
  return map[s] ?? null;
}

function slaCountdown(due: string | null) {
  if (!due) return null;
  const diff = new Date(due).getTime() - Date.now();
  if (diff < 0) return "OVERDUE";
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `${h}h ${m}m`;
}

function statusVars(s: string): { bg: string; color: string } {
  const map: Record<string, { bg: string; color: string }> = {
    open:                        { bg: "var(--accent-muted)",  color: "var(--accent)" },
    awaiting_provider_response:  { bg: "var(--warning-bg)",    color: "var(--warning-text)" },
    under_admin_review:          { bg: "var(--accent-muted)",  color: "var(--accent)" },
    admin_review_pending:        { bg: "var(--accent-muted)",  color: "var(--accent)" },
    resolution_proposed:         { bg: "var(--info-bg, var(--accent-muted))", color: "var(--info-text, var(--accent))" },
    ai_settlement_started:       { bg: "var(--danger-bg)",     color: "var(--danger-text)" },
    ai_waiting_customer:         { bg: "var(--warning-bg)",    color: "var(--warning-text)" },
    ai_proposal_sent:            { bg: "var(--accent-muted)",  color: "var(--accent)" },
    ai_settlement_accepted:      { bg: "var(--success-bg)",    color: "var(--success-text)" },
    settled:                     { bg: "var(--success-bg)",    color: "var(--success-text)" },
    resolved:                    { bg: "var(--success-bg)",    color: "var(--success-text)" },
    closed:                      { bg: "var(--surface-sunken)",color: "var(--text-tertiary)" },
    rejected:                    { bg: "var(--danger-bg)",     color: "var(--danger-text)" },
    cancelled:                   { bg: "var(--surface-sunken)",color: "var(--text-tertiary)" },
    tenant_no_response:          { bg: "var(--danger-bg)",     color: "var(--danger-text)" },
  };
  return map[s] ?? { bg: "var(--surface-sunken)", color: "var(--text-secondary)" };
}

function priorityVars(p: string): { bg: string; color: string } {
  const map: Record<string, { bg: string; color: string }> = {
    urgent: { bg: "var(--danger-bg)",  color: "var(--danger-text)"  },
    high:   { bg: "var(--warning-bg)", color: "var(--warning-text)" },
    normal: { bg: "var(--accent-muted)", color: "var(--accent)"     },
    low:    { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  };
  return map[p] ?? { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" };
}

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function SummaryCard({
  label, value, active, onClick,
}: { label: string; value: number; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={Boolean(active)}
      aria-label={`${label}: ${value}`}
      style={{
        background: active ? "var(--brand)" : "var(--surface)",
        border: `1.5px solid ${active ? "var(--brand)" : "var(--border)"}`,
        borderRadius: 10, padding: "14px 18px",
        cursor: "pointer", textAlign: "left", transition: "all .15s",
        flex: "1 1 140px", minWidth: 130, fontFamily: "inherit",
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, color: active ? "var(--text-on-brand)" : "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>{value}</div>
      <div style={{ fontSize: 12, color: active ? "rgba(255,255,255,.75)" : "var(--text-tertiary)", marginTop: 2 }}>{label}</div>
    </button>
  );
}

function Chip({ label, active, onClick }: {
  label: string; active?: boolean; onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={Boolean(active)}
      style={{
        padding: "4px 12px", borderRadius: 20,
        border: `1.5px solid ${active ? "var(--brand)" : "var(--border)"}`,
        background: active ? "var(--brand)" : "transparent",
        color: active ? "var(--text-on-brand)" : "var(--text-secondary)",
        cursor: "pointer", fontSize: 12, fontWeight: 500, fontFamily: "inherit",
        transition: "all .15s",
      }}
    >
      {label}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { bg, color } = statusVars(status);
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 10,
      background: bg, color, fontSize: 11, fontWeight: 600,
    }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function SLABadge({ slaStatus }: { slaStatus: string | null }) {
  const info = slaLabel(slaStatus);
  if (!info) return null;
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 10,
      background: info.varBg, color: info.varColor,
      fontSize: 11, fontWeight: 600,
    }}>
      {info.label}
    </span>
  );
}

function ComplaintRow({ item, onView, onAISettle, onFinalize }: {
  item: ComplaintItem;
  onView: (id: string) => void;
  onAISettle: (id: string) => void;
  onFinalize: (id: string, decision: string) => void;
}) {
  const slaInfo = slaLabel(item.sla_status);
  const pv = priorityVars(item.priority);
  return (
    <tr style={{ borderBottom: "1px solid var(--border)" }}>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        <div style={{ fontWeight: 600, color: "var(--accent)", fontFamily: "monospace" }}>
          {item.complaint_number}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{fmtDate(item.created_at)}</div>
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        <StatusBadge status={item.status} />
        {item.sla_status && (
          <div style={{ marginTop: 3 }}><SLABadge slaStatus={item.sla_status} /></div>
        )}
        {item.tenant_first_response_due_at && item.sla_status !== "on_time" && (
          <div style={{ fontSize: 10, color: slaInfo?.varColor ?? "var(--text-tertiary)", marginTop: 2 }}>
            {slaCountdown(item.tenant_first_response_due_at)}
          </div>
        )}
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        <span style={{
          display: "inline-block", padding: "2px 8px", borderRadius:"var(--radius-md)",
          background: pv.bg, color: pv.color, fontSize: 11, fontWeight: 600,
        }}>
          {item.priority}
        </span>
        {item.severity && (
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3 }}>
            {item.severity} severity
          </div>
        )}
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>{item.complaint_type.replace(/_/g, " ")}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{item.record_type.replace(/_/g, " ")}</div>
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13, maxWidth: 200 }}>
        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>{item.title || "(no title)"}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {item.description}
        </div>
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>{item.tenant_name ?? "—"}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{item.customer_name ?? "—"}</div>
      </td>
      <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>
        {item.message_count > 0 && <span>{item.message_count} msg</span>}
        {item.proposal_count > 0 && (
          <span style={{ marginLeft: 6, color: "var(--accent)" }}>{item.proposal_count} proposal{item.proposal_count > 1 ? "s" : ""}</span>
        )}
      </td>
      <td style={{ padding: "10px 12px" }}>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <Btn size="xs" variant="secondary" onClick={() => onView(item.id)}>View</Btn>
          {["open", "awaiting_provider_response", "tenant_review_pending", "tenant_no_response"].includes(item.status) && (
            <Btn size="xs" variant="ghost" onClick={() => onAISettle(item.id)}>AI Settle</Btn>
          )}
          {["admin_review_pending", "ai_settlement_failed", "ai_proposal_sent"].includes(item.status) && (
            <Btn size="xs" variant="success" onClick={() => onFinalize(item.id, "settle")}>Settle</Btn>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function AdminComplaintsPage() {
  const [columnState, setColumnState] = useState<ColumnDef[]>([
    { key: "complaint_number", label: "Complaint #", visible: true, order: 0 },
    { key: "status", label: "Status / SLA", visible: true, order: 1 },
    { key: "priority", label: "Priority", visible: true, order: 2 },
    { key: "complaint_type", label: "Type", visible: true, order: 3 },
    { key: "title", label: "Title", visible: true, order: 4 },
    { key: "tenant_name", label: "Tenant / customer", visible: true, order: 5 },
    { key: "activity", label: "Activity", visible: true, order: 6 },
    { key: "actions", label: "Actions", visible: true, order: 7 },
  ]);
  const [tab, setTab] = useState<"complaints" | "policies">("complaints");
  const [q, setQ]               = useState("");
  const [status, setStatus]     = useState("");
  const [slaFilter, setSla]     = useState("");
  const [priority, setPriority] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [severity, setSeverity] = useState("");
  const [recordType, setRecordType] = useState("");
  const [complaintType, setComplaintType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage]         = useState(1);
  const [pageSize]              = useState(25);
  const [sortBy, setSortBy]     = useState("created_at");
  const [sortDir, setSortDir]   = useState<"asc" | "desc">("desc");
  const [cardFilter, setCardFilter] = useState("");
  const [newToday, setNewToday] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [exporting, setExporting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: sumData } = useApi(() => complaintsApi.adminSummary(), []);
  const { data: filterOptions } = useApi(() => complaintsApi.filterOptions(), []);
  // apiFetch unwraps the standard { data } envelope, so sumData already is
  // the summary payload. Double-unwrapping hid every summary card.
  const summary: Partial<ComplaintSummary> = sumData ?? {};

  const listParams = {
    q: q || undefined,
    status: cardFilter || status || undefined,
    sla_status: slaFilter || undefined,
    priority: priority || undefined,
    tenant_id: tenantId || undefined, severity: severity || undefined,
    record_type: recordType || undefined, complaint_type: complaintType || undefined,
    date_from: dateFrom || (newToday ? (() => {
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      return start.toISOString();
    })() : undefined), date_to: dateTo || undefined,
    page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir,
  };

  const { data: listData, loading, error, refetch } = useApi(
    () => complaintsApi.adminList(listParams),
    [q, status, slaFilter, priority, tenantId, severity, recordType, complaintType, dateFrom, dateTo, page, sortBy, sortDir, cardFilter, newToday],
  );

  const items: ComplaintItem[] = (listData?.items ?? []) as unknown as ComplaintItem[];
  const meta = (listData?.meta ?? {}) as { total?: number; total_pages?: number; has_next?: boolean };

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(refetch, 30000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh, refetch]);

  const { execute: startAI } = useAction(
    useCallback(async (id: string) => {
      await complaintsApi.startAISettlement(id);
      refetch();
    }, [refetch])
  );

  const { execute: finalize } = useAction(
    useCallback(async (id: string, decision: string) => {
      await complaintsApi.finalizeSettlement(id, decision);
      refetch();
    }, [refetch])
  );

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const filters: Record<string, string> = {};
      if (q) filters.q = q;
      if (cardFilter || status) filters.status = cardFilter || status;
      if (slaFilter) filters.sla_status = slaFilter;
      if (priority) filters.priority = priority;
      if (tenantId) filters.tenant_id = tenantId;
      if (severity) filters.severity = severity;
      if (recordType) filters.record_type = recordType;
      if (complaintType) filters.complaint_type = complaintType;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;
      if (newToday && listParams.date_from) filters.date_from = listParams.date_from;
      const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const token = localStorage.getItem("serviceos_admin_token") ?? "";
      const response = await fetch(`${API_BASE}${complaintsApi.exportUrl(filters)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `complaints-${new Date().toISOString().slice(0, 10)}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      window.alert("Complaint export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  }, [q, cardFilter, status, slaFilter, priority, tenantId, severity, recordType, complaintType, dateFrom, dateTo, newToday, listParams.date_from]);

  const enterpriseFilters: Record<string, unknown> = Object.fromEntries(Object.entries(listParams).filter(([key, value]) =>
    !["page", "page_size", "sort_by", "sort_dir"].includes(key) && value !== undefined && value !== ""));
  function applySavedView(view: Record<string, unknown>, savedSort: Record<string, unknown>) {
    setQ(String(view.q ?? view.search ?? "")); setStatus(String(view.status ?? "")); setSla(String(view.sla_status ?? ""));
    setPriority(String(view.priority ?? "")); setTenantId(String(view.tenant_id ?? "")); setSeverity(String(view.severity ?? ""));
    setRecordType(String(view.record_type ?? "")); setComplaintType(String(view.complaint_type ?? ""));
    setDateFrom(String(view.date_from ?? "")); setDateTo(String(view.date_to ?? ""));
    setSortBy(String(savedSort.sort_by ?? "created_at")); setSortDir(savedSort.sort_direction === "asc" ? "asc" : "desc"); setPage(1);
  }

  const toggleSort = (col: string) => {
    if (sortBy === col) setSortDir((d: "asc" | "desc") => d === "asc" ? "desc" : "asc");
    else { setSortBy(col); setSortDir("desc"); }
  };

  const SortTh = ({ col, label }: { col: string; label: string }) => (
    <th
      onClick={() => toggleSort(col)}
      style={{
        padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 600,
        color: "var(--text-tertiary)", background: "var(--surface-sunken)",
        cursor: "pointer", userSelect: "none",
        borderBottom: "1px solid var(--border)", whiteSpace: "nowrap",
      }}
    >
      {label}{sortBy === col ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );

  const staticTh = (label: string) => (
    <th style={{
      padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 600,
      color: "var(--text-tertiary)", background: "var(--surface-sunken)",
      borderBottom: "1px solid var(--border)",
    }}>
      {label}
    </th>
  );
  const visibleComplaintColumns = new Set(columnState.filter(column => column.visible).map(column => column.key));
  const complaintColumnCss = [
    ["complaint_number", 1], ["status", 2], ["priority", 3], ["complaint_type", 4],
    ["title", 5], ["tenant_name", 6], ["activity", 7], ["actions", 8],
  ].filter(([key]) => !visibleComplaintColumns.has(String(key)))
    .map(([, position]) => `.admin-complaints-grid th:nth-child(${position}), .admin-complaints-grid td:nth-child(${position}) { display: none; }`)
    .join("\n");

  return (
    <AdminLayout activeNav="complaints">
      <div className="operations-admin-page">
        <SectionHeader
          title="Complaints & Disputes"
          subtitle="Platform-wide complaint monitoring, SLA response and governed settlement."
          icon={<AlertOctagon size={18} />}
          actions={tab === "complaints" ? (
            <>
              <Btn
                size="sm"
                variant={autoRefresh ? "success" : "secondary"}
                onClick={() => setAutoRefresh((a: boolean) => !a)}
              >
                <Radio size={14} style={{ marginRight: 5 }} />{autoRefresh ? "Live · 30s" : "Auto-refresh"}
              </Btn>
              <Btn size="sm" variant="secondary" disabled={exporting} onClick={handleExport}>
                <Download size={14} style={{ marginRight: 5 }} />{exporting ? "Exporting…" : "Export CSV"}
              </Btn>
              <Btn size="sm" variant="primary" onClick={refetch}><RefreshCw size={14} style={{ marginRight: 5 }} />Refresh</Btn>
            </>
          ) : undefined}
        />

        {/* Tabs -- Policies folded in here 2026-08-05 (was a separate
            /admin/complaint-policies page/nav item) at explicit user
            request, since it's config for this exact workflow. */}
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20 }}>
          {([["complaints", "Complaints"], ["policies", "Policies"]] as const).map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)}
              style={{ padding: "10px 16px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
                borderBottom: tab === key ? "2px solid var(--brand)" : "2px solid transparent",
                color: tab === key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer" }}>
              {label}
            </button>
          ))}
        </div>

        {tab === "policies" && <ComplaintPoliciesPanel />}

        {tab === "complaints" && <>
        <div style={{ marginBottom: 16 }}>
          <OperationsDirectoryControls resourceKey="admin_complaints" filters={enterpriseFilters}
            sort={{ sort_by: sortBy, sort_direction: sortDir }} columns={columnState}
            onApplyView={applySavedView} onColumnsChange={setColumnState} />
        </div>
        {/* Summary Cards */}
        {Object.keys(summary).length > 0 && (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
            <SummaryCard label="Total" value={summary.total ?? 0}
              active={!cardFilter && !status && !slaFilter && !priority && !newToday}
              onClick={() => { setCardFilter(""); setStatus(""); setSla(""); setPriority(""); setNewToday(false); setPage(1); }} />
            <SummaryCard label="Open" value={summary.open ?? 0}
              active={cardFilter === "open"} onClick={() => { setCardFilter("open"); setPage(1); }} />
            <SummaryCard label="SLA Breached" value={summary.sla_breached ?? 0}
              active={slaFilter === "breached"} onClick={() => { setSla(slaFilter === "breached" ? "" : "breached"); setPage(1); }} />
            <SummaryCard label="Pending Admin" value={summary.pending_admin ?? 0}
              active={cardFilter === "under_admin_review"} onClick={() => { setCardFilter("under_admin_review"); setPage(1); }} />
            <SummaryCard label="High Priority" value={summary.high_priority ?? 0}
              active={priority === "high,urgent"} onClick={() => { setPriority(priority === "high,urgent" ? "" : "high,urgent"); setPage(1); }} />
            <SummaryCard label="AI Settlement" value={summary.in_ai_settlement ?? 0}
              active={cardFilter === "ai_settlement_started"}
              onClick={() => { setCardFilter(cardFilter === "ai_settlement_started" ? "" : "ai_settlement_started"); setNewToday(false); setPage(1); }} />
            <SummaryCard label="New Today" value={summary.new_today ?? 0}
              active={newToday}
              onClick={() => { setNewToday(v => !v); setCardFilter(""); setPage(1); }} />
            <SummaryCard label="Settled" value={summary.settled ?? 0}
              active={cardFilter === "settled"} onClick={() => { setCardFilter("settled"); setPage(1); }} />
          </div>
        )}

        {/* Quick filters */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          <Chip label="All" active={!cardFilter && !status && !slaFilter && !priority && !newToday} onClick={() => { setCardFilter(""); setStatus(""); setSla(""); setPriority(""); setNewToday(false); setPage(1); }} />
          <Chip label="SLA Breached" active={slaFilter === "breached"}
            onClick={() => { setSla(slaFilter === "breached" ? "" : "breached"); setPage(1); }} />
          <Chip label="Awaiting Provider" active={status === "awaiting_provider_response"}
            onClick={() => { setStatus((s: string) => s === "awaiting_provider_response" ? "" : "awaiting_provider_response"); setPage(1); }} />
          <Chip label="AI Settlement" active={status === "ai_settlement_started"}
            onClick={() => { setStatus((s: string) => s === "ai_settlement_started" ? "" : "ai_settlement_started"); setPage(1); }} />
          <Chip label="Admin Review" active={status === "under_admin_review"}
            onClick={() => { setStatus((s: string) => s === "under_admin_review" ? "" : "under_admin_review"); setPage(1); }} />
          <Chip label="Urgent" active={priority === "urgent"}
            onClick={() => { setPriority((p: string) => p === "urgent" ? "" : "urgent"); setPage(1); }} />
        </div>

        {/* Search + Filter Bar */}
        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
          <input
            value={q}
            onChange={e => { setQ(e.target.value); setPage(1); }}
            placeholder="Search complaint #, title, customer, tenant…"
            style={{
              flex: "1 1 300px", padding: "8px 12px", borderRadius:"var(--radius-md)",
              border: "1.5px solid var(--border)", fontSize: 13, outline: "none",
              background: "var(--surface)", color: "var(--text-primary)",
            }}
          />
          <select
            value={status}
            onChange={e => { setStatus(e.target.value); setPage(1); }}
            style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="awaiting_provider_response">Awaiting Provider</option>
            <option value="tenant_no_response">Tenant No Response</option>
            <option value="under_admin_review">Under Admin Review</option>
            <option value="ai_settlement_started">AI Settlement Started</option>
            <option value="ai_proposal_sent">AI Proposal Sent</option>
            <option value="admin_review_pending">Admin Review Pending</option>
            <option value="resolution_proposed">Resolution Proposed</option>
            <option value="settled">Settled</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select
            value={priority}
            onChange={e => { setPriority(e.target.value); setPage(1); }}
            style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="high,urgent">High + Urgent</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
          <select
            value={slaFilter}
            onChange={e => { setSla(e.target.value); setPage(1); }}
            style={{ padding: "8px 12px", borderRadius:"var(--radius-md)", border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">All SLA</option>
            <option value="on_time">On Time</option>
            <option value="at_risk">At Risk</option>
            <option value="breached">Breached</option>
            <option value="escalated">Escalated</option>
          </select>
          <select value={tenantId} onChange={e => { setTenantId(e.target.value); setPage(1); }} className="operations-filter-input">
            <option value="">All Providers</option>
            {filterOptions?.tenants?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select value={severity} onChange={e => { setSeverity(e.target.value); setPage(1); }} className="operations-filter-input">
            <option value="">All Severities</option>
            {filterOptions?.severities?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select value={recordType} onChange={e => { setRecordType(e.target.value); setPage(1); }} className="operations-filter-input">
            <option value="">All Records</option>
            {filterOptions?.record_types?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select value={complaintType} onChange={e => { setComplaintType(e.target.value); setPage(1); }} className="operations-filter-input">
            <option value="">All Complaint Types</option>
            {filterOptions?.complaint_types?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <input aria-label="Complaints from date" type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1); }} className="operations-filter-input" />
          <input aria-label="Complaints to date" type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1); }} className="operations-filter-input" />
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", padding: 16, marginBottom: 16, color: "var(--danger-text)" }}>
            Could not load complaints. {String(error)}
          </div>
        )}

        {/* Table */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, overflow: "auto" }}>
          <table className="admin-complaints-grid" style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <SortTh col="created_at" label="Complaint #" />
                <SortTh col="status" label="Status / SLA" />
                <SortTh col="priority" label="Priority" />
                {staticTh("Type")}
                {staticTh("Title")}
                <SortTh col="tenant_name" label="Tenant / Customer" />
                {staticTh("Activity")}
                {staticTh("Actions")}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</td></tr>
              )}
              {!loading && items.length === 0 && (
                <tr><td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)" }}>No complaints found.</td></tr>
              )}
              {items.map((item: ComplaintItem) => (
                <ComplaintRow
                  key={item.id}
                  item={item}
                  onView={(id: string) => { window.location.href = `/admin/complaints/${id}`; }}
                  onAISettle={(id: string) => startAI(id)}
                  onFinalize={(id: string, decision: string) => finalize(id, decision)}
                />
              ))}
            </tbody>
          </table>
          {complaintColumnCss && <style>{complaintColumnCss}</style>}
        </div>

        {/* Pagination */}
        {(meta.total ?? 0) > pageSize && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, meta.total ?? 0)} of {meta.total ?? 0} complaints
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <Btn size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p: number) => p - 1)}>Prev</Btn>
              <span style={{ padding: "0 8px", fontSize: 13, color: "var(--text-secondary)" }}>
                Page {page} / {meta.total_pages ?? 1}
              </span>
              <Btn size="sm" variant="secondary" disabled={!meta.has_next} onClick={() => setPage((p: number) => p + 1)}>Next</Btn>
            </div>
          </div>
        )}
        </>}
      </div>
    </AdminLayout>
  );
}

// ── Policies tab (ported from the standalone /admin/complaint-policies page,
// removed from nav 2026-08-05 at explicit user request -- policy config for
// this exact workflow belongs alongside it, not as a separate menu item).
const policyInputStyle: React.CSSProperties = {
  border: "1px solid var(--border)", borderRadius:"var(--radius-md)", padding: "6px 12px",
  fontSize: 13, background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit",
};

function ComplaintPoliciesPanel() {
  const { data: policies, loading, error, refetch } = useApi(useCallback(() => adminComplaintPolicyApi.list(), []), []);
  const [editing, setEditing] = useState<ComplaintPolicyRecord | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<ComplaintPolicyRecord>>({});

  const saveAction = useAction(useCallback(async () => {
    if (!editing && !creating) return;
    if (creating) await adminComplaintPolicyApi.create(form);
    else await adminComplaintPolicyApi.update(editing!.id, form);
    setEditing(null);
    setCreating(false);
    refetch();
  }, [editing, creating, form, refetch]));

  const startCreate = () => {
    setEditing(null);
    setCreating(true);
    setForm({
      policy_key: "default", policy_name: "Default complaint policy",
      complaint_window_hours: 72, allow_duplicate_open_complaints: false,
      allow_rework: true, allow_refund_request: true, require_admin_review: true,
      is_active: true, ai_settlement_enabled: true,
      ai_auto_start_on_provider_failure: true, ai_settlement_max_pct: 25,
      ai_settlement_allowed_remedies: ["credit_points", "rework"],
      settlement_payout_in_credits_only: true,
    });
  };

  const startEdit = (p: ComplaintPolicyRecord) => {
    setEditing(p);
    setForm({
      complaint_window_hours:          p.complaint_window_hours,
      allow_duplicate_open_complaints: p.allow_duplicate_open_complaints,
      allow_rework:                    p.allow_rework ?? p.allow_rework_request,
      allow_refund_request:            p.allow_refund_request,
      require_admin_review:            p.require_admin_review,
      is_active:                       p.is_active,
      ai_settlement_enabled:             p.ai_settlement_enabled ?? true,
      ai_auto_start_on_provider_failure: p.ai_auto_start_on_provider_failure ?? true,
      ai_settlement_max_pct:             p.ai_settlement_max_pct ?? 25,
      ai_settlement_allowed_remedies:    p.ai_settlement_allowed_remedies ?? ["credit_points", "rework"],
      settlement_payout_in_credits_only: p.settlement_payout_in_credits_only ?? true,
    });
  };

  const BoolField = ({ label, field }: { label: string; field: keyof ComplaintPolicyRecord }) => (
    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
      <input
        type="checkbox"
        checked={!!(form as Record<string, unknown>)[field]}
        onChange={e => setForm(prev => ({ ...prev, [field]: e.target.checked }))}
        style={{ width: 16, height: 16 }}
      />
      {label}
    </label>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h2 style={{ fontSize: 16, margin: 0, color: "var(--text-primary)" }}>Complaint policies</h2>
          <p style={{ fontSize: 12, margin: "3px 0 0", color: "var(--text-tertiary)" }}>Configure response windows, review gates and settlement boundaries.</p>
        </div>
        <Btn size="sm" variant="primary" onClick={startCreate}>Create policy</Btn>
      </div>
      {loading && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>}
      {error   && <p style={{ fontSize: 13, color: "var(--danger-text)" }}>{error}</p>}
      {policies && policies.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No policies configured.</p>}

      {policies && policies.map((p: ComplaintPolicyRecord) => (
        <div key={p.id} style={{ border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20,
          background: "var(--surface)", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{p.policy_key}</p>
              {p.category_id && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Category: {p.category_id}</p>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                background: p.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
                color: p.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                {p.is_active ? "Active" : "Inactive"}
              </span>
              <button onClick={() => startEdit(p)} style={{ fontSize: 13, color: "var(--accent)", background: "none",
                border: "none", cursor: "pointer", padding: 0, fontFamily: "inherit" }}>Edit</button>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              { label: "Complaint Window", val: `${p.complaint_window_hours}h` },
              { label: "Allow Duplicates",  val: p.allow_duplicate_open_complaints ? "Yes" : "No" },
              { label: "Allow Rework",      val: p.allow_rework_request ? "Yes" : "No" },
              { label: "Allow Refund",      val: p.allow_refund_request ? "Yes" : "No" },
            ].map(({ label, val }) => (
              <div key={label} style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 10 }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>{val}</p>
              </div>
            ))}
            <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 10, gridColumn: "span 2" }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Require Admin Review</p>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                {p.require_admin_review ? "Yes" : "No"}
              </p>
            </div>
          </div>

          <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12,
            background: "var(--surface-sunken)" }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
              AI Settlement Rule
            </p>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
              The AI takes over automatically once the provider has failed to solve the complaint.
              It never pays money &mdash; compensation is credit points, funded from the provider&apos;s
              credits and then their security deposit. A case worth more than the cap goes to admin
              manual review.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                { label: "AI Settlement", val: (p.ai_settlement_enabled ?? true) ? "Enabled" : "Disabled" },
                { label: "Auto-start on provider failure",
                  val: (p.ai_auto_start_on_provider_failure ?? true) ? "Yes" : "No" },
                { label: "Max AI offer", val: `${p.ai_settlement_max_pct ?? 25}% of job value` },
                { label: "Payout", val: (p.settlement_payout_in_credits_only ?? true)
                    ? "Credit points only (never money)" : "—" },
              ].map(({ label, val }) => (
                <div key={label} style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 10 }}>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
                  <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>{val}</p>
                </div>
              ))}
              <div style={{ background: "var(--surface)", borderRadius:"var(--radius-md)", padding: 10, gridColumn: "span 2" }}>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Permitted remedies</p>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                  {(p.ai_settlement_allowed_remedies ?? ["credit_points", "rework"]).join(", ").replace(/_/g, " ")}
                </p>
              </div>
            </div>
          </div>
        </div>
      ))}

      {(editing || creating) && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "var(--surface)", borderRadius:"var(--radius-lg)", padding: 24, width: "100%",
            maxWidth: 480, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                {creating ? "Create Complaint Policy" : `Edit Policy: ${editing?.policy_key}`}
              </h2>
              <button onClick={() => { setEditing(null); setCreating(false); }} style={{ fontSize: 18, background: "none", border: "none",
                cursor: "pointer", color: "var(--text-tertiary)" }}>✕</button>
            </div>
            {creating && (
              <>
                <div>
                  <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Policy key</label>
                  <input style={{ ...policyInputStyle, width: "100%", boxSizing: "border-box" }} value={form.policy_key ?? ""}
                    onChange={e => setForm(prev => ({ ...prev, policy_key: e.target.value }))} />
                </div>
                <div>
                  <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Policy name</label>
                  <input style={{ ...policyInputStyle, width: "100%", boxSizing: "border-box" }} value={form.policy_name ?? ""}
                    onChange={e => setForm(prev => ({ ...prev, policy_name: e.target.value }))} />
                </div>
              </>
            )}
            <div>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Complaint Window (hours)
              </label>
              <input type="number" min={1} style={{ ...policyInputStyle, width: "100%", boxSizing: "border-box" }}
                value={form.complaint_window_hours ?? ""}
                onChange={e => setForm(prev => ({ ...prev, complaint_window_hours: +e.target.value }))}
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <BoolField label="Allow Duplicate Open Complaints" field="allow_duplicate_open_complaints" />
              <BoolField label="Allow Rework Requests"           field="allow_rework" />
              <BoolField label="Allow Refund Requests"           field="allow_refund_request" />
              <BoolField label="Require Admin Review"            field="require_admin_review" />
              <BoolField label="Is Active"                       field="is_active" />
            </div>

            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14,
              display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
                  AI Settlement Rule
                </p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                  You set the rule; the rest runs automatically. The AI takes over once the provider
                  has failed to solve the complaint. Running it charges the provider 20 credits.
                </p>
              </div>

              <BoolField label="Enable AI settlement" field="ai_settlement_enabled" />
              <BoolField label="Auto-start when the provider fails to solve it"
                         field="ai_auto_start_on_provider_failure" />

              <div>
                <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Maximum the AI may offer (% of job value)
                </label>
                <input type="number" min={0} max={100} step={1}
                  style={{ ...policyInputStyle, width: "100%", boxSizing: "border-box" }}
                  value={form.ai_settlement_max_pct ?? 25}
                  onChange={e => setForm(prev => ({ ...prev, ai_settlement_max_pct: +e.target.value }))}
                />
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                  A case worth more than this is escalated to admin manual review &mdash; it is never
                  quietly settled down at the cap.
                </p>
              </div>

              <div>
                <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Remedies the AI may offer
                </label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  {["credit_points", "rework", "callback", "apology", "no_action"].map(rem => {
                    const list = (form.ai_settlement_allowed_remedies ?? []) as string[];
                    const on = list.includes(rem);
                    return (
                      <label key={rem} style={{ display: "flex", alignItems: "center", gap: 6,
                        fontSize: 13, cursor: "pointer" }}>
                        <input type="checkbox" checked={on} style={{ width: 16, height: 16 }}
                          onChange={e => setForm(prev => {
                            const cur = ((prev.ai_settlement_allowed_remedies ?? []) as string[]);
                            return { ...prev, ai_settlement_allowed_remedies:
                              e.target.checked ? [...cur, rem] : cur.filter(x => x !== rem) };
                          })}
                        />
                        {rem.replace(/_/g, " ")}
                      </label>
                    );
                  })}
                </div>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
                  Refunds and every other cash remedy are deliberately absent: the platform never
                  settles a dispute with real money. Compensation is paid in credit points, deducted
                  from the provider&apos;s credits and then their security deposit.
                </p>
              </div>
            </div>
            <button onClick={() => saveAction.execute()} disabled={saveAction.loading}
              style={{ padding: "8px 0", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)", border: "none",
                cursor: "pointer", fontFamily: "inherit", background: "var(--brand)", color: "white",
                opacity: saveAction.loading ? 0.5 : 1 }}>
              {saveAction.loading ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
