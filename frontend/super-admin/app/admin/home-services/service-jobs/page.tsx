"use client";
/**
 * Admin Service Jobs — migrated to EnterpriseDataGrid (Sprint 26).
 * Wraps existing endpoint; adds search/sort/pagination/export/column mgmt.
 */
import { useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { enterpriseApi, apiFetchPaginatedRaw, finalRecordsAdminApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import { usePermissions } from "../../../../hooks/usePermissions";

const SLA_LABEL: Record<string, string> = {
  ON_TRACK: "On Track", AT_RISK: "At Risk", BREACHED: "Breached", NOT_APPLICABLE: "—",
};
const SLA_COLOR: Record<string, string> = {
  ON_TRACK: "var(--success-text, var(--success))", AT_RISK: "var(--warning-text, var(--warning))",
  BREACHED: "var(--danger-text, var(--danger))", NOT_APPLICABLE: "var(--text-tertiary)",
};

const COLUMNS: GridColumn[] = [
  { key: "job_number",        label: "Job #",       width: 140 },
  { key: "status",            label: "Status",      width: 120 },
  { key: "assignment_status", label: "Assignment",  width: 140 },
  { key: "sla",                label: "SLA",         width: 110,
    render: (v: unknown) => {
      const sla = v as { sla_status: string } | null;
      const status = sla?.sla_status ?? "NOT_APPLICABLE";
      return <span style={{ color: SLA_COLOR[status], fontWeight: 600, fontSize: 12 }}>{SLA_LABEL[status] ?? "—"}</span>;
    } },
  { key: "assigned_staff_id", label: "Technician",  width: 140,
    render: v => v ? String(v).slice(0, 8) : "Unassigned" },
  { key: "city",               label: "City",        width: 120 },
  { key: "zipcode",            label: "Zipcode",     width: 100 },
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

function SummaryCards() {
  const summary = useApi(useCallback(() => finalRecordsAdminApi.getJobsSummary(), []));
  const d = summary.data;
  const cards = [
    { label: "Total", value: d?.total },
    { label: "Unassigned", value: d?.unassigned },
    { label: "In Progress", value: d?.in_progress },
    { label: "Completed", value: d?.completed },
    { label: "At Risk", value: d?.at_risk, color: "var(--warning-text, var(--warning))" },
    { label: "Breached", value: d?.breached, color: "var(--danger-text, var(--danger))" },
    { label: "Completion Exceptions", value: d?.completion_exceptions },
  ];
  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
      {cards.map(c => (
        <div key={c.label} style={{ padding: "10px 16px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
          background: "var(--surface)", minWidth: 110 }}>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>{c.label}</p>
          <p style={{ fontSize: 20, fontWeight: 700, margin: 0, color: c.color ?? "var(--text-primary)" }}>
            {summary.loading ? "…" : c.value ?? 0}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function AdminServiceJobsPage() {
  const perm = usePermissions();
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
      alert("Export job created. View progress and download it from Export Jobs (/admin/exports).");
    } catch {
      alert("Export failed. Check permissions.");
    }
  }, []);

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto" }}>
      <SummaryCards />
      <EnterpriseDataGrid
        resourceKey="admin_service_jobs"
        fetchFn={fetchJobs}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
        enableExport={perm.has("field_ops:jobs:export")}
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
