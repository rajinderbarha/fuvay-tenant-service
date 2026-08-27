"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Active Coverage — approved operational service-area coverage. Admin can
 * suspend/reactivate/revoke; cannot directly edit a tenant's requested
 * city/zipcode (material changes require a new request).
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Select } from "../../../components/shared/ui";
import { serviceAreaRequestAdminApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "ACTIVE", label: "Active" },
  { value: "SUSPENDED", label: "Suspended" },
  { value: "EXPIRED", label: "Expired" },
  { value: "REVOKED", label: "Revoked" },
];

function statusTone(status: string): "success" | "warning" | "danger" | "default" {
  if (status === "ACTIVE") return "success";
  if (status === "SUSPENDED") return "warning";
  if (status === "REVOKED" || status === "EXPIRED") return "danger";
  return "default";
}

export default function ActiveCoveragePage() {
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [busyId, setBusyId] = useState<string | null>(null);

  const coverage = useApi(useCallback(
    () => serviceAreaRequestAdminApi.listCoverage({ status_filter: statusFilter || undefined, limit: 50 }),
    [statusFilter],
  ), [statusFilter]);

  const rows = coverage.data?.coverage ?? [];

  const suspend = async (id: string) => {
    const reason = window.prompt("Reason for suspending this coverage:");
    if (!reason) return;
    setBusyId(id);
    try { await serviceAreaRequestAdminApi.suspendCoverage(id, reason); coverage.refetch(); }
    finally { setBusyId(null); }
  };
  const reactivate = async (id: string) => {
    setBusyId(id);
    try { await serviceAreaRequestAdminApi.reactivateCoverage(id); coverage.refetch(); }
    finally { setBusyId(null); }
  };
  const revoke = async (id: string) => {
    const reason = window.prompt("Reason for revoking this coverage (cannot be undone without a new request):");
    if (!reason) return;
    setBusyId(id);
    try { await serviceAreaRequestAdminApi.revokeCoverage(id, reason); coverage.refetch(); }
    finally { setBusyId(null); }
  };

  return (
    <AdminLayout activeNav="verticals">
      <RequirePermission requiredPermission="platform:admin" parentLabel="Active Coverage">
        <SectionHeader
          title="Active Coverage"
          subtitle="Approved tenant service-area coverage, materialized from approved requests. No price is shown or editable here."
        />

        <Card style={{ marginBottom: 16, padding: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ minWidth: 220 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Status</label>
            <Select value={statusFilter} onChange={v => setStatusFilter(v)} options={STATUS_OPTIONS} />
          </div>
          <Btn variant="ghost" onClick={() => coverage.refetch()}>Refresh</Btn>
        </Card>

        {coverage.loading ? <Spinner /> : coverage.error ? (
          <Card><p style={{ color: "var(--danger)" }}>{coverage.error}</p></Card>
        ) : rows.length === 0 ? (
          <Card style={{ padding: 32, textAlign: "center", color: "var(--text-secondary)" }}>
            No coverage rows match these filters.
          </Card>
        ) : (
          <Card padding={0}>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "12px 16px" }}>Tenant</th>
                    <th style={{ padding: "12px 16px" }}>City</th>
                    <th style={{ padding: "12px 16px" }}>Zipcode</th>
                    <th style={{ padding: "12px 16px" }}>Status</th>
                    <th style={{ padding: "12px 16px" }}>Approved</th>
                    <th style={{ padding: "12px 16px" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(c => (
                    <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{c.tenant_id.slice(0, 8)}</td>
                      <td style={{ padding: "10px 16px" }}>{c.city}</td>
                      <td style={{ padding: "10px 16px" }}>{c.zipcode || "—"}</td>
                      <td style={{ padding: "10px 16px" }}><Badge tone={statusTone(c.status)}>{c.status}</Badge></td>
                      <td style={{ padding: "10px 16px" }}>{c.approved_at ? new Date(c.approved_at).toLocaleDateString() : "—"}</td>
                      <td style={{ padding: "10px 16px", display: "flex", gap: 6 }}>
                        {c.status === "ACTIVE" && (
                          <Btn variant="ghost" onClick={() => suspend(c.id)} disabled={busyId === c.id}>Suspend</Btn>
                        )}
                        {c.status === "SUSPENDED" && (
                          <Btn variant="ghost" onClick={() => reactivate(c.id)} disabled={busyId === c.id}>Reactivate</Btn>
                        )}
                        {c.status !== "REVOKED" && (
                          <Btn variant="danger" onClick={() => revoke(c.id)} disabled={busyId === c.id}>Revoke</Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          </Card>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}
