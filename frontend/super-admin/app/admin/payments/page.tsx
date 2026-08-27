"use client";
import { useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { enterpriseApi, apiFetchPaginatedRaw } from "../../../lib/api";
import { usePermissions } from "../../../hooks/usePermissions";

const COLUMNS: GridColumn[] = [
  { key: "payment_reference",  label: "Reference",   width: 160 },
  { key: "status",             label: "Status",      width: 140 },
  { key: "tenant_id",          label: "Tenant",      visible: false },
  { key: "amount",             label: "Amount",      width: 120,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "payment_method",     label: "Method",      width: 120 },
  { key: "confirmed_at",       label: "Confirmed",   width: 140,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",         label: "Created",     width: 140,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "pending",            label: "Pending" },
      { value: "customer_confirmed", label: "Customer Confirmed" },
      { value: "admin_verified",     label: "Admin Verified" },
      { value: "confirmed",          label: "Confirmed" },
      { value: "disputed",           label: "Disputed" },
      { value: "failed",             label: "Failed" },
    ],
  },
  {
    key: "payment_method", label: "Method", type: "select",
    options: [
      { value: "cash",          label: "Cash" },
      { value: "card",          label: "Card" },
      { value: "upi",           label: "UPI" },
      { value: "bank_transfer", label: "Bank Transfer" },
      { value: "wallet",        label: "Wallet" },
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

export default function AdminPaymentsPage() {
  const perm = usePermissions();
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const d = await apiFetchPaginatedRaw("/v1/admin/payments", params);
    if (d?.pagination) return d as unknown as GridData;
    return wrapLegacy(d, params);
  }, []);

  const handleExport = useCallback(async (params: Record<string, unknown>) => {
    try {
      await enterpriseApi.createExport({
        resource_key: "admin_payments",
        filters: params,
        columns: ["payment_reference", "status", "amount", "payment_method", "confirmed_at", "created_at"],
      });
      alert("Export job created. View progress and download it from Export Jobs (/admin/exports).");
    } catch { alert("Export failed."); }
  }, []);

  return (
    <AdminLayout>
      <div>
      <EnterpriseDataGrid
        resourceKey="admin_payments"
        fetchFn={fetchFn}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableExport={perm.has("finance:hub:export")}
        enableColumnPrefs
        onExport={handleExport}
        title="Payments"
        emptyMessage="No payment records found."
        rowActions={row => [
          { label: "View Details", onClick: () => { window.location.href = `/admin/payments/${row.id}`; } },
        ]}
      />
      </div>
    </AdminLayout>
  );
}
