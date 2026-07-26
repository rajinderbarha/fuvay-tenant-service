"use client";
/**
 * Service Area Requests — replaces the retired Pricing Tiers / City-Zipcode
 * Mapping admin workflow. Tenants request coverage for a city/zipcode +
 * service; admin reviews and approves/rejects here. No price is shown or
 * editable on this page — coverage approval never touches tenant pricing.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Input, Select } from "../../../components/shared/ui";
import { serviceAreaRequestAdminApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "CHANGES_REQUESTED", label: "Changes Requested" },
  { value: "PARTIALLY_APPROVED", label: "Partially Approved" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "WITHDRAWN", label: "Withdrawn" },
];

function statusVariant(status: string): "success" | "warning" | "danger" | "default" {
  if (status === "APPROVED") return "success";
  if (status === "REJECTED" || status === "WITHDRAWN") return "danger";
  if (status === "PARTIALLY_APPROVED" || status === "CHANGES_REQUESTED") return "warning";
  return "default";
}

export default function ServiceAreaRequestsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [tenantId, setTenantId] = useState("");

  const requests = useApi(useCallback(
    () => serviceAreaRequestAdminApi.list({
      status_filter: statusFilter || undefined,
      tenant_id: tenantId || undefined,
      limit: 50,
    }),
    [statusFilter, tenantId],
  ), [statusFilter, tenantId]);

  const rows = requests.data?.requests ?? [];

  return (
    <AdminLayout activeNav="verticals">
      <RequirePermission requiredPermission="platform:admin" parentLabel="Service Area Requests">
        <SectionHeader
          title="Service Area Requests"
          subtitle="Tenants request coverage for a city/zipcode + service. Review and approve or reject here — pricing is set entirely by the tenant and never appears on this page."
        />

        <Card style={{ marginBottom: 16, padding: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ minWidth: 220 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Status</label>
            <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} options={STATUS_OPTIONS} />
          </div>
          <div style={{ minWidth: 260 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Tenant ID</label>
            <Input value={tenantId} onChange={e => setTenantId(e.target.value)} placeholder="Filter by tenant UUID" />
          </div>
          <Btn variant="ghost" onClick={() => requests.refetch()}>Refresh</Btn>
        </Card>

        {requests.loading ? <Spinner /> : requests.error ? (
          <Card><p style={{ color: "var(--danger)" }}>{requests.error}</p></Card>
        ) : rows.length === 0 ? (
          <Card style={{ padding: 32, textAlign: "center", color: "var(--text-secondary)" }}>
            No service area requests match these filters.
          </Card>
        ) : (
          <Card padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "12px 16px" }}>Request ID</th>
                    <th style={{ padding: "12px 16px" }}>Tenant</th>
                    <th style={{ padding: "12px 16px" }}>Status</th>
                    <th style={{ padding: "12px 16px" }}>Version</th>
                    <th style={{ padding: "12px 16px" }}>Submitted</th>
                    <th style={{ padding: "12px 16px" }}>Reviewed</th>
                    <th style={{ padding: "12px 16px" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{r.id.slice(0, 8)}</td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 12 }}>{r.tenant_id.slice(0, 8)}</td>
                      <td style={{ padding: "10px 16px" }}><Badge variant={statusVariant(r.status)}>{r.status}</Badge></td>
                      <td style={{ padding: "10px 16px" }}>v{r.version}</td>
                      <td style={{ padding: "10px 16px" }}>{r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : "—"}</td>
                      <td style={{ padding: "10px 16px" }}>{r.reviewed_at ? new Date(r.reviewed_at).toLocaleDateString() : "—"}</td>
                      <td style={{ padding: "10px 16px", textAlign: "right" }}>
                        <Btn variant="ghost" onClick={() => { window.location.href = `/admin/service-area-requests/${r.id}`; }}>
                          Review
                        </Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}
