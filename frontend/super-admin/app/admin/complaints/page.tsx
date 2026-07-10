"use client";
import { useCallback, useState, useEffect, useRef } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { useApi, useAction } from "../../../hooks/useApi";
import { complaintsApi } from "../../../lib/api";
import { Btn } from "../../../components/shared/ui";

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
          display: "inline-block", padding: "2px 8px", borderRadius: 8,
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
  const [q, setQ]               = useState("");
  const [status, setStatus]     = useState("");
  const [slaFilter, setSla]     = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage]         = useState(1);
  const [pageSize]              = useState(25);
  const [sortBy, setSortBy]     = useState("created_at");
  const [sortDir, setSortDir]   = useState<"asc" | "desc">("desc");
  const [cardFilter, setCardFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: sumData } = useApi(() => complaintsApi.adminSummary(), []);
  const summary: ComplaintSummary = (sumData?.data ?? {}) as ComplaintSummary;

  const listParams = {
    q: q || undefined,
    status: cardFilter || status || undefined,
    sla_status: slaFilter || undefined,
    priority: priority || undefined,
    page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir,
  };

  const { data: listData, loading, error, refetch } = useApi(
    () => complaintsApi.adminList(listParams),
    [q, status, slaFilter, priority, page, sortBy, sortDir, cardFilter],
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

  const handleExport = useCallback(() => {
    const rows = [
      ["Complaint #", "Status", "Priority", "Severity", "SLA", "Type", "Title", "Tenant", "Customer", "Created"],
      ...items.map((c: ComplaintItem) => [
        c.complaint_number, c.status, c.priority, c.severity ?? "", c.sla_status ?? "",
        c.complaint_type, c.title ?? "", c.tenant_name ?? "", c.customer_name ?? "", c.created_at ?? "",
      ]),
    ];
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
      download: `complaints-${new Date().toISOString().slice(0, 10)}.csv`,
    });
    a.click();
  }, [items]);

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

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1400, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, gap: 16, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>Complaints & Disputes</h1>
            <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--text-tertiary)" }}>
              Platform-wide complaint monitoring with SLA tracking and AI settlement
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn
              size="sm"
              variant={autoRefresh ? "success" : "secondary"}
              onClick={() => setAutoRefresh((a: boolean) => !a)}
            >
              {autoRefresh ? "● Live" : "Auto-refresh"}
            </Btn>
            <Btn size="sm" variant="secondary" onClick={handleExport}>Export CSV</Btn>
            <Btn size="sm" variant="primary" onClick={refetch}>Refresh</Btn>
          </div>
        </div>

        {/* Summary Cards */}
        {Object.keys(summary).length > 0 && (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
            <SummaryCard label="Total" value={summary.total ?? 0}
              active={cardFilter === ""} onClick={() => { setCardFilter(""); setPage(1); }} />
            <SummaryCard label="Open" value={summary.open ?? 0}
              active={cardFilter === "open"} onClick={() => { setCardFilter("open"); setPage(1); }} />
            <SummaryCard label="SLA Breached" value={summary.sla_breached ?? 0}
              active={slaFilter === "breached"} onClick={() => { setSla(slaFilter === "breached" ? "" : "breached"); setPage(1); }} />
            <SummaryCard label="Pending Admin" value={summary.pending_admin ?? 0}
              active={cardFilter === "under_admin_review"} onClick={() => { setCardFilter("under_admin_review"); setPage(1); }} />
            <SummaryCard label="High Priority" value={summary.high_priority ?? 0}
              active={priority === "high"} onClick={() => { setPriority(priority === "high" ? "" : "high"); setPage(1); }} />
            <SummaryCard label="AI Settlement" value={summary.in_ai_settlement ?? 0}
              active={false} onClick={() => {}} />
            <SummaryCard label="New Today" value={summary.new_today ?? 0}
              active={false} onClick={() => {}} />
            <SummaryCard label="Settled" value={summary.settled ?? 0}
              active={cardFilter === "settled"} onClick={() => { setCardFilter("settled"); setPage(1); }} />
          </div>
        )}

        {/* Quick filters */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          <Chip label="All" active={!cardFilter && !slaFilter} onClick={() => { setCardFilter(""); setSla(""); setPage(1); }} />
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
              flex: "1 1 300px", padding: "8px 12px", borderRadius: 8,
              border: "1.5px solid var(--border)", fontSize: 13, outline: "none",
              background: "var(--surface)", color: "var(--text-primary)",
            }}
          />
          <select
            value={status}
            onChange={e => { setStatus(e.target.value); setPage(1); }}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
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
            style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
          <select
            value={slaFilter}
            onChange={e => { setSla(e.target.value); setPage(1); }}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid var(--border)", fontSize: 13, background: "var(--surface)", color: "var(--text-primary)" }}
          >
            <option value="">All SLA</option>
            <option value="on_time">On Time</option>
            <option value="at_risk">At Risk</option>
            <option value="breached">Breached</option>
            <option value="escalated">Escalated</option>
          </select>
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 8, padding: 16, marginBottom: 16, color: "var(--danger-text)" }}>
            Could not load complaints. {String(error)}
          </div>
        )}

        {/* Table */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
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
      </div>
    </AdminLayout>
  );
}
