"use client";
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader,
} from "../../../components/shared/ui";
import { catalogApi, type BrandRequest34D } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RefreshCw } from "lucide-react";

const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "danger"> = {
  pending: "warning", approved: "success", rejected: "danger", merged: "muted",
};

export default function BrandRequestsPage() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [actionModal, setActionModal] = useState<{ type: "approve" | "reject" | "merge"; req: BrandRequest34D } | null>(null);
  const [adminNote, setAdminNote]     = useState("");
  const [existingBrandId, setExistingBrandId] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const requests = useApi(useCallback(
    () => catalogApi.listBrandRequests({ status: statusFilter || undefined }),
    [statusFilter],
  ));

  const brands = useApi(useCallback(
    () => catalogApi.listBrands({ status: "active" }),
    [],
  ));

  const approveAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.approveBrandRequest(id, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); notify("Request approved.");
  });

  const rejectAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.rejectBrandRequest(id, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); notify("Request rejected.");
  });

  const mergeAction = useAction(async ({ id }: { id: string }) => {
    await catalogApi.mergeBrandRequest(id, existingBrandId, adminNote || undefined);
    requests.refetch(); setActionModal(null); setAdminNote(""); setExistingBrandId(""); notify("Brand request merged with existing brand.");
  });

  function openAction(type: "approve" | "reject" | "merge", req: BrandRequest34D) {
    setActionModal({ type, req }); setAdminNote(""); setExistingBrandId("");
  }

  const rows = requests.data?.requests ?? [];
  const activeBrands = brands.data?.brands ?? [];
  const modal = actionModal;
  const modalTitle = modal?.type === "approve" ? "Approve Request" : modal?.type === "reject" ? "Reject Request" : "Merge with Existing Brand";
  const currentAction = modal?.type === "approve" ? approveAction : modal?.type === "reject" ? rejectAction : mergeAction;

  const columns = [
    {
      key: "requested_brand_name", label: "Brand Name",
      render: (_: unknown, row: BrandRequest34D) => (
        <div>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.requested_brand_name}</span>
          {row.normalized_name && (
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-secondary)" }}>normalized: {row.normalized_name}</p>
          )}
        </div>
      ),
    },
    {
      key: "reason", label: "Reason",
      render: (_: unknown, row: BrandRequest34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{row.reason || "—"}</span>
      ),
    },
    {
      key: "status", label: "Status", width: 110,
      render: (_: unknown, row: BrandRequest34D) => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "muted"}>{row.status}</Badge>
      ),
    },
    {
      key: "created_at", label: "Requested", width: 120,
      render: (_: unknown, row: BrandRequest34D) => (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
        </span>
      ),
    },
    {
      key: "request_id", label: "", width: 260,
      render: (_: unknown, row: BrandRequest34D) => row.status === "pending" ? (
        <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
          <Btn variant="primary" size="xs" onClick={() => openAction("approve", row)}>Approve</Btn>
          <Btn variant="secondary" size="xs" onClick={() => openAction("merge", row)}>Merge Existing</Btn>
          <Btn variant="danger" size="xs" onClick={() => openAction("reject", row)}>Reject</Btn>
        </div>
      ) : (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {row.reviewed_at ? `Reviewed ${new Date(row.reviewed_at).toLocaleDateString()}` : "—"}
        </span>
      ),
    },
  ];

  return (
    <AdminLayout activeNav="brand-requests">
      <SectionHeader
        title="Brand Requests"
        subtitle="Providers and tenants can request new brands. Review, approve, reject, or merge with existing brands."
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" size="sm" onClick={() => requests.refetch()}>
              <RefreshCw size={14} style={{ marginRight: 4 }} /> Refresh
            </Btn>
          </div>
        }
      />

      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 9999, padding: "10px 18px",
          borderRadius: 10, background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13,
        }}>{toast.msg}</div>
      )}

      {/* Status filter tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {[
          { value: "pending", label: "Pending" },
          { value: "approved", label: "Approved" },
          { value: "merged", label: "Merged" },
          { value: "rejected", label: "Rejected" },
          { value: "", label: "All" },
        ].map(opt => (
          <button key={opt.value} onClick={() => setStatusFilter(opt.value)} style={{
            padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 500,
            border: `1px solid ${statusFilter === opt.value ? "var(--brand, #1a56db)" : "var(--border)"}`,
            background: statusFilter === opt.value ? "var(--brand-muted, rgba(26,86,219,.08))" : "var(--surface)",
            color: statusFilter === opt.value ? "var(--brand, #1a56db)" : "var(--text-secondary)",
            cursor: "pointer",
          }}>{opt.label}</button>
        ))}
      </div>

      <DataTable
        columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={requests.loading}
        emptyText="No brand requests found for this status."
      />

      {/* Action modal */}
      <Modal open={!!modal} onClose={() => setActionModal(null)} title={modalTitle}>
        {modal && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Brand: <strong style={{ color: "var(--text-primary)" }}>{modal.req.requested_brand_name}</strong>
            </p>

            {modal.type === "merge" && (
              <Select label="Merge into existing brand *" value={existingBrandId}
                onChange={setExistingBrandId} placeholder="Select existing brand…"
                options={activeBrands.map(b => ({ value: b.brand_id, label: b.display_name || b.name }))} />
            )}

            <Input label="Admin Note" placeholder="Reason / message to requester (optional)"
              value={adminNote} onChange={setAdminNote} />

            {currentAction.error && (
              <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>{currentAction.error}</p>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <Btn variant="secondary" size="sm" onClick={() => setActionModal(null)}>Cancel</Btn>
              <Btn
                variant={modal.type === "reject" ? "danger" : "primary"}
                size="sm"
                loading={currentAction.loading}
                disabled={modal.type === "merge" && !existingBrandId}
                onClick={() => currentAction.execute({ id: modal.req.request_id })}
              >
                {modal.type === "approve" ? "Approve" : modal.type === "reject" ? "Reject" : "Merge"}
              </Btn>
            </div>
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
