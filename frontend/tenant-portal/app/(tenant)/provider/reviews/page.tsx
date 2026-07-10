"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "review_number",  label: "Review #",   width: 150 },
  { key: "status",         label: "Status",     width: 120 },
  { key: "overall_rating", label: "Rating",     width: 90,
    render: v => v != null ? `${v} ★` : "—" },
  { key: "record_type",    label: "Type",       width: 130,
    render: v => String(v ?? "").replace(/_/g, " ") },
  { key: "review_title",   label: "Title",      width: 220 },
  { key: "visibility",     label: "Visibility", width: 110 },
  { key: "submitted_at",   label: "Submitted",  width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "created_at",     label: "Created",    width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "approved",  label: "Approved" },
      { value: "pending",   label: "Pending" },
      { value: "hidden",    label: "Hidden" },
      { value: "flagged",   label: "Flagged" },
    ],
  },
  {
    key: "record_type", label: "Type", type: "select",
    options: [
      { value: "service_job",          label: "Service Job" },
      { value: "coaching_appointment", label: "Coaching" },
      { value: "real_estate_lead",     label: "Real Estate" },
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

export default function ProviderReviewsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/provider/reviews?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <EnterpriseDataGrid
      resourceKey="provider_reviews"
      fetchFn={fetchFn}
      columns={COLUMNS}
      filters={FILTERS}
      defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
      enableColumnPrefs
      title="Customer Reviews"
      emptyMessage="No reviews yet."
      rowActions={row => [
        { label: "Reply",    onClick: () => { window.location.href = `/provider/reviews/${row.id}?action=reply`; } },
        { label: "Flag",     onClick: () => { window.location.href = `/provider/reviews/${row.id}?action=flag`; } },
      ]}
    />
  );
}
