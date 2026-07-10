"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "job_number",        label: "Job #",        width: 140 },
  { key: "status",            label: "Status",       width: 120 },
  { key: "assignment_status", label: "Assignment",   width: 140 },
  { key: "category_id",       label: "Category",     visible: false },
  { key: "scheduled_date",    label: "Scheduled",    width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",        label: "Created",      width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "pending",     label: "Pending" },
      { value: "assigned",    label: "Assigned" },
      { value: "in_progress", label: "In Progress" },
      { value: "completed",   label: "Completed" },
      { value: "cancelled",   label: "Cancelled" },
    ],
  },
  {
    key: "assignment_status", label: "Assignment", type: "select",
    options: [
      { value: "unassigned", label: "Unassigned" },
      { value: "assigned",   label: "Assigned" },
      { value: "accepted",   label: "Accepted" },
    ],
  },
  { key: "created", label: "Date Range", type: "date_range" },
];

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  const raw      = (d as Record<string, unknown>)?.jobs ?? d;
  const items    = Array.isArray(raw) ? raw : [];
  const page     = Number(params.page ?? 1);
  const pageSize = Number(params.page_size ?? 25);
  const total    = (d as Record<string, unknown>)?.count ?? (d as Record<string, unknown>)?.total ?? items.length;
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

export default function ProviderServiceJobsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/provider/service-jobs?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <EnterpriseDataGrid
      resourceKey="provider_service_jobs"
      fetchFn={fetchFn}
      columns={COLUMNS}
      filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
      enableColumnPrefs
      title="Service Jobs"
      emptyMessage="No service jobs found."
      rowActions={row => [
        { label: "View Job",     onClick: () => { window.location.href = `/service-jobs/${row.id}`; } },
        { label: "Assign Staff", onClick: () => { window.location.href = `/service-jobs/${row.id}?tab=assignment`; } },
      ]}
    />
  );
}
