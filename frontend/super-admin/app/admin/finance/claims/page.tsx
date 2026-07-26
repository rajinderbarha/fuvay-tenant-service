"use client";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertOctagon, RefreshCw, Download, Search } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { SummaryCardsRow } from "../../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../../components/pricing/ActionMenu";
import { financeApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import type { FinanceClaim } from "../../../../lib/api";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "New / Pending Review" },
  { value: "pending_review", label: "Pending Review" },
  { value: "investigating", label: "Investigating" },
  { value: "awaiting_documents", label: "Awaiting Documents" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "settled", label: "Settled" },
  { value: "closed", label: "Closed" },
];
const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  approved: "success", settled: "success", rejected: "danger", closed: "muted",
  pending: "warning", pending_review: "warning", investigating: "info", awaiting_documents: "warning",
};

export default function WarrantyClaimsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [modal, setModal] = useState<{ type: "assign" | "documents" | "approve" | "reject"; claim: FinanceClaim } | null>(null);
  const [field1, setField1] = useState("");
  const [field2, setField2] = useState("");

  const summary = useApi(useCallback(() => financeApi.getClaimsSummary(), []));
  const claims = useApi(useCallback(() => financeApi.listClaims({
    q: search || undefined, status: status || undefined, pageSize: 200,
  }), [search, status]));

  const assignAction = useAction(useCallback((id: string, reviewerId: string) => financeApi.assignReviewer(id, reviewerId), []));
  const docsAction = useAction(useCallback((id: string, notes: string) => financeApi.requestDocuments(id, notes), []));
  const approveAction = useAction(useCallback((id: string, amt: number, notes: string) => financeApi.approveClaim(id, amt, notes), []));
  const rejectAction = useAction(useCallback((id: string, reason: string, notes: string) => financeApi.rejectClaim(id, reason, notes), []));
  const settleAction = useAction(useCallback((id: string) => financeApi.settleClaim(id), []));

  function refetchAll() { summary.refetch(); claims.refetch(); }

  function openModal(type: "assign" | "documents" | "approve" | "reject", claim: FinanceClaim) {
    setModal({ type, claim }); setField1(""); setField2("");
  }
  async function handleSettle(c: FinanceClaim) {
    const res = await settleAction.execute(c.claim_id);
    if (res) refetchAll();
  }
  async function handleModalSubmit() {
    if (!modal) return;
    const { type, claim } = modal;
    let res = null;
    if (type === "assign") res = await assignAction.execute(claim.claim_id, field1);
    if (type === "documents") res = await docsAction.execute(claim.claim_id, field1);
    if (type === "approve") res = await approveAction.execute(claim.claim_id, Number(field1), field2);
    if (type === "reject") res = await rejectAction.execute(claim.claim_id, field1, field2);
    if (res) { setModal(null); refetchAll(); }
  }
  async function handleExport() {
    const res = await financeApi.exportClaims({ status: status || undefined });
    const header = "tenant_name,job_id,claim_type,amount_requested,status,created_at\n";
    const body = res.rows.map(r => [r.tenant_name ?? "", r.job_id, r.claim_type, r.amount_requested, r.status, r.created_at ?? ""].join(",")).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "warranty_claims.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  const rows = claims.data?.items ?? [];
  const s = summary.data;

  const columns = [
    { key: "claim_id", label: "Claim ID", width: 110, render: (_: unknown, row: FinanceClaim) => (
      <span style={{ fontFamily: "monospace", fontSize: 12 }}>{row.claim_id.slice(0, 8)}</span>
    )},
    { key: "tenant_name", label: "Tenant", render: (_: unknown, row: FinanceClaim) => row.tenant_name },
    { key: "job_id", label: "Booking / Job", width: 140, render: (_: unknown, row: FinanceClaim) => row.job_id },
    { key: "claim_type", label: "Issue Type", width: 140, render: (_: unknown, row: FinanceClaim) => (
      <span style={{ textTransform: "capitalize" }}>{row.claim_type.replace(/_/g, " ")}</span>
    )},
    { key: "amount_requested", label: "Claim Amount", width: 130, render: (_: unknown, row: FinanceClaim) => `₹${row.amount_requested.toLocaleString("en-IN")}` },
    { key: "status", label: "Status", width: 160, render: (_: unknown, row: FinanceClaim) => (
      <Badge variant={STATUS_BADGE[row.status] ?? "muted"}>{row.status.replace(/_/g, " ")}</Badge>
    )},
    { key: "assigned_reviewer_id", label: "Assigned Reviewer", width: 150, render: (_: unknown, row: FinanceClaim) => row.assigned_reviewer_id ? row.assigned_reviewer_id.slice(0, 8) : "—" },
    { key: "created_at", label: "Raised On", width: 120, render: (_: unknown, row: FinanceClaim) => row.created_at ? new Date(row.created_at).toLocaleDateString("en-IN") : "—" },
    { key: "claim_id2", label: "", width: 110, render: (_: unknown, row: FinanceClaim) => (
      <ActionMenu items={[
        { label: "View Claim", onClick: () => router.push(`/admin/finance/claims/${row.claim_id}`) },
        { label: "Assign Reviewer", onClick: () => openModal("assign", row) },
        { label: "Request Documents", onClick: () => openModal("documents", row) },
        row.status !== "approved" && row.status !== "rejected" && row.status !== "settled" &&
          { label: "Approve", onClick: () => openModal("approve", row) },
        row.status !== "approved" && row.status !== "rejected" && row.status !== "settled" &&
          { label: "Reject", onClick: () => openModal("reject", row), destructive: true },
        row.status === "approved" && { label: "Settle", onClick: () => handleSettle(row) },
        { label: "View Audit Logs", onClick: () => router.push(`/admin/finance/claims/${row.claim_id}#audit`) },
      ]}/>
    )},
  ];

  return (
    <AdminLayout activeNav="finance-claims">
      <SectionHeader title="Warranty Claims" subtitle="Track claim requests, verification, settlements, and claim payout decisions."/>
      <div style={{ padding: "0 28px 32px" }}>
        {s && (
          <SummaryCardsRow cards={[
            { label: "Total Claims", value: s.total_claims },
            { label: "Pending Review", value: s.pending_review },
            { label: "Investigation Ongoing", value: s.investigation_ongoing },
            { label: "Approved Claims", value: s.approved_claims },
            { label: "Rejected Claims", value: s.rejected_claims },
            { label: "Settled Value", value: `₹${s.settled_value.toLocaleString("en-IN")}` },
          ]}/>
        )}
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <AlertOctagon size={18} color="var(--brand)"/>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Warranty Claims</span>
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
              <input placeholder="Search claim / tenant / job…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius:"var(--radius-md)",
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}/>
            </div>
            <Select label="" value={status} onChange={setStatus} options={STATUS_OPTIONS}/>
          </div>
          {(assignAction.error || docsAction.error || approveAction.error || rejectAction.error || settleAction.error) && (
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
              {assignAction.error || docsAction.error || approveAction.error || rejectAction.error || settleAction.error}
            </p>
          )}
          <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]} loading={claims.loading}
            emptyText="No claims pending."/>
        </Card>
      </div>

      <Modal open={!!modal} onClose={() => setModal(null)} title={
        modal?.type === "assign" ? "Assign Reviewer" :
        modal?.type === "documents" ? "Request Documents" :
        modal?.type === "approve" ? "Approve Claim" : "Reject Claim"
      }>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {modal?.type === "assign" && <Input label="Reviewer User ID *" value={field1} onChange={setField1}/>}
          {modal?.type === "documents" && <Input label="Notes — what documents are needed?" value={field1} onChange={setField1}/>}
          {modal?.type === "approve" && (
            <>
              <Input label="Amount Approved ₹ *" type="number" value={field1} onChange={setField1}/>
              <Input label="Admin Notes" value={field2} onChange={setField2}/>
            </>
          )}
          {modal?.type === "reject" && (
            <>
              <Input label="Rejection Reason *" value={field1} onChange={setField1}/>
              <Input label="Admin Notes" value={field2} onChange={setField2}/>
            </>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setModal(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" onClick={handleModalSubmit}
              loading={assignAction.loading || docsAction.loading || approveAction.loading || rejectAction.loading}>
              Confirm
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
