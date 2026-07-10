"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Modal } from "../../../../components/shared/ui";
import { SummaryCardsRow } from "../../../../components/pricing/SummaryCard";
import { financeApi, DisputeSettlement, DisputeSettlementSummary } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  executed: "success", approved: "info", draft: "muted",
  pending_approval: "warning", executing: "info",
  failed: "danger", cancelled: "danger", reversed: "danger",
};
const fmt = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;

function SettlementRow({ s, onApprove, onExecute, onCancel }: {
  s: DisputeSettlement;
  onApprove: (id: string) => void;
  onExecute: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  return (
    <tr>
      <td style={{ padding: "10px 12px", fontFamily: "monospace", fontSize: 12 }}>{s.settlement_number}</td>
      <td style={{ padding: "10px 12px", fontSize: 12 }}>
        <Badge variant={STATUS_VARIANT[s.settlement_status] ?? "muted"}>{s.settlement_status}</Badge>
      </td>
      <td style={{ padding: "10px 12px", fontSize: 12 }}>{s.settlement_type.replace(/_/g, " ")}</td>
      <td style={{ padding: "10px 12px", fontSize: 13, fontWeight: 700 }}>{fmt(s.settlement_amount)}</td>
      <td style={{ padding: "10px 12px", fontSize: 12 }}>
        {fmt(s.tenant_wallet_deduction_amount)} wallet / {fmt(s.security_deposit_deduction_amount)} deposit
      </td>
      <td style={{ padding: "10px 12px", fontSize: 12 }}>
        {s.executed_at ? new Date(s.executed_at).toLocaleDateString("en-IN") :
          new Date(s.created_at).toLocaleDateString("en-IN")}
      </td>
      <td style={{ padding: "10px 12px" }}>
        {s.settlement_status === "draft" || s.settlement_status === "pending_approval" ? (
          <Btn size="sm" variant="primary" onClick={() => onApprove(s.id)} style={{ marginRight: 6 }}>Approve</Btn>
        ) : null}
        {s.settlement_status === "approved" ? (
          <Btn size="sm" variant="primary" onClick={() => onExecute(s.id)} style={{ marginRight: 6 }}>Execute</Btn>
        ) : null}
        {!["executed", "cancelled", "reversed"].includes(s.settlement_status) ? (
          <Btn size="sm" variant="ghost" onClick={() => onCancel(s.id)}>Cancel</Btn>
        ) : null}
      </td>
    </tr>
  );
}

export default function DisputeSettlementsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [busy, setBusy] = useState(false);

  const summary = useApi(useCallback(() => financeApi.getSettlementSummary(), []));
  const list = useApi(useCallback(() =>
    financeApi.listSettlements({ page, limit: 50, status: statusFilter || undefined }),
    [page, statusFilter]));

  const s: DisputeSettlementSummary | undefined = summary.data;

  async function handleApprove(id: string) {
    setBusy(true);
    await financeApi.approveSettlement(id);
    list.refetch();
    setBusy(false);
  }
  async function handleExecute(id: string) {
    setBusy(true);
    await financeApi.executeSettlement(id);
    list.refetch(); summary.refetch();
    setBusy(false);
  }
  async function handleCancel() {
    if (!cancelId) return;
    setBusy(true);
    await financeApi.cancelSettlement(cancelId, cancelReason || "Cancelled by admin");
    setCancelId(null); setCancelReason("");
    list.refetch();
    setBusy(false);
  }

  return (
    <AdminLayout activeNav="finance">
      <SectionHeader
        title="Dispute Settlements"
        subtitle="Platform credit issued after dispute review. Tenant wallet / security deposit deducted."
        actions={<Btn variant="ghost" onClick={() => { summary.refetch(); list.refetch(); }}>Refresh</Btn>}
      />

      {s && (
        <SummaryCardsRow cards={[
          { label: "Total Settlements", value: s.total_settlements },
          { label: "Pending Approval", value: s.pending_approval, accent: s.pending_approval > 0 },
          { label: "Executed", value: s.executed_settlements },
          { label: "Credits Issued", value: fmt(s.customer_credits_issued) },
          { label: "Wallet Deducted", value: fmt(s.tenant_wallet_deducted) },
          { label: "Deposit Deducted", value: fmt(s.security_deposit_deducted) },
        ]} />
      )}

      <Card padding={0} style={{ marginTop: 20 }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 10, alignItems: "center" }}>
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-input, var(--bg))", fontSize: 13 }}
          >
            <option value="">All statuses</option>
            {["draft","pending_approval","approved","executing","executed","failed","cancelled","reversed"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {list.data?.meta.total ?? 0} records
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-subtle, var(--bg))" }}>
                {["Settlement #","Status","Type","Amount","Deductions","Date","Actions"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.loading && (
                <tr><td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</td></tr>
              )}
              {!list.loading && !list.data?.settlements.length && (
                <tr><td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>No settlements found.</td></tr>
              )}
              {list.data?.settlements.map(s => (
                <SettlementRow key={s.id} s={s}
                  onApprove={handleApprove}
                  onExecute={handleExecute}
                  onCancel={(id) => setCancelId(id)}
                />
              ))}
            </tbody>
          </table>
        </div>

        {(list.data?.meta.total_pages ?? 1) > 1 && (
          <div style={{ padding: "12px 16px", display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Btn>
            <span style={{ fontSize: 13, padding: "6px 0" }}>Page {page} / {list.data?.meta.total_pages}</span>
            <Btn size="sm" variant="ghost" disabled={page >= (list.data?.meta.total_pages ?? 1)} onClick={() => setPage(p => p + 1)}>Next</Btn>
          </div>
        )}
      </Card>

      <Modal open={cancelId !== null} onClose={() => setCancelId(null)} title="Cancel Settlement">
        {cancelId !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
              This will cancel the settlement. No funds will be moved.
            </p>
            <textarea
              value={cancelReason}
              onChange={e => setCancelReason(e.target.value)}
              placeholder="Reason for cancellation (optional)"
              rows={3}
              style={{ padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13, resize: "vertical" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setCancelId(null)}>Back</Btn>
              <Btn variant="danger" disabled={busy} onClick={handleCancel}>Cancel Settlement</Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
