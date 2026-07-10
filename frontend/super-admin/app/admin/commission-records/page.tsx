"use client";
import { useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { enterpriseApi } from "../../../lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const COLUMNS: GridColumn[] = [
  { key: "commission_number",  label: "Commission #",  width: 160 },
  { key: "status",             label: "Status",        width: 130 },
  { key: "tenant_id",          label: "Tenant",        visible: false },
  { key: "commission_amount",  label: "Amount",        width: 120,
    render: v => v != null ? `₹${Number(v).toLocaleString("en-IN")}` : "—" },
  { key: "commission_rate",    label: "Rate",          width: 90,
    render: v => v != null ? `${v}%` : "—" },
  { key: "deducted_at",        label: "Deducted",      width: 140,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",         label: "Created",       width: 140,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "pending",             label: "Pending" },
      { value: "calculated",          label: "Calculated" },
      { value: "deducted",            label: "Deducted" },
      { value: "reversed",            label: "Reversed" },
      { value: "insufficient_credit", label: "Insufficient Credit" },
      { value: "failed",              label: "Failed" },
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

export default function AdminCommissionRecordsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const token = typeof window !== "undefined" ? localStorage.getItem("serviceos_admin_token") ?? "" : "";
    const res   = await fetch(`${API}/v1/admin/commission-records?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json?.error?.message ?? "Request failed");
    const d = json.data ?? json;
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  const handleExport = useCallback(async (params: Record<string, unknown>) => {
    try {
      await enterpriseApi.createExport({
        resource_key: "admin_commission_records",
        filters: params,
        columns: ["commission_number", "status", "commission_amount", "commission_rate", "deducted_at", "created_at"],
      });
      alert("Export job created — check /admin/exports.");
    } catch { alert("Export failed."); }
  }, []);

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto" }}>
      <EnterpriseDataGrid
        resourceKey="admin_commission_records"
        fetchFn={fetchFn}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableExport
        enableColumnPrefs
        onExport={handleExport}
        title="Commission Records"
        emptyMessage="No commission records found."
        rowActions={row => [
          { label: "View Details", onClick: () => { window.location.href = `/admin/commission-records/${row.id}`; } },
        ]}
      />
      </div>
    </AdminLayout>
  );
}
