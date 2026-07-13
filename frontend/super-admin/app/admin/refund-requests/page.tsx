"use client";
import { useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { enterpriseApi, apiFetchPaginatedRaw } from "../../../lib/api";
import { usePermissions } from "../../../hooks/usePermissions";

const COLUMNS: GridColumn[] = [
  { key: "id",               label: "ID",            width: 120,
    render: v => String(v ?? "").slice(0, 8) },
  { key: "status",           label: "Status",        width: 140 },
  { key: "refund_type",      label: "Type",          width: 120 },
  { key: "requested_amount", label: "Requested (₹)", width: 130,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "approved_amount",  label: "Approved (₹)",  width: 130,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "approved_at",      label: "Approved",      width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",       label: "Created",       width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "pending",   label: "Pending" },
      { value: "approved",  label: "Approved" },
      { value: "rejected",  label: "Rejected" },
      { value: "recorded",  label: "Recorded" },
      { value: "verified",  label: "Verified" },
    ],
  },
  {
    key: "refund_type", label: "Type", type: "select",
    options: [
      { value: "full",     label: "Full" },
      { value: "partial",  label: "Partial" },
      { value: "goodwill", label: "Goodwill" },
    ],
  },
  { key: "created", label: "Date Range", type: "date_range" },
];

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  const items    = Array.isArray(d) ? d : ((d as Record<string, unknown>)?.items ?? [d]);
  const page     = Number(params.page ?? 1);
  const pageSize = Number(params.page_size ?? 25);
  const total    = (d as Record<string, unknown>)?.total ?? (items as unknown[]).length;
  return {
    items: items as Record<string, unknown>[],
    pagination: {
      page, page_size: pageSize, total_items: Number(total),
      total_pages: Math.ceil(Number(total) / pageSize) || 1,
      has_next: page * pageSize < Number(total), has_previous: page > 1,
    },
    sort:            { sort_by: String(params.sort_by), sort_direction: String(params.sort_direction) },
    filters_applied: params as Record<string, unknown>,
    available_columns: [],
  };
}

export default function AdminRefundRequestsPage() {
  const perm = usePermissions();
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const d = await apiFetchPaginatedRaw("/v1/admin/refund-requests", params);
    if (d?.pagination) return d as unknown as GridData;
    return wrapLegacy(d, params);
  }, []);

  const handleExport = useCallback(async (params: Record<string, unknown>) => {
    try {
      await enterpriseApi.createExport({
        resource_key: "admin_refund_requests",
        filters: params,
        columns: ["status", "refund_type", "requested_amount", "approved_amount", "approved_at", "created_at"],
      });
      alert("Export job created. View progress and download it from Export Jobs (/admin/exports).");
    } catch { alert("Export failed."); }
  }, []);

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto" }}>
      <EnterpriseDataGrid
        resourceKey="admin_refund_requests"
        fetchFn={fetchFn}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableExport={perm.has("operations:export")}
        enableColumnPrefs
        onExport={handleExport}
        title="Refund Requests"
        emptyMessage="No refund requests found."
        rowActions={row => [
          { label: "View Details", onClick: () => { window.location.href = `/admin/refund-requests/${row.id}`; } },
        ]}
      />
      </div>
    </AdminLayout>
  );
}
