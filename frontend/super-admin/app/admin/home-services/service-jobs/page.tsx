"use client";
/**
 * Admin Service Jobs — migrated to EnterpriseDataGrid (Sprint 26).
 * Wraps existing endpoint; adds search/sort/pagination/export/column mgmt.
 */
import { useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { enterpriseApi, apiFetchPaginatedRaw } from "../../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "job_number",        label: "Job #",       width: 140 },
  { key: "status",            label: "Status",      width: 120 },
  { key: "assignment_status", label: "Assignment",  width: 140 },
  { key: "tenant_id",         label: "Tenant",      visible: false },
  { key: "created_at",        label: "Created",     width: 140,
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

export default function AdminServiceJobsPage() {
  const fetchJobs = useCallback(async (params: Record<string, unknown>) => {
    const d = await apiFetchPaginatedRaw("/v1/admin/final-records/jobs", params);
    if (d.pagination) return d as unknown as GridData;
    // wrap legacy shape
    const page     = Number(params.page ?? 1);
    const pageSize = Number(params.page_size ?? 25);
    const total    = Number(d.total ?? 0);
    return {
      items:            (d.items ?? []) as Record<string, unknown>[],
      pagination:       { page, page_size: pageSize, total_items: total,
                          total_pages: Math.ceil(total / pageSize) || 1,
                          has_next: page * pageSize < total, has_previous: page > 1 },
      sort:             { sort_by: String(params.sort_by), sort_direction: String(params.sort_direction) },
      filters_applied:  params as Record<string, unknown>,
      available_columns: [],
    } as GridData;
  }, []);

  const handleExport = useCallback(async (params: Record<string, unknown>) => {
    try {
      await enterpriseApi.createExport({
        resource_key: "admin_service_jobs",
        filters:      params,
        columns:      ["job_number", "status", "assignment_status", "created_at"],
      });
      alert("Export job created — check /admin/exports.");
    } catch {
      alert("Export failed. Check permissions.");
    }
  }, []);

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto" }}>
      <EnterpriseDataGrid
        resourceKey="admin_service_jobs"
        fetchFn={fetchJobs}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableExport
        enableColumnPrefs
        enableSavedViews
        onExport={handleExport}
        title="Service Jobs"
        emptyMessage="No service jobs found."
        rowActions={row => [
          { label: "View Details", onClick: () => window.location.href = `/admin/home-services/service-jobs/${row.id}` },
        ]}
      />
      </div>
    </AdminLayout>
  );
}
