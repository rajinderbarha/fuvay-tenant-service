"use client";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, RefreshCw, Download, Search } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { SummaryCardsRow } from "../../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../../components/pricing/ActionMenu";
import { financeApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";
import { usePermissions } from "../../../../hooks/usePermissions";
import type { FinanceDeposit } from "../../../../lib/api";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "unpaid", label: "Not Required / Pending Payment" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "pending_verification", label: "Pending Verification" },
  { value: "paid", label: "Held" },
  { value: "partially_adjusted", label: "Partially Adjusted" },
  { value: "refund_requested", label: "Refund Requested" },
  { value: "refunded", label: "Refunded" },
  { value: "forfeited", label: "Forfeited" },
  { value: "blocked", label: "Blocked" },
];
const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  paid: "success", refunded: "muted", forfeited: "danger", blocked: "danger",
  partially_paid: "warning", partially_adjusted: "warning",
  pending_verification: "info", refund_requested: "warning", unpaid: "muted",
};

function StatusBadge({ status }: { status: string }) {
  return <Badge variant={STATUS_BADGE[status] ?? "muted"}>{status.replace(/_/g, " ")}</Badge>;
}

export default function SecurityDepositsPage() {
  const router = useRouter();
  const perm = usePermissions();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const summary = useApi(useCallback(() => financeApi.getDepositsSummary(), []));
  const deposits = useApi(useCallback(() => financeApi.listDeposits({
    q: search || undefined, status: status || undefined, pageSize: 200,
  }), [search, status]));

  const [actionModal, setActionModal] = useState<{ type: "reject" | "offline" | "refund" | "adjust"; deposit: FinanceDeposit } | null>(null);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");

  const approveAction = useAction(useCallback((id: string) => financeApi.approveDeposit(id), []));
  const rejectAction = useAction(useCallback((id: string, r: string) => financeApi.rejectDeposit(id, r), []));
  const offlineAction = useAction(useCallback((id: string, amt: number, ref: string, notes: string) =>
    financeApi.recordOfflineDeposit(id, amt, ref, notes), []));
  const refundAction = useAction(useCallback((id: string, amt: number, r: string) => financeApi.refundDeposit(id, amt, r), []));
  const adjustAction = useAction(useCallback((id: string, amt: number, r: string) => financeApi.adjustDeposit(id, amt, r), []));

  function refetchAll() { summary.refetch(); deposits.refetch(); }

  async function handleApprove(d: FinanceDeposit) {
    const res = await approveAction.execute(d.deposit_id);
    if (res) refetchAll();
  }
  function openModal(type: "reject" | "offline" | "refund" | "adjust", d: FinanceDeposit) {
    setActionModal({ type, deposit: d }); setAmount(""); setReason("");
  }
  async function handleModalSubmit() {
    if (!actionModal) return;
    const { type, deposit } = actionModal;
    let res = null;
    if (type === "reject") res = await rejectAction.execute(deposit.deposit_id, reason);
    if (type === "offline") res = await offlineAction.execute(deposit.deposit_id, Number(amount), reason, reason);
    if (type === "refund") res = await refundAction.execute(deposit.deposit_id, Number(amount), reason);
    if (type === "adjust") res = await adjustAction.execute(deposit.deposit_id, Number(amount), reason);
    if (res) { setActionModal(null); refetchAll(); }
  }
  async function handleExport() {
    const res = await financeApi.exportDeposits({ status: status || undefined });
    const header = "tenant_name,required_amount,received_amount,status,created_at\n";
    const body = res.rows.map(r => [r.tenant_name ?? "", r.required_amount, r.received_amount, r.status, r.created_at ?? ""].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "security_deposits.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const rows = deposits.data?.items ?? [];
  const s = summary.data;

  const columns = [
    { key: "tenant_name", label: "Tenant", render: (_: unknown, row: FinanceDeposit) => (
      <div>
        <div style={{ fontWeight: 600 }}>{row.tenant_name}</div>
        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{row.vertical} · {row.city}</div>
      </div>
    )},
    { key: "required_amount", label: "Required Amount", width: 140, render: (_: unknown, row: FinanceDeposit) => `₹${row.required_amount.toLocaleString("en-IN")}` },
    { key: "received_amount", label: "Received Amount", width: 140, render: (_: unknown, row: FinanceDeposit) => `₹${row.received_amount.toLocaleString("en-IN")}` },
    { key: "pending_amount", label: "Pending Amount", width: 130, render: (_: unknown, row: FinanceDeposit) => `₹${row.pending_amount.toLocaleString("en-IN")}` },
    { key: "status", label: "Status", width: 160, render: (_: unknown, row: FinanceDeposit) => <StatusBadge status={row.status}/> },
    { key: "hold_state", label: "Hold State", width: 110, render: (_: unknown, row: FinanceDeposit) => row.hold_state ?? "—" },
    { key: "adjusted_amount", label: "Adjusted Amount", width: 140, render: (_: unknown, row: FinanceDeposit) => `₹${row.adjusted_amount.toLocaleString("en-IN")}` },
    { key: "created_at", label: "Created", width: 120, render: (_: unknown, row: FinanceDeposit) => row.created_at ? new Date(row.created_at).toLocaleDateString("en-IN") : "—" },
    { key: "deposit_id", label: "", width: 110, render: (_: unknown, row: FinanceDeposit) => (
      // FINAL-L5-05O Part 22: overflow menu is permission-filtered before
      // opening -- mutation items are omitted (not disabled) for any role
      // lacking the real backend permission the action calls, matching
      // rule 12 (Admin Read Only sees zero mutation controls) and 23
      // (denied items must not appear even transiently).
      <ActionMenu items={[
        { label: "View Deposit Detail", onClick: () => router.push(`/admin/finance/deposits/${row.deposit_id}`) },
        (row.status === "unpaid" || row.status === "partially_paid" || row.status === "pending_verification") &&
          perm.has("finance:deposits:approve") && { label: "Approve Deposit", onClick: () => handleApprove(row) },
        perm.has("finance:deposits:approve") && { label: "Reject Deposit", onClick: () => openModal("reject", row) },
        perm.has("finance:deposits:update") && { label: "Record Offline Deposit", onClick: () => openModal("offline", row) },
        perm.has("finance:deposits:refund") && { label: "Initiate Refund", onClick: () => openModal("refund", row) },
        perm.has("finance:deposits:update") && { label: "Forfeit / Adjust", onClick: () => openModal("adjust", row) },
        { label: "View Audit Logs", onClick: () => router.push(`/admin/finance/deposits/${row.deposit_id}#audit`) },
      ]}/>
    )},
  ];

  return (
    <AdminLayout activeNav="finance-deposits">
      <RequirePermission requiredPermission="finance:deposits:read" parentLabel="Dashboard">
      <SectionHeader title="Security Deposits" subtitle="Manage provider security deposits, hold status, approvals, refunds, and adjustments." />
      <div style={{ padding: "0 28px 32px" }}>
        {s && (
          <SummaryCardsRow cards={[
            { label: "Total Deposit Accounts", value: s.total_deposit_accounts },
            { label: "Active Held Deposits", value: s.active_held_deposits },
            { label: "Pending Deposits", value: s.pending_deposits },
            { label: "Refund Pending", value: s.refund_pending },
            { label: "Refunded", value: s.refunded },
            { label: "Deposit Risk Cases", value: s.deposit_risk_cases, accent: s.deposit_risk_cases > 0 },
          ]}/>
        )}
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Shield size={18} color="var(--brand)"/>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Security Deposits</span>
              <Badge variant="muted">{rows.length}</Badge>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={refetchAll}>Refresh</Btn>
              {/* FINAL-L5-05U: export must not flash for roles that lack it
                  (Admin Read Only/Operations/Security all lack finance:hub:export) --
                  backend already enforced this, frontend was not. */}
              {perm.has("finance:hub:export") && (
                <Btn variant="secondary" size="sm" icon={<Download size={13}/>} onClick={handleExport}>Export</Btn>
              )}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 10, marginBottom: 12 }}>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
              <input placeholder="Search tenant / business…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius:"var(--radius-md)",
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}/>
            </div>
            <Select label="" value={status} onChange={setStatus} options={STATUS_OPTIONS}/>
          </div>
          {(approveAction.error || rejectAction.error || offlineAction.error || refundAction.error || adjustAction.error) && (
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
              {approveAction.error || rejectAction.error || offlineAction.error || refundAction.error || adjustAction.error}
            </p>
          )}
          <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]} loading={deposits.loading}
            emptyText="No deposits found."/>
        </Card>
      </div>

      <Modal open={!!actionModal} onClose={() => setActionModal(null)} title={
        actionModal?.type === "reject" ? "Reject Deposit" :
        actionModal?.type === "offline" ? "Record Offline Deposit" :
        actionModal?.type === "refund" ? "Initiate Refund" : "Forfeit / Adjust Deposit"
      }>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {actionModal?.type !== "reject" && (
            <Input label="Amount ₹" type="number" value={amount} onChange={setAmount}
              hint={actionModal?.type === "adjust" ? "Use a negative amount to forfeit / deduct." : undefined}/>
          )}
          <Input label={actionModal?.type === "offline" ? "Reference / Notes" : "Reason *"} value={reason} onChange={setReason}/>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setActionModal(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" onClick={handleModalSubmit}
              loading={rejectAction.loading || offlineAction.loading || refundAction.loading || adjustAction.loading}>
              Confirm
            </Btn>
          </div>
        </div>
      </Modal>
      </RequirePermission>
    </AdminLayout>
  );
}
