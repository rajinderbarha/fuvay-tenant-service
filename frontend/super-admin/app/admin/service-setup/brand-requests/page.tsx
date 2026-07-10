"use client";
import React, { useState } from "react";
import { MessageSquare, Check, X, GitMerge } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { catalogApi, type BrandRequest34D } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const STATUS_OPTS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "merged", label: "Merged" },
];

function reqStatusBadge(s: string) {
  const map: Record<string, string> = { pending: "warning", approved: "success", rejected: "error", merged: "info" };
  return <Badge variant={(map[s] as any) ?? "default"}>{s}</Badge>;
}

export default function BrandRequestsPage() {
  const [filterStatus, setFilterStatus] = useState("pending");
  const [selectedReq, setSelectedReq] = useState<BrandRequest34D | null>(null);
  const [adminNote, setAdminNote] = useState("");
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [action, setAction] = useState<"approve" | "reject" | "merge" | null>(null);

  const { data, loading, refetch } = useApi(
    () => catalogApi.listBrandRequests(filterStatus || undefined),
    [filterStatus],
  );

  const approveAction = useAction(async (reqId: string) => {
    await catalogApi.approveBrandRequest(reqId, adminNote || undefined);
    setSelectedReq(null); setAction(null); setAdminNote("");
    refetch();
  });

  const rejectAction = useAction(async (reqId: string) => {
    await catalogApi.rejectBrandRequest(reqId, adminNote || undefined);
    setSelectedReq(null); setAction(null); setAdminNote("");
    refetch();
  });

  const mergeAction = useAction(async (reqId: string) => {
    await catalogApi.mergeBrandRequest(reqId, mergeTargetId, adminNote || undefined);
    setSelectedReq(null); setAction(null); setAdminNote(""); setMergeTargetId("");
    refetch();
  });

  const requests = data?.requests ?? [];
  const pending = requests.filter(r => r.status === "pending").length;

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1100, margin: "0 auto" }}>
        <SectionHeader
          title="Brand Requests"
          subtitle={`${pending} pending · Providers submit missing brand requests for admin review`}
          icon={<MessageSquare size={20} />}
          actions={
            <Btn size="sm" variant="ghost" onClick={() => window.location.href = "/admin/service-setup/brands"}>
              ← All Brands
            </Btn>
          }
        />

        {/* Filter */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <Select value={filterStatus} onChange={v => setFilterStatus(v)} options={STATUS_OPTS} />
          <Btn size="sm" variant="ghost" onClick={refetch}>Refresh</Btn>
        </div>

        <Card>
          {loading && <div style={{ padding: 24, textAlign: "center", opacity: 0.5 }}>Loading…</div>}
          {!loading && requests.length === 0 && (
            <div style={{ padding: 40, textAlign: "center", opacity: 0.5 }}>No brand requests.</div>
          )}
          {!loading && requests.length > 0 && (
            <DataTable
              columns={[
                { key: "requested_brand_name", label: "Brand Name", render: (v: unknown, row: Record<string,unknown>) => {
                  const r = row as unknown as BrandRequest34D;
                  return (
                    <div>
                      <div style={{ fontWeight: 500 }}>{v as string}</div>
                      {r.normalized_name && <div style={{ fontSize: 11, opacity: 0.4, fontFamily: "monospace" }}>{r.normalized_name}</div>}
                    </div>
                  );
                }},
                { key: "status", label: "Status", render: (v: unknown) => reqStatusBadge(v as string) },
                { key: "reason", label: "Reason", render: (v: unknown) => (
                  <span style={{ fontSize: 12, opacity: 0.7 }}>{(v as string) || "—"}</span>
                )},
                { key: "tenant_id", label: "Tenant", render: (v: unknown) => {
                  const s = v as string;
                  return <span style={{ fontSize: 11, fontFamily: "monospace" }}>{s ? s.slice(0, 8) + "…" : "—"}</span>;
                }},
                { key: "created_at", label: "Submitted", render: (v: unknown) => (
                  <span style={{ fontSize: 12 }}>{v ? new Date(v as string).toLocaleDateString() : "—"}</span>
                )},
                { key: "actions", label: "", render: (_: unknown, row: Record<string,unknown>) => {
                  const r = row as unknown as BrandRequest34D;
                  return r.status === "pending" ? (
                    <div style={{ display: "flex", gap: 6 }}>
                      <Btn size="sm" onClick={() => { setSelectedReq(r); setAction("approve"); setAdminNote(""); }}>
                        <Check size={12} style={{ marginRight: 3 }} /> Approve
                      </Btn>
                      <Btn size="sm" variant="ghost" onClick={() => { setSelectedReq(r); setAction("merge"); setAdminNote(""); setMergeTargetId(""); }}>
                        <GitMerge size={12} style={{ marginRight: 3 }} /> Merge
                      </Btn>
                      <Btn size="sm" variant="ghost" onClick={() => { setSelectedReq(r); setAction("reject"); setAdminNote(""); }}>
                        <X size={12} style={{ marginRight: 3 }} /> Reject
                      </Btn>
                    </div>
                  ) : <span style={{ fontSize: 12, opacity: 0.5 }}>{r.admin_note || "reviewed"}</span>;
                }},
              ]}
              rows={requests as unknown as Record<string,unknown>[]}
            />
          )}
        </Card>

        {/* Review Modal */}
        <Modal
          open={!!selectedReq && !!action}
          onClose={() => { setSelectedReq(null); setAction(null); }}
          title={action === "approve" ? "Approve Brand Request" : action === "reject" ? "Reject Brand Request" : "Merge Brand Request"}
        >
          {selectedReq && (
            <>
              <div style={{ marginBottom: 12, padding: 10, background: "var(--surface-raised, #f8fafc)", borderRadius: 6, fontSize: 13 }}>
                Brand requested: <strong>{selectedReq.requested_brand_name}</strong>
                {selectedReq.reason && <div style={{ opacity: 0.6, marginTop: 4 }}>Reason: {selectedReq.reason}</div>}
              </div>
              {action === "merge" && (
                <Input
                  label="Existing Brand UUID to merge into *"
                  value={mergeTargetId}
                  onChange={v => setMergeTargetId(v)}
                  placeholder="canonical-brand-uuid"
                />
              )}
              <Input label="Admin Note" value={adminNote} onChange={v => setAdminNote(v)}
                placeholder={action === "reject" ? "Reason for rejection…" : "Optional note…"} />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
                <Btn variant="ghost" onClick={() => { setSelectedReq(null); setAction(null); }}>Cancel</Btn>
                {action === "approve" && (
                  <Btn onClick={() => approveAction.execute(selectedReq.request_id)}
                    disabled={approveAction.loading}>
                    {approveAction.loading ? "Approving…" : "Approve & Create Brand"}
                  </Btn>
                )}
                {action === "reject" && (
                  <Btn variant="ghost" onClick={() => rejectAction.execute(selectedReq.request_id)}
                    disabled={rejectAction.loading}>
                    {rejectAction.loading ? "Rejecting…" : "Reject"}
                  </Btn>
                )}
                {action === "merge" && (
                  <Btn onClick={() => mergeAction.execute(selectedReq.request_id)}
                    disabled={!mergeTargetId.trim() || mergeAction.loading}>
                    {mergeAction.loading ? "Merging…" : "Merge into Existing"}
                  </Btn>
                )}
              </div>
            </>
          )}
        </Modal>
      </div>
    </AdminLayout>
  );
}
