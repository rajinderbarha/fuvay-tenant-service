"use client";
import { TableSurface } from "@serviceos/design-system";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Modal, SummaryCardsRow, Pagination } from "../../../../components/shared/ui";
import { financeApi, CustomerServiceCredit, CustomerCreditSummary } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  active: "success", partially_used: "info", used: "muted",
  expired: "warning", cancelled: "danger", reversed: "danger",
};
const fmt = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;

export default function CustomerCreditsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [extendId, setExtendId] = useState<string | null>(null);
  const [newExpiry, setNewExpiry] = useState("");

  const summary = useApi(useCallback(() => financeApi.getCreditSummary(), []));
  const list = useApi(useCallback(() =>
    financeApi.listCredits({ page, limit: 50, status: statusFilter || undefined }),
    [page, statusFilter]));

  const s: CustomerCreditSummary | undefined = summary.data;

  async function handleCancel() {
    if (!cancelId) return;
    setBusy(true);
    await financeApi.cancelCredit(cancelId, cancelReason || "Cancelled by admin");
    setCancelId(null); setCancelReason("");
    list.refetch(); summary.refetch();
    setBusy(false);
  }

  async function handleExtend() {
    if (!extendId || !newExpiry) return;
    setBusy(true);
    await financeApi.extendCredit(extendId, new Date(newExpiry).toISOString());
    setExtendId(null); setNewExpiry("");
    list.refetch();
    setBusy(false);
  }

  return (
    <AdminLayout activeNav="finance">
      <SectionHeader
        title="Customer Service Credits"
        subtitle="ServiceOS platform credits issued to customers after dispute settlements. NOT cash refunds."
        actions={<Btn variant="ghost" onClick={() => { summary.refetch(); list.refetch(); }}>Refresh</Btn>}
      />

      {s && (
        <SummaryCardsRow cards={[
          { label: "Total Credits", value: s.total_credits },
          { label: "Active", value: s.active_credits, accent: s.active_credits > 0 },
          { label: "Active Balance", value: fmt(s.active_credit_balance) },
          { label: "From Disputes", value: s.credits_from_disputes },
          { label: "Used", value: s.used_credits },
          { label: "Expired", value: s.expired_credits },
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
            {["active","partially_used","used","expired","cancelled","reversed"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {list.data?.meta.total ?? 0} records
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-subtle, var(--bg))" }}>
                {["Credit #","Status","Type","Source","Amount","Remaining","Expires","Actions"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.loading && (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</td></tr>
              )}
              {!list.loading && !list.data?.credits.length && (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>No credits found.</td></tr>
              )}
              {list.data?.credits.map((c: CustomerServiceCredit) => (
                <tr key={c.id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 12px", fontFamily: "monospace", fontSize: 12 }}>{c.credit_number}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <Badge variant={STATUS_VARIANT[c.status] ?? "muted"}>{c.status.replace(/_/g, " ")}</Badge>
                  </td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>{c.credit_type.replace(/_/g, " ")}</td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>{c.source.replace(/_/g, " ")}</td>
                  <td style={{ padding: "10px 12px", fontSize: 13, fontWeight: 700 }}>{fmt(c.amount)}</td>
                  <td style={{ padding: "10px 12px", fontSize: 13 }}>{fmt(c.remaining_amount)}</td>
                  <td style={{ padding: "10px 12px", fontSize: 12 }}>
                    {c.expires_at ? new Date(c.expires_at).toLocaleDateString("en-IN") : "—"}
                  </td>
                  <td style={{ padding: "10px 12px", display: "flex", gap: 6 }}>
                    {["active","partially_used"].includes(c.status) && (
                      <>
                        <Btn size="sm" variant="ghost" onClick={() => { setExtendId(c.id); setNewExpiry(""); }}>Extend</Btn>
                        <Btn size="sm" variant="ghost" onClick={() => { setCancelId(c.id); setCancelReason(""); }}>Cancel</Btn>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>

        {list.data?.meta && <Pagination page={page} pageSize={50} total={list.data.meta.total}
          pageCount={list.data.meta.total_pages} onPage={setPage} itemLabel="credits" />}
      </Card>

      <Modal open={cancelId !== null} onClose={() => setCancelId(null)} title="Cancel Credit">
        {cancelId !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
              The remaining balance will be forfeited. The customer will be notified.
            </p>
            <textarea
              value={cancelReason}
              onChange={e => setCancelReason(e.target.value)}
              placeholder="Reason for cancellation"
              rows={3}
              style={{ padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13, resize: "vertical" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setCancelId(null)}>Back</Btn>
              <Btn variant="danger" disabled={busy} onClick={handleCancel}>Cancel Credit</Btn>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={extendId !== null} onClose={() => setExtendId(null)} title="Extend Credit Expiry">
        {extendId !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label style={{ fontSize: 13, fontWeight: 600 }}>New expiry date</label>
            <input
              type="date"
              value={newExpiry}
              onChange={e => setNewExpiry(e.target.value)}
              min={new Date().toISOString().slice(0, 10)}
              style={{ padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setExtendId(null)}>Back</Btn>
              <Btn variant="primary" disabled={busy || !newExpiry} onClick={handleExtend}>Extend</Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
