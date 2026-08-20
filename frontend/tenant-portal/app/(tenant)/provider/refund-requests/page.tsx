"use client";
import { useCallback, useState } from "react";
import EnterpriseDataGrid, { GridColumn, GridData, RowAction } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch, financeApi } from "../../../../lib/api";

type RemedyMode = "refunds" | "warranty";
type ActionKind = "refund_approve" | "refund_reject" | "refund_record" | "warranty_respond" | "warranty_resolve" | "warranty_escalate";
interface PendingAction { kind: ActionKind; row: Record<string, unknown> }

const REFUND_COLUMNS: GridColumn[] = [
  { key: "refund_number", label: "Refund", width: 130 },
  { key: "status", label: "Status", width: 160, render: v => String(v ?? "").replaceAll("_", " ") },
  { key: "refund_type", label: "Type", width: 140 },
  { key: "requested_amount", label: "Requested (₹)", width: 130, render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "approved_amount", label: "Approved (₹)", width: 130, render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "provider_response_due_at", label: "Response due", width: 180, render: v => v ? new Date(String(v)).toLocaleString() : "—" },
  { key: "created_at", label: "Created", width: 150, render: v => v ? new Date(String(v)).toLocaleDateString() : "—" },
];
const WARRANTY_COLUMNS: GridColumn[] = [
  { key: "claim_id", label: "Claim", width: 110, render: v => String(v ?? "").slice(0, 8) },
  { key: "job_id", label: "Job", width: 110, render: v => String(v ?? "").slice(0, 8) },
  { key: "status", label: "Status", width: 170, render: v => String(v ?? "").replaceAll("_", " ") },
  { key: "claim_type", label: "Issue type", width: 150, render: v => String(v ?? "").replaceAll("_", " ") },
  { key: "amount_requested", label: "Exposure (₹)", width: 130, render: v => `₹${Number(v ?? 0).toLocaleString("en-IN")}` },
  { key: "warranty_expires_at", label: "Warranty ends", width: 150, render: v => v ? new Date(String(v)).toLocaleDateString() : "—" },
  { key: "provider_response_due_at", label: "Response due", width: 180, render: v => v ? new Date(String(v)).toLocaleString() : "—" },
];
const FILTERS: FilterDef[] = [{ key: "status", label: "Status", type: "select", options: [
  { value: "requested", label: "Requested" }, { value: "provider_review", label: "Provider review" },
  { value: "provider_action_required", label: "Provider action required" }, { value: "provider_in_progress", label: "Provider in progress" },
  { value: "provider_resolved", label: "Provider resolved" }, { value: "approved", label: "Approved" },
  { value: "recorded", label: "Recorded" }, { value: "verified", label: "Verified" },
  { value: "admin_review", label: "Admin escalation" }, { value: "credit_issued", label: "Service points issued" },
  { value: "rejected", label: "Rejected" },
] }];

function wrap(items: Record<string, unknown>[], params: Record<string, unknown>): GridData {
  const page = Number(params.page ?? 1); const pageSize = Number(params.page_size ?? 25);
  return { items, pagination: { page, page_size: pageSize, total_items: items.length, total_pages: Math.max(1, Math.ceil(items.length / pageSize)), has_next: false, has_previous: page > 1 }, sort: { sort_by: String(params.sort_by ?? "created_at"), sort_direction: String(params.sort_direction ?? "desc") }, filters_applied: params, available_columns: [] };
}

export default function ProviderCustomerRemediesPage() {
  const [mode, setMode] = useState<RemedyMode>("refunds");
  const [revision, setRevision] = useState(0);
  const [action, setAction] = useState<PendingAction | null>(null);
  const [notes, setNotes] = useState(""); const [amount, setAmount] = useState(""); const [proof, setProof] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);

  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const status = params.status ? String(params.status) : undefined;
    if (mode === "warranty") {
      const result = await financeApi.warrantyClaims(status, Number(params.page_size ?? 25));
      return wrap((result as unknown as { claims?: Record<string, unknown>[] }).claims ?? [], params);
    }
    const qs = new URLSearchParams(); if (status) qs.set("status", status);
    qs.set("page", String(params.page ?? 1)); qs.set("page_size", String(params.page_size ?? 25));
    if (params.q) qs.set("q", String(params.q));
    const result = await apiFetch<GridData>(`/v1/provider/refund-requests?${qs}`);
    return { ...result, sort: result.sort ?? { sort_by: "created_at", sort_direction: "desc" }, filters_applied: params, available_columns: result.available_columns ?? [] };
  }, [mode, revision]);

  const rowActions = useCallback((row: Record<string, unknown>): RowAction[] => {
    const status = String(row.status ?? "");
    if (mode === "warranty") {
      if (!["provider_action_required", "provider_in_progress"].includes(status)) return [];
      return [
        { label: "Respond / update", onClick: () => setAction({ kind: "warranty_respond", row }) },
        { label: "Mark resolved", onClick: () => setAction({ kind: "warranty_resolve", row }) },
        { label: "Escalate to admin", danger: true, onClick: () => setAction({ kind: "warranty_escalate", row }) },
      ];
    }
    if (["requested", "provider_review"].includes(status)) return [
      { label: "Approve refund", onClick: () => { setAmount(String(row.requested_amount ?? "")); setAction({ kind: "refund_approve", row }); } },
      { label: "Reject with reason", danger: true, onClick: () => setAction({ kind: "refund_reject", row }) },
    ];
    if (status === "approved") return [{ label: "Record repayment", onClick: () => { setAmount(String(row.approved_amount ?? row.requested_amount ?? "")); setAction({ kind: "refund_record", row }); } }];
    return [];
  }, [mode]);

  async function submitAction() {
    if (!action) return; setBusy(true); setError(null);
    try {
      const id = String(action.row.id ?? action.row.claim_id);
      if (action.kind === "refund_approve") await apiFetch(`/v1/provider/refund-requests/${id}/decision`, { method: "POST", body: JSON.stringify({ approve: true, approved_amount: Number(amount) }) });
      if (action.kind === "refund_reject") await apiFetch(`/v1/provider/refund-requests/${id}/decision`, { method: "POST", body: JSON.stringify({ approve: false, reason: notes.trim() }) });
      if (action.kind === "refund_record") await apiFetch(`/v1/provider/refund-requests/${id}/record`, { method: "POST", body: JSON.stringify({ recorded_amount: Number(amount), proof_media_url: proof.trim() || null }) });
      if (action.kind === "warranty_respond") await financeApi.respondWarrantyClaim(id, notes.trim(), false);
      if (action.kind === "warranty_resolve") await financeApi.respondWarrantyClaim(id, notes.trim(), true);
      if (action.kind === "warranty_escalate") await financeApi.escalateWarrantyClaim(id, notes.trim());
      setAction(null); setNotes(""); setAmount(""); setProof(""); setRevision(v => v + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to update this request."); } finally { setBusy(false); }
  }

  const needsAmount = action?.kind === "refund_approve" || action?.kind === "refund_record";
  const needsNotes = !!action && action.kind !== "refund_approve" && action.kind !== "refund_record";
  const valid = !!action && (!needsAmount || Number(amount) > 0) && (!needsNotes || notes.trim().length >= 10);
  const fieldStyle = { padding: 11, borderRadius: 8, border: "1px solid var(--border-default)", background: "var(--surface-default)", color: "var(--text-primary)" };

  return <>
    <EnterpriseDataGrid key={`${mode}-${revision}`} resourceKey={`provider_${mode}`} fetchFn={fetchFn}
      columns={mode === "refunds" ? REFUND_COLUMNS : WARRANTY_COLUMNS} filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }} enableColumnPrefs rowActions={rowActions}
      title="Customer remedies" emptyMessage={mode === "refunds" ? "No customer refund requests." : "No warranty claims."}
      headerSlot={<div style={{ display: "flex", gap: 8 }}><button className="btn-secondary" onClick={() => setMode("refunds")} aria-pressed={mode === "refunds"}>Refunds</button><button className="btn-secondary" onClick={() => setMode("warranty")} aria-pressed={mode === "warranty"}>Warranty claims</button></div>} />
    {action && <div role="dialog" aria-modal="true" style={{ position: "fixed", inset: 0, zIndex: 1000, display: "grid", placeItems: "center", background: "rgba(0,0,0,.5)", padding: 20 }}>
      <div style={{ width: "min(520px,100%)", background: "var(--surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 22, boxShadow: "var(--shadow-lg)" }}>
        <h2 style={{ margin: "0 0 6px", fontSize: 18 }}>Update customer remedy</h2>
        <p style={{ margin: "0 0 18px", color: "var(--text-tertiary)", fontSize: 13 }}>Providers own the first response. Escalate only when you cannot provide a satisfactory resolution.</p>
        {needsAmount && <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Amount (₹)<input value={amount} onChange={e => setAmount(e.target.value)} type="number" min="0.01" step="0.01" style={fieldStyle} /></label>}
        {needsNotes && <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Resolution or reason<textarea value={notes} onChange={e => setNotes(e.target.value)} rows={5} maxLength={2000} style={{ ...fieldStyle, resize: "vertical" }} /></label>}
        {action.kind === "refund_record" && <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Proof URL (optional)<input value={proof} onChange={e => setProof(e.target.value)} style={fieldStyle} /></label>}
        {error && <p role="alert" style={{ color: "var(--danger-text)", fontSize: 12 }}>{error}</p>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><button className="btn-secondary" onClick={() => { setAction(null); setError(null); }} disabled={busy}>Cancel</button><button className="btn-primary" onClick={submitAction} disabled={!valid || busy}>{busy ? "Saving…" : "Confirm"}</button></div>
      </div>
    </div>}
  </>;
}
