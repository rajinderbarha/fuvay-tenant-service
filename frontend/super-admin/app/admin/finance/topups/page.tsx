"use client";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Wallet, RefreshCw, Download, Search, Package } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { SummaryCardsRow } from "../../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../../components/pricing/ActionMenu";
import { financeApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import type { FinanceTopup } from "../../../../lib/api";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "initiated", label: "Initiated" },
  { value: "paid_pending_credit", label: "Paid — Pending Credit" },
  { value: "credited", label: "Credited" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "refunded", label: "Refunded" },
  { value: "partially_refunded", label: "Partially Refunded" },
];
const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  credited: "success", failed: "danger", cancelled: "muted",
  refunded: "muted", partially_refunded: "warning",
  initiated: "info", paid_pending_credit: "warning",
};

export default function CreditTopupsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [refundModal, setRefundModal] = useState<FinanceTopup | null>(null);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");

  const summary = useApi(useCallback(() => financeApi.getTopupsSummary(), []));
  const topups = useApi(useCallback(() => financeApi.listTopups({
    q: search || undefined, paymentStatus: status || undefined, pageSize: 200,
  }), [search, status]));

  const retryAction = useAction(useCallback((id: string) => financeApi.retryCreditPosting(id), []));
  const refundAction = useAction(useCallback((id: string, amt: number, r: string) => financeApi.refundTopup(id, amt, r), []));

  function refetchAll() { summary.refetch(); topups.refetch(); }

  async function handleRetry(t: FinanceTopup) {
    const res = await retryAction.execute(t.topup_id);
    if (res) refetchAll();
  }
  async function handleRefundSubmit() {
    if (!refundModal) return;
    const res = await refundAction.execute(refundModal.topup_id, Number(amount), reason);
    if (res) { setRefundModal(null); refetchAll(); }
  }
  async function handleExport() {
    const res = await financeApi.exportTopups({ paymentStatus: status || undefined });
    const header = "tenant_name,order_ref,credits_purchased,amount_paid,payment_status,created_at\n";
    const body = res.rows.map(r => [r.tenant_name ?? "", r.order_ref ?? "", r.credits_purchased, r.amount_paid, r.payment_status, r.created_at ?? ""].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "credit_topups.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const rows = topups.data?.items ?? [];
  const s = summary.data;

  const columns = [
    { key: "tenant_name", label: "Tenant", render: (_: unknown, row: FinanceTopup) => row.tenant_name },
    { key: "order_ref", label: "Order Ref", width: 160, render: (_: unknown, row: FinanceTopup) => (
      <span style={{ fontFamily: "monospace", fontSize: 12 }}>{row.order_ref ?? "—"}</span>
    )},
    { key: "credits_purchased", label: "Credits Purchased", width: 150, render: (_: unknown, row: FinanceTopup) =>
      (row.credits_purchased + row.bonus_credits).toLocaleString("en-IN") },
    { key: "amount_paid", label: "Amount Paid", width: 130, render: (_: unknown, row: FinanceTopup) => `₹${row.amount_paid.toLocaleString("en-IN")}` },
    { key: "payment_method", label: "Payment Method", width: 140, render: (_: unknown, row: FinanceTopup) => row.payment_method ?? "—" },
    { key: "payment_status", label: "Payment Status", width: 160, render: (_: unknown, row: FinanceTopup) => (
      <Badge variant={STATUS_BADGE[row.payment_status] ?? "muted"}>{row.payment_status.replace(/_/g, " ")}</Badge>
    )},
    { key: "wallet_credit_status", label: "Wallet Credit Status", width: 150, render: (_: unknown, row: FinanceTopup) => row.wallet_credit_status },
    { key: "created_at", label: "Created", width: 120, render: (_: unknown, row: FinanceTopup) => row.created_at ? new Date(row.created_at).toLocaleDateString("en-IN") : "—" },
    { key: "topup_id", label: "", width: 110, render: (_: unknown, row: FinanceTopup) => (
      <ActionMenu items={[
        { label: "View Top-up Detail", onClick: () => router.push(`/admin/finance/topups/${row.topup_id}`) },
        row.payment_status === "paid_pending_credit" && { label: "Retry Credit Posting", onClick: () => handleRetry(row) },
        { label: "Refund", onClick: () => { setRefundModal(row); setAmount(""); setReason(""); } },
        { label: "View Ledger", onClick: () => router.push(`/admin/finance/topups/${row.topup_id}`) },
        { label: "View Audit Logs", onClick: () => router.push(`/admin/finance/topups/${row.topup_id}#audit`) },
      ]}/>
    )},
  ];

  return (
    <AdminLayout activeNav="finance-topups">
      <SectionHeader title="Credit Top-ups" subtitle="Monitor credit purchases, wallet funding, top-up approvals, and failures."/>
      <div style={{ padding: "0 28px 32px" }}>
        {s && (
          <SummaryCardsRow cards={[
            { label: "Total Top-ups", value: s.total_topups },
            { label: "Total Top-up Value", value: `₹${s.total_topup_value.toLocaleString("en-IN")}` },
            { label: "Pending Top-ups", value: s.pending_topups },
            { label: "Failed Top-ups", value: s.failed_topups, accent: s.failed_topups > 0 },
            { label: "Refunded Top-ups", value: s.refunded_topups },
            { label: "Top-up Value This Month", value: `₹${s.topup_value_this_month.toLocaleString("en-IN")}` },
          ]}/>
        )}
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Wallet size={18} color="var(--brand)"/>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Credit Top-ups</span>
              <Badge variant="muted">{rows.length}</Badge>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" icon={<Package size={13}/>} onClick={() => router.push("/admin/packages?type=credit_topup")}>Manage Credit Packages</Btn>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={refetchAll}>Refresh</Btn>
              <Btn variant="secondary" size="sm" icon={<Download size={13}/>} onClick={handleExport}>Export</Btn>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 10, marginBottom: 12 }}>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input placeholder="Search tenant / order ref…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}/>
            </div>
            <Select label="" value={status} onChange={setStatus} options={STATUS_OPTIONS}/>
          </div>
          {(retryAction.error || refundAction.error) && <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{retryAction.error || refundAction.error}</p>}
          <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]} loading={topups.loading}
            emptyText="No top-ups found."/>
        </Card>
      </div>

      <Modal open={!!refundModal} onClose={() => setRefundModal(null)} title="Refund Top-up">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input label="Refund Amount ₹" type="number" value={amount} onChange={setAmount}/>
          <Input label="Reason" value={reason} onChange={setReason}/>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setRefundModal(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={refundAction.loading} onClick={handleRefundSubmit}>Confirm Refund</Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
