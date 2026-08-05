"use client";
/** Weekly/day availability grid -- one row per technician (aligned with
 * TeamRoster's order), one column per date. Each cell stacks real,
 * server-computed facts vertically: working hours, break, each assigned
 * job, and unavailable reasons -- never a fabricated hourly-position
 * timeline, since scheduled_time_window is a free-form label, not a
 * structured start/end (see Dispatch Board's same documented limitation). */
import React from "react";

export interface GridTechnician {
  id: string;
  name: string;
}
export interface GridSchedule {
  staff_id: string; date: string; available: boolean; reasons: string[];
  working_hours: { start: string | null; end: string | null } | null;
  break: { start: string; end: string } | null;
  assignments_today: { job_number: string; status: string; time_window: string | null }[];
  daily_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
}

const REASON_LABELS: Record<string, string> = {
  business_closed: "Business closed", staff_inactive: "Technician inactive",
  staff_setup_incomplete: "Weekly pattern not configured", outside_working_hours: "Outside working hours",
  date_override_blocked: "Date override", on_time_off: "On time off", during_break: "During break",
  schedule_conflict: "Schedule conflict", daily_capacity_exceeded: "Daily capacity reached",
  concurrent_capacity_exceeded: "Concurrent capacity reached", timezone_context_invalid: "Timezone context invalid",
};
function reasonLabel(code: string): string {
  return REASON_LABELS[code.toLowerCase()] ?? code;
}

function DayCell({ schedule, onSelectJob }: { schedule: GridSchedule | undefined; onSelectJob?: (jobNumber: string) => void }) {
  if (!schedule) {
    return <div style={{ padding: "8px 6px", color: "var(--text-tertiary)", fontSize: 12 }}>—</div>;
  }
  if (!schedule.available) {
    const hasConflict = schedule.reasons.some(r => ["schedule_conflict", "daily_capacity_exceeded", "concurrent_capacity_exceeded"].includes(r.toLowerCase()));
    return (
      <div style={{ padding: "8px 6px" }}>
        <span style={{ display: "inline-block", padding: "3px 8px", borderRadius: 6, fontSize: 10.5, fontWeight: 600,
          background: hasConflict ? "var(--danger-bg)" : "var(--surface-sunken)",
          color: hasConflict ? "var(--danger-text)" : "var(--text-tertiary)",
          border: `1px solid ${hasConflict ? "var(--danger-border)" : "var(--border)"}` }}>
          {schedule.reasons.map(reasonLabel).join(", ") || "Off"}
        </span>
      </div>
    );
  }
  const hasConflict = schedule.reasons.some(r => r.toLowerCase() === "schedule_conflict");
  return (
    <div style={{ padding: "6px", display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 10.5, fontWeight: 700, padding: "3px 6px", borderRadius: 6,
        background: "var(--success-bg)", border: "1px solid var(--success-border)", color: "var(--success-text)" }}>
        {schedule.working_hours?.start ?? "—"}–{schedule.working_hours?.end ?? "—"}
      </div>
      {schedule.break && (
        <div style={{ fontSize: 10, padding: "3px 6px", borderRadius: 6,
          background: "var(--surface-sunken)", border: "1px solid var(--border)", color: "var(--text-tertiary)" }}>
          Break {schedule.break.start}–{schedule.break.end}
        </div>
      )}
      {schedule.assignments_today.map(a => (
        <button key={a.job_number} onClick={() => onSelectJob?.(a.job_number)}
          style={{ textAlign: "left", fontSize: 10, padding: "3px 6px", borderRadius: 6, cursor: onSelectJob ? "pointer" : "default",
            background: hasConflict ? "var(--danger-bg)" : "var(--info-bg)",
            border: `1px solid ${hasConflict ? "var(--danger-border)" : "var(--info-border)"}`,
            color: hasConflict ? "var(--danger-text)" : "var(--info-text)" }}>
          {a.time_window ? `${a.time_window} ` : ""}{a.job_number}{hasConflict ? " (Overlap)" : ""}
        </button>
      ))}
      {schedule.daily_capacity?.limit != null && (
        <div style={{ fontSize: 9.5, color: "var(--text-tertiary)" }}>
          {schedule.assignments_today.length}/{schedule.daily_capacity.limit} jobs
        </div>
      )}
    </div>
  );
}

export function WeeklyGrid({
  technicians, days, scheduleFor, selectedStaffId, onSelectStaff, onSelectJob, todayISO,
}: {
  technicians: GridTechnician[]; days: string[];
  scheduleFor: (staffId: string, date: string) => GridSchedule | undefined;
  selectedStaffId: string | null; onSelectStaff: (id: string) => void;
  onSelectJob?: (jobNumber: string) => void; todayISO: string;
}) {
  return (
    <div style={{ flex: 1, minWidth: 0, overflowX: "auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 640 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ padding: "10px 12px", fontWeight: 600, color: "var(--text-tertiary)", textAlign: "left", minWidth: 160 }}>Technician</th>
            {days.map(d => (
              <th key={d} style={{ padding: "10px 8px", fontWeight: 600, color: d === todayISO ? "var(--brand)" : "var(--text-tertiary)",
                textAlign: "left", minWidth: 108 }}>
                {new Date(d + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" })}
                <br/>
                <span style={{ fontWeight: 400 }}>{new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {technicians.map(t => (
            <tr key={t.id} onClick={() => onSelectStaff(t.id)} style={{
              borderBottom: "1px solid var(--border)", cursor: "pointer",
              background: selectedStaffId === t.id ? "var(--accent-muted)" : "transparent",
            }}>
              <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--text-primary)" }}>{t.name}</td>
              {days.map(d => <td key={d} style={{ verticalAlign: "top" }}><DayCell schedule={scheduleFor(t.id, d)} onSelectJob={onSelectJob}/></td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
