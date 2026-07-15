"use client";
import { useCallback } from "react";
import EnterpriseDataGrid, { GridColumn, GridData } from "../../../components/enterprise/EnterpriseDataGrid";
import { FilterDef } from "../../../components/enterprise/EnterpriseFilterBar";
import { apiFetch } from "../../../lib/api";

// MODULE-L5-42: columns/filters realigned to the real CoachingAppointment
// shape (final_records/models.py). The old columns (appointment_type,
// scheduled_date, scheduled_time, duration_minutes) don't exist on the
// record; the real fields are student_name/target_exam/selected_date/
// selected_time_start.
const COLUMNS: GridColumn[] = [
  { key: "appointment_number", label: "Appt #",      width: 150 },
  { key: "status",             label: "Status",      width: 130 },
  { key: "student_name",       label: "Student",     width: 160,
    render: v => String(v ?? "—") },
  { key: "target_exam",        label: "Target",      width: 130,
    render: v => v ? String(v).replace(/_/g, " ") : "—" },
  { key: "selected_date",      label: "Scheduled",   width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
  { key: "selected_time_start", label: "Time",       width: 100,
    render: v => v ? String(v).slice(0, 5) : "—" },
  { key: "created_at",         label: "Booked",      width: 130,
    render: v => v ? String(v).slice(0, 10) : "—" },
];

const FILTERS: FilterDef[] = [
  {
    key: "status", label: "Status", type: "select",
    options: [
      { value: "confirmed",   label: "Confirmed" },
      { value: "in_progress", label: "In Progress" },
      { value: "completed",   label: "Completed" },
      { value: "cancelled",   label: "Cancelled" },
      { value: "no_show",     label: "No Show" },
    ],
  },
];

function wrapLegacy(d: unknown, params: Record<string, unknown>) {
  // MODULE-L5-42: the real endpoint returns {items, total, limit, offset}.
  const raw      = (d as Record<string, unknown>)?.items ?? d;
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
  // MODULE-L5-42: was GET /v1/appointments/staff?... -- a route that requires
  // a staff_id in the PATH (/v1/appointments/staff/{staff_id}) and 404s as
  // written, so the whole page showed nothing. The real tenant-wide list is
  // GET /v1/provider/my-records/appointments (final_records/provider_router),
  // returning {items, total, limit, offset}. It supports status + limit/offset
  // only (no server-side sort/date filter), so page/page_size are translated
  // to limit/offset and other grid params are dropped.
  const fetchFn = useCallback(async (params: Record<string, unknown>) => {
    const page     = Number(params.page ?? 1);
    const pageSize = Number(params.page_size ?? 25);
    const qs = new URLSearchParams();
    qs.set("limit", String(pageSize));
    qs.set("offset", String((page - 1) * pageSize));
    if (params.status != null && params.status !== "") qs.set("status", String(params.status));
    const d = await apiFetch<GridData>(`/v1/provider/my-records/appointments?${qs}`);
    return wrapLegacy(d, params);
  }, []);

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1120, margin: "0 auto" }}>
      <EnterpriseDataGrid
        resourceKey="provider_coaching_appointments"
        fetchFn={fetchFn}
        columns={COLUMNS}
        filters={FILTERS}
        defaultSort={{ sort_by: "created_at", sort_direction: "desc" }}
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
