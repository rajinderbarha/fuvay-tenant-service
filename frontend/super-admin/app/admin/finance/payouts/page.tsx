"use client";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight, RefreshCw, Download, Search } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader, SummaryCardsRow } from "../../../../components/shared/ui";
import { ActionMenu } from "../../../../components/shared/layout";
import { financeApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import type { FinancePayout } from "../../../../lib/api";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending Review" },
  { value: "approved", label: "Approved" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "rejected", label: "Rejected" },
];
const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  completed: "success", approved: "info", processing: "warning",
  failed: "danger", rejected: "danger", pending: "warning",
};

export default function PayoutsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [modal, setModal] = useState<{ type: "reject" | "fail"; payout: FinancePayout } | null>(null);
  const [reason, setReason] = useState("");

  const summary = useApi(useCallback(() => financeApi.getPayoutsSummary(), []));
  const payouts = useApi(useCallback(() => financeApi.listPayouts({
    q: search || undefined, status: status || undefined, pageSize: 200,
  }), [search, status]));

  const approveAction = useAction(useCallback((id: string) => financeApi.approvePayout(id), []));
  const rejectAction = useAction(useCallback((id: string, r: string) => financeApi.rejectPayout(id, r), []));
  const processingAction = useAction(useCallback((id: string) => financeApi.markProcessing(id), []));
  const completedAction = useAction(useCallback((id: string) => financeApi.markCompleted(id), []));
  const failedAction = useAction(useCallback((id: string, r: string) => financeApi.markFailed(id, r), []));

  function refetchAll() { summary.refetch(); payouts.refetch(); }

  async function handleApprove(p: FinancePayout) { if (await approveAction.execute(p.payout_id)) refetchAll(); }
  async function handleMarkProcessing(p: FinancePayout) { if (await processingAction.execute(p.payout_id)) refetchAll(); }
  async function handleMarkCompleted(p: FinancePayout) { if (await completedAction.execute(p.payout_id)) refetchAll(); }
  async function handleModalSubmit() {
    if (!modal) return;
    const res = modal.type === "reject"
      ? await rejectAction.execute(modal.payout.payout_id, reason)
      : await failedAction.execute(modal.payout.payout_id, reason);
    if (res) { setModal(null); refetchAll(); }
  }
  async function handleExport() {
    const res = await financeApi.exportPayouts({ status: status || undefined });
    const header = "payout_number,tenant_name,payout_type,requested_amount,status,requested_on\n";
    const body = res.rows.map(r => [r.payout_number ?? "", r.tenant_name ?? "", r.payout_type, r.requested_amount, r.status, r.requested_on ?? ""].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "payouts.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const rows = payouts.data?.items ?? [];
  const s = summary.data;

  const columns = [
    { key: "payout_number", label: "Payout Ref", width: 140, render: (_: unknown, row: FinancePayout) => (
      <span style={{ fontFamily: "monospace", fontSize: 12 }}>{row.payout_number ?? row.payout_id.slice(0, 8)}</span>
    )},
    { key: "tenant_name", label: "Tenant / Beneficiary", render: (_: unknown, row: FinancePayout) => row.tenant_name },
    { key: "payout_type", label: "Payout Type", width: 150, render: (_: unknown, row: FinancePayout) => (
      <span style={{ textTransform: "capitalize" }}>{row.payout_type.replace(/_/g, " ")}</span>
    )},
    { key: "requested_amount", label: "Requested Amount", width: 150, render: (_: unknown, row: FinancePayout) => `₹${row.requested_amount.toLocaleString("en-IN")}` },
    { key: "approved_amount", label: "Approved Amount", width: 150, render: (_: unknown, row: FinancePayout) => row.approved_amount != null ? `₹${row.approved_amount.toLocaleString("en-IN")}` : "—" },
    { key: "status", label: "Status", width: 140, render: (_: unknown, row: FinancePayout) => (
      <Badge variant={STATUS_BADGE[row.status] ?? "muted"}>{row.status}</Badge>
    )},
    { key: "requested_on", label: "Requested On", width: 140, render: (_: unknown, row: FinancePayout) => row.requested_on ? new Date(row.requested_on).toLocaleDateString("en-IN") : "—" },
    { key: "processed_on", label: "Processed On", width: 140, render: (_: unknown, row: FinancePayout) => row.processed_on ? new Date(row.processed_on).toLocaleDateString("en-IN") : "—" },
    { key: "payout_id", label: "", width: 110, render: (_: unknown, row: FinancePayout) => (
      <ActionMenu items={[
        { label: "View Payout", onClick: () => router.push(`/admin/finance/payouts/${row.payout_id}`) },
        row.status === "pending" && { label: "Approve", onClick: () => handleApprove(row) },
        (row.status === "pending" || row.status === "approved") && { label: "Reject", onClick: () => { setModal({ type: "reject", payout: row }); setReason(""); }, destructive: true },
        row.status === "approved" && { label: "Mark Processing", onClick: () => handleMarkProcessing(row) },
        row.status === "processing" && { label: "Mark Completed", onClick: () => handleMarkCompleted(row) },
        (row.status === "processing" || row.status === "approved") && { label: "Mark Failed", onClick: () => { setModal({ type: "fail", payout: row }); setReason(""); } },
        { label: "View Audit Logs", onClick: () => router.push(`/admin/finance/payouts/${row.payout_id}#audit`) },
      ]}/>
    )},
  ];

  return (
    <AdminLayout activeNav="finance-payouts">
      <SectionHeader title="Payouts" subtitle="Manage payout requests, payout approvals, transfers, and settlement history."/>
      <div style={{ padding: "0 28px 32px" }}>
        {s && (
          <SummaryCardsRow cards={[
            { label: "Pending Payouts", value: s.pending_payouts },
            { label: "Approved Payouts", value: s.approved_payouts },
            { label: "Processing", value: s.processing },
            { label: "Failed Payouts", value: s.failed_payouts, accent: s.failed_payouts > 0 },
            { label: "Completed Payouts", value: s.completed_payouts },
            { label: "Total Payout Value", value: `₹${s.total_payout_value.toLocaleString("en-IN")}` },
          ]}/>
        )}
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <ArrowUpRight size={18} color="var(--brand)"/>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Payouts</span>
              <Badge variant="muted">{rows.length}</Badge>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={refetchAll}>Refresh</Btn>
              <Btn variant="secondary" size="sm" icon={<Download size={13}/>} onClick={handleExport}>Export</Btn>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 10, marginBottom: 12 }}>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input placeholder="Search payout ref / tenant…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius:"var(--radius-md)",
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}/>
            </div>
            <Select label="" value={status} onChange={setStatus} options={STATUS_OPTIONS}/>
          </div>
          {(approveAction.error || rejectAction.error || processingAction.error || completedAction.error || failedAction.error) && (
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
              {approveAction.error || rejectAction.error || processingAction.error || completedAction.error || failedAction.error}
            </p>
          )}
          <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]} loading={payouts.loading}
            emptyText="No payouts created."/>
        </Card>
      </div>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal?.type === "reject" ? "Reject Payout" : "Mark Payout Failed"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input label="Reason *" value={reason} onChange={setReason}/>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" onClick={handleModalSubmit} loading={rejectAction.loading || failedAction.loading}>Confirm</Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
