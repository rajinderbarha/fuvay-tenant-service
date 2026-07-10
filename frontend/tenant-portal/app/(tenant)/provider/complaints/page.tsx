"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "complaint_number", label: "Complaint #",  width: 160 },
  { key: "status",           label: "Status",       width: 180 },
  { key: "priority",         label: "Priority",     width: 100 },
  { key: "complaint_type",   label: "Type",         width: 140,
    render: v => String(v ?? "").replace(/_/g, " ") },
  { key: "title",            label: "Title",        width: 240 },
  { key: "resolved_at",      label: "Resolved",     width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",       label: "Created",      width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "open",                          label: "Open" },
      { value: "awaiting_provider_response",    label: "Awaiting My Response" },
      { value: "resolution_proposed",           label: "Resolution Proposed" },
      { value: "resolved",                      label: "Resolved" },
      { value: "closed",                        label: "Closed" },
      { value: "rejected",                      label: "Rejected" },
    ],
  },
  {
    key: "priority", label: "Priority", type: "select",
    options: [
      { value: "low",      label: "Low" },
      { value: "medium",   label: "Medium" },
      { value: "high",     label: "High" },
      { value: "critical", label: "Critical" },
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

export default function ProviderComplaintsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/provider/complaints?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <EnterpriseDataGrid
      resourceKey="provider_complaints"
      fetchFn={fetchFn}
      columns={COLUMNS}
      filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
      enableColumnPrefs
      title="Customer Complaints"
      emptyMessage="No complaints found."
      rowActions={row => [
        { label: "View & Respond", onClick: () => { window.location.href = `/provider/complaints/${row.id}`; } },
      ]}
    />
  );
}
