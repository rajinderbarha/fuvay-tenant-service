"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../layout/AdminLayout";
import { Card, Badge, Btn } from "../shared/ui";
import { verticalDirectoryApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { Lock, Download, RefreshCw, Search } from "lucide-react";

// COMPLAINT-CONSOLIDATION: central Super Admin complaint work queue.
// Reused as-is by every Business Vertical -- the vertical is resolved from
// trusted route/navigation configuration (never a client-editable
// selector). Reuses the SAME canonical app.engines.complaints engine via
// the vertical-scoped VerticalComplaintWorkspaceService -- never a second
// complaint engine.

type Row = Record<string, unknown>;

const STATUS_LABELS: Record<string, string> = {
  open: "New", awaiting_provider_response: "Waiting on Provider",
  awaiting_customer_response: "Waiting on Customer", under_admin_review: "In Investigation",
  resolution_proposed: "Resolution Proposed", rework_approved: "Rework Approved",
  refund_requested: "Refund Requested", refund_approved: "Refund Approved",
  refund_recorded: "Refund Recorded", rejected: "Rejected", resolved: "Resolved",
  closed: "Closed", cancelled: "Cancelled",
};
function statusVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "resolved" || v === "closed") return "success";
  if (v === "rejected" || v === "cancelled") return "danger";
  if (v === "open") return "muted";
  return "warning";
}
function severityVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "critical") return "danger";
  if (v === "high") return "warning";
  if (v === "low") return "muted";
  return "muted";
}
function slaVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (v === "breached" || v === "escalated") return "danger";
  if (v === "at_risk") return "warning";
  return "success";
}

export function VerticalComplaintWorkspace({ vertical, verticalLabel }: { vertical: string; verticalLabel: string }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [severity, setSeverity] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<string | null>(null);

  const listApi = useApi(useCallback(
    () => verticalDirectoryApi.listComplaints(vertical, { search: search || undefined, status, severity, page_size: 25 }),
    [vertical, search, status, severity]));
  const summaryApi = useApi(useCallback(() => verticalDirectoryApi.complaintsSummary(vertical), [vertical]));

  const rows = (listApi.data?.items ?? []) as Row[];
  const s = summaryApi.data as Record<string, number> | null;

  async function doExport() {
    const data = await verticalDirectoryApi.exportComplaints(vertical);
    if (!data.items.length) { alert("Nothing to export."); return; }
    const headers = Object.keys(data.items[0]);
    const csv = [headers.join(","), ...data.items.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${vertical}-complaints.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  const KPIS: [string, string, (() => void)?][] = [
    ["Open", "open"], ["New", "new"], ["Unassigned", "unassigned"],
    ["In Investigation", "in_investigation"], ["Waiting on Customer", "waiting_on_customer"],
    ["Waiting on Provider", "waiting_on_provider"], ["Escalated", "escalated"],
    ["SLA Due Soon", "sla_due_soon"], ["SLA Breached", "sla_breached"], ["Resolved", "resolved"],
  ];

  return (
    <AdminLayout>
      <div style={{ padding: "0 4px" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Operations / {verticalLabel} / Complaints</p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 8 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{verticalLabel} Complaints</h1>
              <Badge variant="muted" size="sm"><Lock size={10} style={{ marginRight: 4, verticalAlign: -1 }}/>{verticalLabel} only</Badge>
            </div>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
              Investigate and resolve customer complaints across all {verticalLabel} providers.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="ghost" size="sm" onClick={doExport}><Download size={14} style={{ marginRight: 4 }}/>Export</Btn>
            <Btn variant="ghost" size="sm" onClick={() => { listApi.refetch(); summaryApi.refetch(); }}>
              <RefreshCw size={14} style={{ marginRight: 4 }}/>Refresh
            </Btn>
            <Btn variant="primary" size="sm" onClick={() => rows[0] && setSelected(rows[0].id as string)}>Review Next →</Btn>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: "var(--radius-lg)",
          background: "var(--info-bg, rgba(59,130,246,0.08))", border: "1px solid var(--info-border, rgba(59,130,246,0.3))", marginBottom: 16 }}>
          <p style={{ fontSize: 12, color: "var(--info-text, #3b82f6)", margin: 0 }}>
            Central queue — no provider-profile navigation required. Customer job payments are made directly to providers.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 10, marginBottom: 16 }}>
          {KPIS.map(([label, key]) => {
            const statusMap: Record<string, string | undefined> = {
              open: undefined, new: "open", in_investigation: "under_admin_review",
              waiting_on_customer: "awaiting_customer_response", waiting_on_provider: "awaiting_provider_response",
              escalated: "resolution_proposed", resolved: "resolved",
            };
            return (
              <div key={key} onClick={() => key in statusMap && setStatus(statusMap[key])}
                style={{ padding: "10px 12px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
                  background: "var(--surface)", cursor: key in statusMap ? "pointer" : "default" }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                  {summaryApi.error ? "—" : (s?.[key] ?? (summaryApi.loading ? "…" : 0))}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{label}</div>
              </div>
            );
          })}
        </div>
        {summaryApi.error && (
          <p style={{ fontSize: 11, color: "var(--warning-text)", margin: "-10px 0 16px" }}>
            Summary metrics are temporarily unavailable ({summaryApi.error}) — the queue below is unaffected.
          </p>
        )}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <div style={{ position: "relative", flex: "1 1 240px", maxWidth: 320 }}>
            <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Complaint, job, customer, provider or technician"
              style={{ width: "100%", padding: "7px 10px 7px 28px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
          </div>
          <select value={status ?? ""} onChange={e => setStatus(e.target.value || undefined)}
            style={{ padding: "7px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <select value={severity ?? ""} onChange={e => setSeverity(e.target.value || undefined)}
            style={{ padding: "7px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
            <option value="">All severities</option>
            {["low", "medium", "high", "critical"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        <div style={{ display: "flex", gap: 16 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Card style={{ padding: 0 }}>
              {listApi.error ? (
                <div style={{ padding: 24, textAlign: "center" }}>
                  <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{listApi.error}</p>
                  {listApi.requestId && <p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Request ID: {listApi.requestId}</p>}
                  <Btn variant="ghost" size="sm" onClick={listApi.refetch}>Retry</Btn>
                </div>
              ) : listApi.loading ? (
                <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading complaints…</div>
              ) : rows.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                  No {verticalLabel} complaints match this view.
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                        {["Complaint", "Severity", "Type", "Status", "SLA", "Created"].map(h => (
                          <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(row => (
                        <tr key={row.id as string} onClick={() => setSelected(row.id as string)}
                          style={{ borderBottom: "1px solid var(--border)", cursor: "pointer",
                            background: selected === row.id ? "var(--surface-sunken)" : "transparent" }}>
                          <td style={{ padding: "9px 14px", fontWeight: 600 }}>{row.complaint_number as string}</td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={severityVariant(row.severity as string)} size="sm">{row.severity as string}</Badge></td>
                          <td style={{ padding: "9px 14px" }}>{(row.complaint_type as string)?.replace(/_/g, " ") ?? "—"}</td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={statusVariant(row.status as string)} size="sm">{STATUS_LABELS[row.status as string] ?? row.status as string}</Badge></td>
                          <td style={{ padding: "9px 14px" }}><Badge variant={slaVariant(row.sla_status as string)} size="sm">{row.sla_status as string}</Badge></td>
                          <td style={{ padding: "9px 14px", color: "var(--text-tertiary)" }}>{row.created_at ? new Date(row.created_at as string).toLocaleDateString() : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
          {selected && (
            <div style={{ width: 420, flexShrink: 0 }}>
              <ComplaintInspector vertical={vertical} complaintId={selected} onClose={() => setSelected(null)}
                onChanged={() => { listApi.refetch(); summaryApi.refetch(); }}/>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

export function ComplaintInspector({ vertical, complaintId, onClose, onChanged, fullPage }: {
  vertical: string; complaintId: string; onClose?: () => void; onChanged?: () => void; fullPage?: boolean;
}) {
  const [tab, setTab] = useState<"case" | "job" | "evidence" | "conversation" | "resolution" | "audit">("case");
  const [reason, setReason] = useState("");
  const [messageText, setMessageText] = useState("");
  const [internalOnly, setInternalOnly] = useState(true);
  const [creditAmount, setCreditAmount] = useState("");

  const detail = useApi(useCallback(() => verticalDirectoryApi.getComplaint(vertical, complaintId), [vertical, complaintId]));
  const jobContext = useApi(useCallback(() => verticalDirectoryApi.getComplaintJobContext(vertical, complaintId), [vertical, complaintId]), [tab], { enabled: tab === "job" });
  const evidence = useApi(useCallback(() => verticalDirectoryApi.getComplaintEvidence(vertical, complaintId), [vertical, complaintId]), [tab], { enabled: tab === "evidence" });
  const conversation = useApi(useCallback(() => verticalDirectoryApi.getComplaintConversation(vertical, complaintId), [vertical, complaintId]), [tab], { enabled: tab === "conversation" });
  const resolution = useApi(useCallback(() => verticalDirectoryApi.getComplaintResolution(vertical, complaintId), [vertical, complaintId]), [tab], { enabled: tab === "resolution" });
  const timeline = useApi(useCallback(() => verticalDirectoryApi.getComplaintTimeline(vertical, complaintId), [vertical, complaintId]), [tab], { enabled: tab === "audit" });

  const escalate = useAction((r: string) => verticalDirectoryApi.escalateComplaint(vertical, complaintId, r));
  const resolveAction = useAction((r: string) => verticalDirectoryApi.resolveComplaint(vertical, complaintId, r));
  const closeAction = useAction((r: string) => verticalDirectoryApi.closeComplaint(vertical, complaintId, r));
  const reopenAction = useAction((r: string) => verticalDirectoryApi.reopenComplaint(vertical, complaintId, r));
  const requestResponse = useAction(() => verticalDirectoryApi.requestComplaintResponse(vertical, complaintId));
  const sendMessage = useAction(() => verticalDirectoryApi.addComplaintMessage(vertical, complaintId, messageText, internalOnly));
  const issueCredit = useAction(() => verticalDirectoryApi.issueCustomerCredit(vertical, complaintId, creditAmount, reason));

  async function run(action: { execute: (r: string) => Promise<unknown> }) {
    const r = await action.execute(reason);
    if (r) { setReason(""); detail.refetch(); onChanged?.(); }
  }

  const d = detail.data as Record<string, unknown> | null;

  return (
    <Card style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div>
          <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{d?.complaint_number as string ?? "…"}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{d?.title as string}</p>
        </div>
        {onClose && <Btn variant="ghost" size="sm" onClick={onClose}>Close</Btn>}
      </div>
      {d && (
        <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
          <Badge variant={statusVariant(d.status as string)} size="sm">{STATUS_LABELS[d.status as string] ?? d.status as string}</Badge>
          <Badge variant={severityVariant(d.severity as string)} size="sm">{d.severity as string}</Badge>
          <Badge variant={slaVariant(d.sla_status as string)} size="sm">SLA: {d.sla_status as string}</Badge>
        </div>
      )}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 10, overflowX: "auto" }}>
        {(["case", "job", "evidence", "conversation", "resolution", "audit"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: "6px 8px", fontSize: 11, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer", textTransform: "capitalize" }}>
            {t === "job" ? "Job Context" : t}
          </button>
        ))}
      </div>

      {tab === "case" && d && (
        <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          <Row label="Complaint type" value={(d.complaint_type as string)?.replace(/_/g, " ")}/>
          <Row label="Customer statement" value={d.description as string}/>
          <Row label="Requested resolution" value={(d.requested_resolution as string) ?? "—"}/>
          <Row label="Submitted" value={d.created_at ? new Date(d.created_at as string).toLocaleString() : "—"}/>
          <Row label="Assigned admin" value={(d.assigned_admin_user_id as string) ?? "Unassigned"}/>
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            <textarea placeholder="Reason (required for escalate/resolve/close/reopen)" value={reason} onChange={e => setReason(e.target.value)} rows={2}
              style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }}/>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Btn variant="secondary" size="sm" onClick={() => requestResponse.execute()} disabled={requestResponse.loading}>Request Provider Response</Btn>
              <Btn variant="warning" size="sm" onClick={() => run(escalate)} disabled={escalate.loading}>Escalate</Btn>
              <Btn variant="success" size="sm" onClick={() => run(resolveAction)} disabled={resolveAction.loading}>Resolve</Btn>
              <Btn variant="secondary" size="sm" onClick={() => run(closeAction)} disabled={closeAction.loading}>Close</Btn>
              <Btn variant="ghost" size="sm" onClick={() => run(reopenAction)} disabled={reopenAction.loading}>Reopen</Btn>
            </div>
            {(escalate.error || resolveAction.error || closeAction.error || reopenAction.error) && (
              <p style={{ fontSize: 11, color: "var(--danger-text)" }}>
                {escalate.error || resolveAction.error || closeAction.error || reopenAction.error}
              </p>
            )}
          </div>
          <div style={{ marginTop: 10, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", fontSize: 11, color: "var(--text-secondary)" }}>
            <p style={{ margin: "0 0 6px", fontWeight: 700 }}>Issue Customer Service Credit</p>
            <p style={{ margin: "0 0 6px" }}>Not a cash refund — the platform did not collect this job payment.</p>
            <input placeholder="Amount" value={creditAmount} onChange={e => setCreditAmount(e.target.value)}
              style={{ width: "100%", padding: "6px 8px", marginBottom: 6, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }}/>
            <Btn variant="primary" size="sm" onClick={() => issueCredit.execute()} disabled={issueCredit.loading || !creditAmount || !reason.trim()}>
              Issue Customer Service Credit
            </Btn>
            {issueCredit.error && <p style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 4 }}>{issueCredit.error}</p>}
          </div>
        </div>
      )}

      {tab === "job" && (
        <div style={{ fontSize: 12 }}>
          {jobContext.data?.job_linked ? (
            <>
              <Row label="Job ID" value={jobContext.data.job_id as string}/>
              <Row label="Job Number" value={jobContext.data.job_number as string}/>
              <Row label="Status" value={jobContext.data.status as string}/>
              <a href={`/admin/home-services/service-jobs/${jobContext.data.job_id}?tab=review`}
                style={{ fontSize: 11, color: "var(--brand)" }}>Open Job 360° →</a>
            </>
          ) : (
            <p style={{ color: "var(--text-tertiary)" }}>No canonical job linkage found for this complaint.</p>
          )}
        </div>
      )}

      {tab === "evidence" && (
        <div style={{ fontSize: 12 }}>
          {(evidence.data?.items.length ?? 0) === 0 ? (
            <p style={{ color: "var(--text-tertiary)" }}>No evidence submitted yet.</p>
          ) : evidence.data!.items.map((m, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              {(m as Record<string, unknown>).media_type as string} — {(m as Record<string, unknown>).uploaded_by_type as string}
            </div>
          ))}
        </div>
      )}

      {tab === "conversation" && (
        <div style={{ fontSize: 12 }}>
          {(conversation.data?.items ?? []).map((m, i) => {
            const msg = m as Record<string, unknown>;
            return (
              <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <p style={{ margin: 0, fontWeight: 600 }}>
                  {msg.sender_type as string} {msg.visibility === "admin_only" && <Badge variant="muted" size="sm">Internal only</Badge>}
                </p>
                <p style={{ margin: "2px 0" }}>{msg.message_text as string}</p>
                <p style={{ margin: 0, color: "var(--text-tertiary)" }}>{msg.created_at ? new Date(msg.created_at as string).toLocaleString() : "—"}</p>
              </div>
            );
          })}
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
            <textarea placeholder="Message" value={messageText} onChange={e => setMessageText(e.target.value)} rows={2}
              style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }}/>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input type="checkbox" checked={internalOnly} onChange={e => setInternalOnly(e.target.checked)}/> Internal note only
            </label>
            <Btn variant="primary" size="sm" onClick={async () => { const r = await sendMessage.execute(); if (r) { setMessageText(""); conversation.refetch(); } }}
              disabled={sendMessage.loading || !messageText.trim()}>Send</Btn>
          </div>
        </div>
      )}

      {tab === "resolution" && (
        <div style={{ fontSize: 12 }}>
          {(resolution.data?.items.length ?? 0) === 0 ? (
            <p style={{ color: "var(--text-tertiary)" }}>No resolution proposed yet.</p>
          ) : resolution.data!.items.map((res, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>{(res as Record<string, unknown>).resolution_type as string}</p>
              <p style={{ margin: 0 }}>{(res as Record<string, unknown>).description as string}</p>
              <p style={{ margin: 0, color: "var(--text-tertiary)" }}>{(res as Record<string, unknown>).status as string}</p>
            </div>
          ))}
        </div>
      )}

      {tab === "audit" && (
        <div style={{ fontSize: 12 }}>
          {(timeline.data?.items.length ?? 0) === 0 ? (
            <p style={{ color: "var(--text-tertiary)" }}>No events recorded yet.</p>
          ) : timeline.data!.items.map((e, i) => (
            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>{(e as Record<string, unknown>).event_type as string}</p>
              <p style={{ margin: 0, color: "var(--text-tertiary)" }}>
                {(e as Record<string, unknown>).created_at ? new Date((e as Record<string, unknown>).created_at as string).toLocaleString() : "—"}
              </p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 500 }}>{value || "—"}</div>
    </div>
  );
}
