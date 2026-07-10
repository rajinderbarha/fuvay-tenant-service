"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "id",               label: "ID",            width: 120,
    render: v => String(v ?? "").slice(0, 8) },
  { key: "status",           label: "Status",        width: 140 },
  { key: "refund_type",      label: "Type",          width: 120 },
  { key: "requested_amount", label: "Requested (₹)", width: 130,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "approved_amount",  label: "Approved (₹)",  width: 130,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "refund_method",    label: "Method",        width: 120 },
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

export default function ProviderRefundRequestsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/provider/refund-requests?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <EnterpriseDataGrid
      resourceKey="provider_refund_requests"
      fetchFn={fetchFn}
      columns={COLUMNS}
      filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
      enableColumnPrefs
      title="Refund Requests"
      emptyMessage="No refund requests found."
    />
  );
}
