"use client";
/**
 * Customer Remedies — refunds, rework and warranty claims in one workspace.
 *
 * This is the destination of the "Refunds & Warranty" sidebar item and now
 * covers all three remedy types. Rework previously had its own page at
 * /provider/rework-requests that **nothing linked to** — it was reachable only
 * by typing the URL — even though rework is the third leg of the same
 * complaint-remedy flow (a customer accepting a rework resolution spawns a
 * ServiceReworkRequest). That page is now a redirect here.
 *
 * Redesign notes:
 *  - The grid emits its search box as `search`; this page read `params.q`, so
 *    searching had never filtered anything. Fixed on both sides.
 *  - Warranty rows were wrapped with a fabricated `total_items: items.length`
 *    and `has_next: false`, discarding the API's real cursor pagination — so
 *    page 2 of warranty claims was unreachable and the total was wrong.
 *  - Refunds showed an amount and a type but no link to the complaint or job
 *    they came from, and never showed the customer's stated reason.
 */
import React, { useCallback, useMemo, useRef, useState } from "react";
import EnterpriseDataGrid, { GridColumn, GridData, RowAction } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch, financeApi, providerComplaintApi } from "../../../../lib/api";

type RemedyMode = "refunds" | "rework" | "warranty";
type ActionKind =
  | "refund_review" | "refund_approve" | "refund_reject" | "refund_record"
  | "rework_schedule" | "rework_start" | "rework_complete"
  | "warranty_respond" | "warranty_resolve";
interface PendingAction { kind: ActionKind; row: Record<string, unknown> }

const money = (v: unknown) => (v != null && v !== "" ? `₹${Number(v).toLocaleString("en-IN")}` : "—");
const dt = (v: unknown) => (v ? new Date(String(v)).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");
const dtl = (v: unknown) => (v ? new Date(String(v)).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
const words = (v: unknown) => String(v ?? "").replaceAll("_", " ");

/** Refund columns now carry the case context the provider needs to judge the
 *  request: which complaint and job it came from, and the stated reason. */
const REFUND_COLUMNS: GridColumn[] = [
  { key: "refund_number", label: "Refund", width: 130 },
  { key: "status", label: "Status", width: 150, render: words },
  { key: "complaint_number", label: "Case", width: 130, render: v => String(v ?? "—") },
  { key: "job_number", label: "Job", width: 130, render: v => String(v ?? "—") },
  { key: "service_name", label: "Service", width: 160, render: v => String(v ?? "—") },
  { key: "refund_type", label: "Type", width: 130, render: words },
  { key: "requested_amount", label: "Requested", width: 115, render: money },
  { key: "approved_amount", label: "Approved", width: 115, render: money },
  { key: "recorded_amount", label: "Paid", width: 110, render: money },
  { key: "reason", label: "Customer reason", width: 260, render: v => String(v ?? "—") },
  { key: "provider_response_due_at", label: "Response due", width: 160, render: dtl },
  { key: "created_at", label: "Created", width: 130, render: dt },
];

const REWORK_COLUMNS: GridColumn[] = [
  { key: "id", label: "Rework", width: 110, render: v => String(v ?? "").slice(0, 8) },
  { key: "status", label: "Status", width: 140, render: words },
  { key: "rework_reason", label: "Reason", width: 320, render: v => String(v ?? "—") },
  { key: "scheduled_date", label: "Scheduled", width: 130, render: v => (v && v !== "None" ? dt(v) : "—") },
  { key: "created_at", label: "Created", width: 150, render: dt },
];

const WARRANTY_COLUMNS: GridColumn[] = [
  { key: "claim_id", label: "Claim", width: 110, render: v => String(v ?? "").slice(0, 8) },
  { key: "job_id", label: "Job", width: 120, render: v => String(v ?? "—") },
  { key: "status", label: "Status", width: 170, render: words },
  { key: "claim_type", label: "Issue type", width: 150, render: words },
  { key: "description", label: "Description", width: 280, render: v => String(v ?? "—") },
  { key: "amount_requested", label: "Exposure", width: 120, render: money },
  { key: "warranty_expires_at", label: "Warranty ends", width: 140, render: dt },
  { key: "provider_response_due_at", label: "Response due", width: 160, render: dtl },
];

/** Every option here maps to a query parameter verified against the live API. */
const REFUND_FILTERS: FilterDef[] = [
  { key: "status", label: "Status", type: "select", options: [
    { value: "requested", label: "Requested" },
    { value: "provider_review", label: "Under your review" },
    { value: "approved", label: "Approved" },
    { value: "recorded", label: "Paid / recorded" },
    { value: "verified", label: "Verified" },
    { value: "rejected", label: "Rejected" },
    { value: "cancelled", label: "Cancelled" },
  ] },
  { key: "refund_type", label: "Refund type", type: "select", options: [
    { value: "full_refund", label: "Full refund" },
    { value: "partial_refund", label: "Partial refund" },
    { value: "goodwill", label: "Goodwill" },
  ] },
  { key: "date_from", label: "From", type: "date" },
  { key: "date_to", label: "To", type: "date" },
];
const REWORK_FILTERS: FilterDef[] = [
  { key: "status", label: "Status", type: "select", options: [
    { value: "requested", label: "Requested" },
    { value: "approved", label: "Approved" },
    { value: "assigned", label: "Assigned" },
    { value: "scheduled", label: "Scheduled" },
    { value: "in_progress", label: "In progress" },
    { value: "completed", label: "Completed" },
    { value: "rejected", label: "Rejected" },
    { value: "cancelled", label: "Cancelled" },
  ] },
];
const WARRANTY_FILTERS: FilterDef[] = [
  { key: "status", label: "Status", type: "select", options: [
    { value: "provider_action_required", label: "Provider action required" },
    { value: "provider_in_progress", label: "Provider in progress" },
    { value: "provider_resolved", label: "Provider resolved" },
    { value: "credit_issued", label: "Service points issued" },
    { value: "rejected", label: "Rejected" },
  ] },
];

interface RefundSummary {
  total: number; needs_action: number; approved: number; settled: number;
  overdue: number; rejected: number;
  requested_amount: string; approved_amount: string;
  recorded_amount: string; provider_exposure: string;
}

export default function ProviderCustomerRemediesPage() {
  const [mode, setMode] = useState<RemedyMode>("refunds");
  const [revision, setRevision] = useState(0);
  const [action, setAction] = useState<PendingAction | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [notes, setNotes] = useState("");
  const [amount, setAmount] = useState("");
  const [proof, setProof] = useState("");
  const [schedDate, setSchedDate] = useState("");
  const [schedWindow, setSchedWindow] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<RefundSummary | null>(null);

  /**
   * Warranty claims are cursor-paginated server-side. The grid is page-based,
   * so remember the cursor that opens each page; page N+1's cursor is whatever
   * page N returned. Without this the previous implementation simply dropped
   * `next_cursor` and reported `has_next: false`, pinning warranty to page 1.
   */
  const cursorsRef = useRef<Record<number, string | null>>({ 1: null });

  const fetchFn = useCallback(async (params: Record<string, unknown>): Promise<GridData> => {
    const page = Number(params.page ?? 1);
    const pageSize = Number(params.page_size ?? 25);
    const status = params.status ? String(params.status) : undefined;
    // The grid supplies its search box value as `search`.
    const search = params.search ? String(params.search) : undefined;
    const sort = { sort_by: String(params.sort_by ?? "created_at"), sort_direction: String(params.sort_direction ?? "desc") };

    if (mode === "warranty") {
      const cursor = cursorsRef.current[page] ?? null;
      const qs = new URLSearchParams({ limit: String(pageSize) });
      if (status) qs.set("status", status);
      if (cursor) qs.set("cursor", cursor);
      const tid = typeof window !== "undefined" ? localStorage.getItem("serviceos_tenant_id") ?? "" : "";
      const result = await apiFetch<{ claims: Record<string, unknown>[]; has_next: boolean; next_cursor: string | null }>(
        `/v1/commerce/tenants/${tid}/warranty/claims?${qs}`,
      );
      cursorsRef.current[page + 1] = result.next_cursor ?? null;
      const seenSoFar = (page - 1) * pageSize + result.claims.length;
      return {
        items: result.claims,
        pagination: {
          page, page_size: pageSize,
          // Cursor pagination has no exact total. Report what is actually
          // known rather than inventing one: everything seen so far, plus at
          // least one more when the API says another page exists.
          total_items: result.has_next ? seenSoFar + 1 : seenSoFar,
          total_pages: result.has_next ? page + 1 : page,
          has_next: result.has_next, has_previous: page > 1,
        },
        sort, filters_applied: params, available_columns: [],
      };
    }

    if (mode === "rework") {
      const reworks = await providerComplaintApi.listReworks(status);
      const rows = (Array.isArray(reworks) ? reworks : []) as unknown as Record<string, unknown>[];
      const filtered = search
        ? rows.filter(r => JSON.stringify(r).toLowerCase().includes(search.toLowerCase()))
        : rows;
      // This endpoint returns a plain list with no server-side paging, so the
      // slice happens here — and the total is the real filtered length, not a
      // guess.
      const start = (page - 1) * pageSize;
      return {
        items: filtered.slice(start, start + pageSize),
        pagination: {
          page, page_size: pageSize, total_items: filtered.length,
          total_pages: Math.max(1, Math.ceil(filtered.length / pageSize)),
          has_next: start + pageSize < filtered.length, has_previous: page > 1,
        },
        sort, filters_applied: params, available_columns: [],
      };
    }

    const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) qs.set("status", status);
    if (search) qs.set("search", search);
    if (params.refund_type) qs.set("refund_type", String(params.refund_type));
    if (params.date_from) qs.set("date_from", String(params.date_from));
    if (params.date_to) qs.set("date_to", String(params.date_to));
    const result = await apiFetch<GridData & { summary?: RefundSummary }>(`/v1/provider/refund-requests?${qs}`);
    setSummary(result.summary ?? null);
    return { ...result, sort: result.sort ?? sort, filters_applied: params, available_columns: result.available_columns ?? [] };
  }, [mode, revision]);

  const rowActions = useCallback((row: Record<string, unknown>): RowAction[] => {
    const status = String(row.status ?? "");
    const open: RowAction = { label: "View details", onClick: () => setDetail(row) };

    if (mode === "warranty") {
      if (!["provider_action_required", "provider_in_progress"].includes(status)) return [open];
      return [open,
        { label: "Respond / update", onClick: () => setAction({ kind: "warranty_respond", row }) },
        { label: "Mark resolved", onClick: () => setAction({ kind: "warranty_resolve", row }) },
      ];
    }

    if (mode === "rework") {
      // Mirrors the server-side rework transition table, so no action is
      // offered that the state machine would reject.
      const acts: RowAction[] = [open];
      if (["approved", "assigned", "scheduled"].includes(status)) {
        acts.push({ label: "Schedule visit", onClick: () => setAction({ kind: "rework_schedule", row }) });
      }
      if (["approved", "assigned", "scheduled"].includes(status)) {
        acts.push({ label: "Start rework", onClick: () => setAction({ kind: "rework_start", row }) });
      }
      if (status === "in_progress") {
        acts.push({ label: "Mark complete", onClick: () => setAction({ kind: "rework_complete", row }) });
      }
      return acts;
    }

    if (["requested", "provider_review"].includes(status)) {
      const acts: RowAction[] = [open];
      // `/review` exists and marks the case as actively under provider review
      // (it stops the "awaiting first response" clock). The page never called
      // it, so that state was unreachable from the UI.
      if (status === "requested") {
        acts.push({ label: "Mark under review", onClick: () => setAction({ kind: "refund_review", row }) });
      }
      acts.push(
        { label: "Approve refund", onClick: () => { setAmount(String(row.requested_amount ?? "")); setAction({ kind: "refund_approve", row }); } },
        { label: "Reject with reason", danger: true, onClick: () => setAction({ kind: "refund_reject", row }) },
      );
      return acts;
    }
    if (status === "approved") {
      return [open, { label: "Record repayment", onClick: () => { setAmount(String(row.approved_amount ?? row.requested_amount ?? "")); setAction({ kind: "refund_record", row }); } }];
    }
    return [open];
  }, [mode]);

  async function submitAction() {
    if (!action) return;
    setBusy(true); setError(null);
    try {
      const id = String(action.row.id ?? action.row.claim_id);
      switch (action.kind) {
        case "refund_review":
          await apiFetch(`/v1/provider/refund-requests/${id}/review`, { method: "POST", body: JSON.stringify({ notes: notes.trim() || null }) }); break;
        case "refund_approve":
          await apiFetch(`/v1/provider/refund-requests/${id}/decision`, { method: "POST", body: JSON.stringify({ approve: true, approved_amount: Number(amount) }) }); break;
        case "refund_reject":
          await apiFetch(`/v1/provider/refund-requests/${id}/decision`, { method: "POST", body: JSON.stringify({ approve: false, reason: notes.trim() }) }); break;
        case "refund_record":
          await apiFetch(`/v1/provider/refund-requests/${id}/record`, { method: "POST", body: JSON.stringify({ recorded_amount: Number(amount), proof_media_url: proof.trim() || null }) }); break;
        case "rework_schedule":
          await apiFetch(`/v1/provider/rework-requests/${id}/schedule`, { method: "POST", body: JSON.stringify({ scheduled_date: schedDate || null, scheduled_time_window: schedWindow.trim() || null }) }); break;
        case "rework_start":
          await providerComplaintApi.startRework(id); break;
        case "rework_complete":
          await providerComplaintApi.completeRework(id, notes.trim() || undefined); break;
        case "warranty_respond":
          await financeApi.respondWarrantyClaim(id, notes.trim(), false); break;
        case "warranty_resolve":
          await financeApi.respondWarrantyClaim(id, notes.trim(), true); break;
      }
      closeAction();
      setRevision(v => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to update this request.");
    } finally { setBusy(false); }
  }

  function closeAction() {
    setAction(null); setNotes(""); setAmount(""); setProof(""); setSchedDate(""); setSchedWindow(""); setError(null);
  }

  function switchMode(next: RemedyMode) {
    cursorsRef.current = { 1: null };
    setMode(next);
    setDetail(null);
  }

  const needsAmount = action?.kind === "refund_approve" || action?.kind === "refund_record";
  const needsSchedule = action?.kind === "rework_schedule";
  const noInput = action?.kind === "rework_start";
  const optionalNotes = action?.kind === "refund_review" || action?.kind === "rework_complete";
  const needsNotes = !!action && !needsAmount && !needsSchedule && !noInput && !optionalNotes;
  const valid = !!action
    && (!needsAmount || Number(amount) > 0)
    && (!needsNotes || notes.trim().length >= 10)
    && (!needsSchedule || Boolean(schedDate));

  const columns = mode === "refunds" ? REFUND_COLUMNS : mode === "rework" ? REWORK_COLUMNS : WARRANTY_COLUMNS;
  const filters = mode === "refunds" ? REFUND_FILTERS : mode === "rework" ? REWORK_FILTERS : WARRANTY_FILTERS;

  return (
    <>
      {mode === "refunds" && summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 16 }}>
          <Kpi label="Needs your action" value={summary.needs_action} sub={money(summary.requested_amount)} tone={summary.needs_action > 0 ? "warning" : "default"}/>
          <Kpi label="Approved" value={summary.approved} sub={money(summary.approved_amount)} tone="default"/>
          <Kpi label="Paid out" value={summary.settled} sub={money(summary.recorded_amount)} tone="success"/>
          <Kpi label="Overdue" value={summary.overdue} tone={summary.overdue > 0 ? "danger" : "default"}/>
          <Kpi label="Rejected" value={summary.rejected} tone="default"/>
          <Kpi label="Provider-funded remedies" value={money(summary.provider_exposure)} sub="usage-credit ledger" tone={Number(summary.provider_exposure) > 0 ? "danger" : "default"}/>
        </div>
      )}

      <EnterpriseDataGrid
        key={`${mode}-${revision}`}
        resourceKey={`provider_${mode}`}
        fetchFn={fetchFn}
        columns={columns}
        filters={filters}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableColumnPrefs
        rowActions={rowActions}
        title="Customer remedies"
        emptyMessage={
          mode === "refunds" ? "No customer refund requests."
            : mode === "rework" ? "No rework requests. These appear when a customer accepts a rework resolution on a complaint."
              : "No warranty claims."
        }
        headerSlot={
          <div style={{ display: "flex", gap: 8 }}>
            {(["refunds", "rework", "warranty"] as RemedyMode[]).map(m => (
              <button key={m} onClick={() => switchMode(m)} aria-pressed={mode === m} style={btnSecondary(mode === m)}>
                {m === "refunds" ? "Refunds" : m === "rework" ? "Rework visits" : "Warranty claims"}
              </button>
            ))}
          </div>
        }
      />

      {detail && <DetailDrawer row={detail} mode={mode} onClose={() => setDetail(null)}/>}

      {action && (
        <div role="dialog" aria-modal="true" style={{ position: "fixed", inset: 0, zIndex: 1000, display: "grid", placeItems: "center", background: "rgba(0,0,0,.5)", padding: 20 }}>
          <div style={{ width: "min(520px,100%)", background: "var(--surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 16, padding: 22, boxShadow: "var(--shadow-lg)" }}>
            <h2 style={{ margin: "0 0 6px", fontSize: 18 }}>{ACTION_TITLES[action.kind]}</h2>
            <p style={{ margin: "0 0 18px", color: "var(--text-tertiary)", fontSize: 13 }}>
              The provider reviews the evidence and works directly with the customer on rework, refund, credit, or another mutually agreed resolution.
            </p>
            {needsAmount && (
              <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Amount (₹)
                <input value={amount} onChange={e => setAmount(e.target.value)} type="number" min="0.01" step="0.01" style={fieldStyle}/>
              </label>
            )}
            {needsSchedule && (
              <>
                <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Visit date
                  <input value={schedDate} onChange={e => setSchedDate(e.target.value)} type="date" style={fieldStyle}/>
                </label>
                <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Time window (optional)
                  <input value={schedWindow} onChange={e => setSchedWindow(e.target.value)} placeholder="10:00-13:00" style={fieldStyle}/>
                </label>
              </>
            )}
            {(needsNotes || optionalNotes) && (
              <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>
                {optionalNotes ? "Notes (optional)" : "Resolution or reason"}
                <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={5} maxLength={2000} style={{ ...fieldStyle, resize: "vertical" }}/>
              </label>
            )}
            {noInput && <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>This marks the rework visit as in progress.</p>}
            {action.kind === "refund_record" && (
              <label style={{ display: "grid", gap: 6, marginBottom: 12, fontSize: 12 }}>Proof URL (optional)
                <input value={proof} onChange={e => setProof(e.target.value)} style={fieldStyle}/>
              </label>
            )}
            {error && <p role="alert" style={{ color: "var(--danger-text)", fontSize: 12 }}>{error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={closeAction} disabled={busy} style={btnSecondary()}>Cancel</button>
              <button onClick={submitAction} disabled={!valid || busy} style={btnPrimary(!valid || busy)}>{busy ? "Saving…" : "Confirm"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const ACTION_TITLES: Record<ActionKind, string> = {
  refund_review: "Mark refund under review",
  refund_approve: "Approve refund",
  refund_reject: "Reject refund",
  refund_record: "Record repayment",
  rework_schedule: "Schedule rework visit",
  rework_start: "Start rework visit",
  rework_complete: "Complete rework visit",
  warranty_respond: "Respond to warranty claim",
  warranty_resolve: "Resolve warranty claim",
};

/** `btn-secondary` / `btn-primary` were used throughout this page but are not
 *  defined in the portal's stylesheet (no Tailwind, and globals.css has no
 *  such rules), so those controls rendered as bare browser buttons. These are
 *  the real token-based equivalents. */
function btnSecondary(active = false): React.CSSProperties {
  return {
    height: 34, padding: "0 13px", fontSize: 13, borderRadius: 8,
    border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
    background: active ? "var(--accent-muted)" : "var(--surface)",
    color: active ? "var(--brand)" : "var(--text-secondary)",
    fontWeight: active ? 700 : 500, cursor: "pointer", fontFamily: "inherit",
    whiteSpace: "nowrap",
  };
}
function btnPrimary(disabled: boolean): React.CSSProperties {
  return {
    height: 34, padding: "0 15px", fontSize: 13, fontWeight: 600, borderRadius: 8,
    border: "1px solid var(--brand)", background: "var(--brand)", color: "#fff",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.55 : 1,
    fontFamily: "inherit",
  };
}

const fieldStyle: React.CSSProperties = {
  padding: 11, borderRadius: 8, border: "1px solid var(--border-default)",
  background: "var(--surface-default)", color: "var(--text-primary)",
};

function Kpi({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: string; tone: "default" | "warning" | "danger" | "success" }) {
  const color = tone === "warning" ? "var(--warning-text)" : tone === "danger" ? "var(--danger-text)" : tone === "success" ? "var(--success-text)" : "var(--text-primary)";
  return (
    <div style={{ padding: "14px 16px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14 }}>
      <p style={{ fontSize: 20, fontWeight: 800, color, margin: 0, lineHeight: 1.1 }}>{value}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "3px 0 0" }}>{label}</p>
      {sub && <p style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)", margin: "4px 0 0" }}>{sub}</p>}
    </div>
  );
}

/** Row payloads carry far more than fits in the grid — the customer's reason,
 *  the money actually recovered from the provider, escalation notes. */
function DetailDrawer({ row, mode, onClose }: { row: Record<string, unknown>; mode: RemedyMode; onClose: () => void }) {
  const fields: [string, React.ReactNode][] =
    mode === "refunds" ? [
      ["Refund", String(row.refund_number ?? "—")],
      ["Status", words(row.status)],
      ["Type", words(row.refund_type)],
      ["Complaint", String(row.complaint_number ?? "—")],
      ["Job", String(row.job_number ?? "—")],
      ["Service", String(row.service_name ?? "—")],
      ["Requested", money(row.requested_amount)],
      ["Approved", money(row.approved_amount)],
      ["Recorded", money(row.recorded_amount)],
      ["Method", words(row.refund_method) || "—"],
      ["Credit recovered from you", money(row.provider_credit_deducted)],
      ["Response due", dtl(row.provider_response_due_at)],
    ] : mode === "rework" ? [
      ["Rework", String(row.id ?? "").slice(0, 8)],
      ["Status", words(row.status)],
      ["Scheduled", row.scheduled_date && row.scheduled_date !== "None" ? dt(row.scheduled_date) : "—"],
      ["Created", dt(row.created_at)],
    ] : [
      ["Claim", String(row.claim_id ?? "").slice(0, 8)],
      ["Status", words(row.status)],
      ["Issue type", words(row.claim_type)],
      ["Job", String(row.job_id ?? "—")],
      ["Requested", money(row.amount_requested)],
      ["Approved", money(row.amount_approved)],
      ["Warranty ends", dt(row.warranty_expires_at)],
      ["Response due", dtl(row.provider_response_due_at)],
      ["Credit recovered from you", money(row.provider_credit_deducted)],
    ];

  const longText = mode === "refunds"
    ? [["Customer reason", row.reason], ["Rejection reason", row.rejection_reason], ["Escalation reason", row.escalation_reason]]
    : mode === "rework"
      ? [["Reason", row.rework_reason], ["Notes to customer", row.customer_visible_notes]]
      : [["Description", row.description], ["Your resolution", row.provider_resolution], ["Escalation reason", row.escalation_reason]];

  return (
    <div role="dialog" aria-modal="true" onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, zIndex: 999, display: "flex", justifyContent: "flex-end", background: "rgba(0,0,0,.45)" }}>
      <div style={{ width: "min(460px,100%)", height: "100%", overflowY: "auto", background: "var(--surface-elevated)", borderLeft: "1px solid var(--border-default)", padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 17 }}>Request details</h2>
          <button onClick={onClose} style={btnSecondary()}>Close</button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 18 }}>
          {fields.map(([label, value]) => (
            <div key={label}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{value || "—"}</p>
            </div>
          ))}
        </div>
        {longText.filter(([, v]) => v).map(([label, value]) => (
          <div key={String(label)} style={{ marginBottom: 14 }}>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-tertiary)", margin: "0 0 4px" }}>{String(label)}</p>
            <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{String(value)}</p>
          </div>
        ))}
        {typeof row.proof_media_url === "string" && row.proof_media_url && (
          <a href={row.proof_media_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12.5, color: "var(--brand)" }}>
            View payment proof
          </a>
        )}
      </div>
    </div>
  );
}
