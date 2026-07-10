"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../lib/api";

const COLUMNS: GridColumn[] = [
  { key: "appointment_number", label: "Appt #",      width: 150 },
  { key: "status",             label: "Status",      width: 130 },
  { key: "appointment_type",   label: "Type",        width: 140,
    render: v => String(v ?? "").replace(/_/g, " ") },
  { key: "scheduled_date",     label: "Scheduled",   width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "scheduled_time",     label: "Time",        width: 100 },
  { key: "duration_minutes",   label: "Duration",    width: 100,
    render: v => v != null ? `${v} min` : "—" },
  { key: "created_at",         label: "Booked",      width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "scheduled",   label: "Scheduled" },
      { value: "confirmed",   label: "Confirmed" },
      { value: "in_progress", label: "In Progress" },
      { value: "completed",   label: "Completed" },
      { value: "cancelled",   label: "Cancelled" },
      { value: "no_show",     label: "No Show" },
    ],
  },
  {
    key: "appointment_type", label: "Type", type: "select",
    options: [
      { value: "ielts_coaching",    label: "IELTS Coaching" },
      { value: "spoken_english",    label: "Spoken English" },
      { value: "academic_coaching", label: "Academic Coaching" },
      { value: "general_coaching",  label: "General Coaching" },
    ],
  },
  { key: "scheduled", label: "Date Range", type: "date_range" },
];

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  const raw      = (d as Record<string, unknown>)?.appointments ?? d;
  const items    = Array.isArray(raw) ? raw : [];
  const page     = Number(params.page ?? 1);
  const pageSize = Number(params.page_size ?? 25);
  const total    = (d as Record<string, unknown>)?.total ?? items.length;
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

export default function AppointmentsPage() {
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
    const d = await apiFetch<GridData>(`/v1/appointments/staff?${qs}`);
    if (d?.pagination) return d;
    return wrapLegacy(d, params);
  }, []);

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1120, margin: "0 auto" }}>
      <EnterpriseDataGrid
        resourceKey="provider_coaching_appointments"
        fetchFn={fetchFn}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "scheduled_date", sort_direction: "asc" }}
        enableColumnPrefs
        title="Appointments"
        emptyMessage="No appointments found."
        rowActions={row => [
          { label: "View Details", onClick: () => { window.location.href = `/appointments/${row.id}`; } },
        ]}
      />
    </div>
  );
}
