"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "invoice_number",         label: "Invoice #",      width: 160 },
  { key: "invoice_status",         label: "Status",         width: 130 },
  { key: "source",                 label: "Source",         width: 130,
    render: v => String(v ?? "").replace(/_/g, " ") },
  { key: "customer_payable_amount",label: "Amount (₹)",     width: 130,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "job_id",                 label: "Job",            width: 120,
    render: v => v ? String(v).slice(0, 8) : "—" },
  { key: "issued_at",              label: "Issued",         width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",             label: "Created",        width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "draft",              label: "Draft" },
      { value: "issued",             label: "Issued" },
      { value: "payment_pending",    label: "Payment Pending" },
      { value: "payment_collected",  label: "Payment Collected" },
      { value: "paid",               label: "Paid" },
      { value: "cancelled",          label: "Cancelled" },
      { value: "failed",             label: "Failed" },
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

export default function ProviderServiceInvoicesPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/provider/service-invoices?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <EnterpriseDataGrid
      resourceKey="provider_service_invoices"
      fetchFn={fetchFn}
      columns={COLUMNS}
      filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
      enableColumnPrefs
      title="Service Invoices"
      emptyMessage="No invoices found."
      rowActions={row => [
        { label: "View Invoice", onClick: () => { window.location.href = `/provider/service-invoices/${row.id}`; } },
      ]}
    />
  );
}
