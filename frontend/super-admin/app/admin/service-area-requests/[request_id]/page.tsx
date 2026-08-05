"use client";
/**
 * Service Area Request detail — item-level approve/reject/request-changes.
 * No price field appears here; only coverage location + decision.
 */
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Textarea } from "../../../../components/shared/ui";
import { serviceAreaRequestAdminApi, ServiceAreaRequestItem } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";

function itemTone(status: string): "success" | "warning" | "danger" | "default" {
  if (status === "APPROVED") return "success";
  if (status === "REJECTED") return "danger";
  if (status === "CHANGES_REQUESTED") return "warning";
  return "default";
}

export default function ServiceAreaRequestDetailPage() {
  const params = useParams();
  const requestId = String(params.request_id);

  const req = useApi(useCallback(() => serviceAreaRequestAdminApi.get(requestId), [requestId]), [requestId]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const startReview = useAction(async () => {
    await serviceAreaRequestAdminApi.startReview(requestId);
    req.refetch();
  });

  const decideOne = async (itemId: string, decision: string) => {
    const reason = reasons[itemId];
    if ((decision === "REJECTED" || decision === "CHANGES_REQUESTED") && !reason) {
      alert("A reason is required to reject an item or request changes.");
      return;
    }
    setBusy(true);
    try {
      await serviceAreaRequestAdminApi.decide(requestId, [{ item_id: itemId, decision, reason }]);
      req.refetch();
    } finally {
      setBusy(false);
    }
  };

  const approveAll = async () => {
    const items = req.data?.items ?? [];
    const pending = items.filter(i => i.decision_status === "PENDING");
    if (pending.length === 0) return;
    setBusy(true);
    try {
      await serviceAreaRequestAdminApi.decide(requestId, pending.map(i => ({ item_id: i.id, decision: "APPROVED" })));
      req.refetch();
    } finally {
      setBusy(false);
    }
  };

  if (req.loading) return <AdminLayout activeNav="verticals"><Spinner /></AdminLayout>;
  if (req.error || !req.data) {
    return <AdminLayout activeNav="verticals"><Card><p style={{ color: "var(--danger)" }}>{req.error || "Request not found."}</p></Card></AdminLayout>;
  }

  const data = req.data;
  const items: ServiceAreaRequestItem[] = data.items ?? [];
  const canReview = data.status === "SUBMITTED" || data.status === "UNDER_REVIEW";

  return (
    <AdminLayout activeNav="verticals">
      <RequirePermission requiredPermission="platform:admin" parentLabel="Service Area Requests">
        <SectionHeader
          title={`Service Area Request — ${data.id.slice(0, 8)}`}
          subtitle={`Tenant ${data.tenant_id.slice(0, 8)} · Status: ${data.status} · v${data.version}`}
        />

        <Card style={{ marginBottom: 16, padding: 16, display: "flex", gap: 10, alignItems: "center" }}>
          <Badge tone={data.status === "APPROVED" ? "success" : "default"}>{data.status}</Badge>
          {data.status === "SUBMITTED" && (
            <Btn onClick={startReview.execute} disabled={startReview.loading}>Start Review</Btn>
          )}
          {canReview && (
            <Btn onClick={approveAll} disabled={busy}>Approve All Pending</Btn>
          )}
        </Card>

        <Card padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "12px 16px" }}>City</th>
                  <th style={{ padding: "12px 16px" }}>Zipcode</th>
                  <th style={{ padding: "12px 16px" }}>Job Type Scope</th>
                  <th style={{ padding: "12px 16px" }}>Decision</th>
                  <th style={{ padding: "12px 16px" }}>Reason</th>
                  <th style={{ padding: "12px 16px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px" }}>{item.city}</td>
                    <td style={{ padding: "10px 16px" }}>{item.zipcode || "—"}</td>
                    <td style={{ padding: "10px 16px" }}>{item.applies_to_all_job_types ? "All job types" : "Selected job type"}</td>
                    <td style={{ padding: "10px 16px" }}><Badge tone={itemTone(item.decision_status)}>{item.decision_status}</Badge></td>
                    <td style={{ padding: "10px 16px", maxWidth: 220 }}>
                      {item.decision_status === "PENDING" && canReview ? (
                        <Textarea
                          value={reasons[item.id] ?? ""}
                          onChange={v => setReasons(r => ({ ...r, [item.id]: v }))}
                          placeholder="Reason (required to reject / request changes)"
                          rows={2}
                        />
                      ) : (item.decision_reason || "—")}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      {item.decision_status === "PENDING" && canReview ? (
                        <div style={{ display: "flex", gap: 6 }}>
                          <Btn variant="ghost" onClick={() => decideOne(item.id, "APPROVED")} disabled={busy}>Approve</Btn>
                          <Btn variant="ghost" onClick={() => decideOne(item.id, "CHANGES_REQUESTED")} disabled={busy}>Changes</Btn>
                          <Btn variant="danger" onClick={() => decideOne(item.id, "REJECTED")} disabled={busy}>Reject</Btn>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </RequirePermission>
    </AdminLayout>
  );
}
