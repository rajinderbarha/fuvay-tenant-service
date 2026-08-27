"use client";
import { TableSurface } from "@serviceos/design-system";
/** Weekly/day availability grid -- one row per technician (aligned with
 * TeamRoster's order), one column per date. Each cell stacks real,
 * server-computed facts vertically: working hours, break, each assigned
 * job, and unavailable reasons -- never a fabricated hourly-position
 * timeline, since scheduled_time_window is a free-form label, not a
 * structured start/end (see Dispatch Board's same documented limitation).
 *
 * Cell states map one-to-one onto what the resolver returns, so the legend
 * below the grid is a description of the data and not a paint chart:
 *   green  working hours from the weekly pattern
 *   amber  a date override -- these hours replace the pattern for this date only
 *   grey   a break, time off, or a day the technician does not work
 *   blue   an assigned job
 *   red    a job whose window overlaps another beyond concurrent capacity
 *
 * The tones are built from the app's own semantic hues rather than the
 * page-level --success-bg/--info-bg tokens. Those are tuned for large calm
 * surfaces like banners; at the size of a grid cell they wash out and the
 * five states stop being separable at a glance, which is the one thing this
 * grid has to do. Same hues, more fill -- defined once here and derived for
 * light and dark so the board still follows the theme.
 */
import React from "react";

export interface GridTechnician {
  id: string;
  name: string;
  subtitle?: string | null;
}
export interface GridSchedule {
  staff_id: string; date: string; available: boolean; reasons: string[];
  working_hours: { start: string | null; end: string | null } | null;
  break: { start: string; end: string } | null;
  assignments_today: {
    job_id: string; job_number: string; status: string; time_window: string | null; service_name?: string | null;
  }[];
  daily_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
  concurrent_capacity?: {
    limit: number | null; used?: number; remaining?: number | null; untimed_assignments?: number;
  } | null;
  date_override?: { start: string | null; end: string | null; full_day_closed: boolean; reason: string | null } | null;
  time_off?: { id: string; all_day: boolean; start: string | null; end: string | null; reason: string | null; source: string } | null;
  overlapping_jobs?: string[];
}

const REASON_LABELS: Record<string, string> = {
  business_closed: "Closed", staff_inactive: "Inactive",
  staff_setup_incomplete: "Not scheduled", outside_working_hours: "Outside hours",
  date_override_blocked: "Date override", staff_date_override_closed: "Not working",
  on_time_off: "Time off", staff_time_off: "Time off", during_break: "Break",
  schedule_conflict: "Conflict", daily_capacity_exceeded: "Day full",
  concurrent_capacity_exceeded: "At capacity", timezone_context_invalid: "Timezone invalid",
  assignment_outside_availability: "Assignment outside availability",
};
function reasonLabel(code: string): string {
  return REASON_LABELS[code.toLowerCase()] ?? code;
}

const LEAVE_CODES = ["on_time_off", "staff_time_off"];

/** Scoped to this component so the stronger fills cannot leak into pages that
 *  legitimately want the calm banner tones. */
export const GRID_TONES = `
.avail-grid {
  --cell-ok-bg: rgba(22,163,74,0.10);  --cell-ok-bd: rgba(22,163,74,0.45);  --cell-ok-fg: #15803D;
  --cell-as-bg: rgba(37,99,235,0.10);  --cell-as-bd: rgba(37,99,235,0.45);  --cell-as-fg: #1D4ED8;
  --cell-ov-bg: rgba(217,119,6,0.12);  --cell-ov-bd: rgba(217,119,6,0.55);  --cell-ov-fg: #B45309;
  --cell-cf-bg: rgba(220,38,38,0.10);  --cell-cf-bd: rgba(220,38,38,0.45);  --cell-cf-fg: #B91C1C;
  --cell-mu-bg: rgba(100,116,139,0.10);--cell-mu-bd: rgba(100,116,139,0.35);--cell-mu-fg: #475569;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .avail-grid {
    --cell-ok-bg: rgba(34,197,94,0.16);  --cell-ok-bd: rgba(34,197,94,0.45);  --cell-ok-fg: #86EFAC;
    --cell-as-bg: rgba(56,130,246,0.18); --cell-as-bd: rgba(56,130,246,0.50); --cell-as-fg: #93C5FD;
    --cell-ov-bg: rgba(245,158,11,0.18); --cell-ov-bd: rgba(245,158,11,0.60); --cell-ov-fg: #FCD34D;
    --cell-cf-bg: rgba(248,113,113,0.18);--cell-cf-bd: rgba(248,113,113,0.55);--cell-cf-fg: #FCA5A5;
    --cell-mu-bg: rgba(148,163,184,0.13);--cell-mu-bd: rgba(148,163,184,0.30);--cell-mu-fg: #94A3B8;
  }
}
[data-theme="dark"] .avail-grid {
  --cell-ok-bg: rgba(34,197,94,0.16);  --cell-ok-bd: rgba(34,197,94,0.45);  --cell-ok-fg: #86EFAC;
  --cell-as-bg: rgba(56,130,246,0.18); --cell-as-bd: rgba(56,130,246,0.50); --cell-as-fg: #93C5FD;
  --cell-ov-bg: rgba(245,158,11,0.18); --cell-ov-bd: rgba(245,158,11,0.60); --cell-ov-fg: #FCD34D;
  --cell-cf-bg: rgba(248,113,113,0.18);--cell-cf-bd: rgba(248,113,113,0.55);--cell-cf-fg: #FCA5A5;
  --cell-mu-bg: rgba(148,163,184,0.13);--cell-mu-bd: rgba(148,163,184,0.30);--cell-mu-fg: #94A3B8;
}
.avail-cell { display:block; width:100%; box-sizing:border-box; text-align:left;
  border-radius:7px; padding:5px 7px; font-size:11px; line-height:1.35; border:1px solid; }
.avail-cell + .avail-cell { margin-top:5px; }
.avail-ok { background:var(--cell-ok-bg); border-color:var(--cell-ok-bd); color:var(--cell-ok-fg); font-weight:700; }
.avail-as { background:var(--cell-as-bg); border-color:var(--cell-as-bd); color:var(--cell-as-fg); font-weight:600; }
.avail-ov { background:var(--cell-ov-bg); border-color:var(--cell-ov-bd); color:var(--cell-ov-fg); font-weight:700; position:relative; }
.avail-cf { background:var(--cell-cf-bg); border-color:var(--cell-cf-bd); color:var(--cell-cf-fg); font-weight:600; }
.avail-mu { background:var(--cell-mu-bg); border-color:var(--cell-mu-bd); color:var(--cell-mu-fg); font-weight:500; }
button.avail-cell { cursor:pointer; font-family:inherit; }
.avail-sub { display:block; font-weight:600; opacity:0.92; }
/* The corner flag marks a date override without spending a line of the cell on
   saying so -- the amber already carries the meaning, this confirms it. */
.avail-ov::after { content:""; position:absolute; top:0; right:0; width:0; height:0;
  border-top:9px solid var(--cell-ov-bd); border-left:9px solid transparent; border-top-right-radius:6px; }
`;

function DayCell({ schedule, onSelectJob }: {
  schedule: GridSchedule | undefined;
  onSelectJob?: (jobId: string) => void;
}) {
  const pad: React.CSSProperties = { padding: "7px 6px" };

  if (!schedule) {
    return <div style={{ ...pad, color: "var(--text-tertiary)", fontSize: 12, textAlign: "center" }}>—</div>;
  }

  const codes = schedule.reasons.map(r => r.toLowerCase());
  const onLeave = codes.some(c => LEAVE_CODES.includes(c));

  // Being full is not the same as not working, and the cell must not treat it as such.
  // `available` goes false for both, so a technician with 4 of 4 jobs booked rendered
  // as a bare "Day full" chip -- their hours, their break and the four jobs themselves
  // all vanished from the board at exactly the moment the provider most needed to see
  // them, to decide what to move. Capacity is drawn ON the day, not instead of it.
  const capacityOnly = !schedule.available && codes.every(c =>
    ["daily_capacity_exceeded", "concurrent_capacity_exceeded", "schedule_conflict"].includes(c));

  if (!schedule.available && !capacityOnly && schedule.assignments_today.length === 0) {
    // Leave gets its own cell rather than a generic reason chip: "Time off" is the
    // single fact the provider is scanning the row for, and burying it in a list of
    // codes is what made this column unreadable.
    if (onLeave) {
      return (
        <div style={pad}>
          <div className="avail-cell avail-mu" title={schedule.time_off?.reason ?? undefined}>Time off</div>
        </div>
      );
    }
    // A technician who simply does not work this day is background, not an alert --
    // plain text, the way the design leaves Sunday quiet.
    if (codes.includes("staff_setup_incomplete") || codes.includes("business_closed")) {
      return (
        <div style={{ ...pad, color: "var(--text-tertiary)", fontSize: 11.5, textAlign: "center" }}>
          {codes.includes("business_closed") ? "Closed" : "Off"}
        </div>
      );
    }
    const hasConflict = codes.includes("schedule_conflict");
    return (
      <div style={pad}>
        <div className={`avail-cell ${hasConflict ? "avail-cf" : "avail-mu"}`}>
          {schedule.reasons.map(reasonLabel).join(", ") || "Off"}
        </div>
      </div>
    );
  }

  // An override replaces the weekly pattern for this date only, so the hours are drawn
  // amber and flagged -- otherwise a one-off 10:00-16:00 is indistinguishable from the
  // pattern, and the provider cannot see which days they have already changed.
  const override = schedule.date_override && !schedule.date_override.full_day_closed
    ? schedule.date_override : null;
  const overlapping = new Set(schedule.overlapping_jobs ?? []);
  const full = codes.includes("daily_capacity_exceeded") || codes.includes("concurrent_capacity_exceeded");

  return (
    <div style={pad}>
      <div
        className={`avail-cell ${override ? "avail-ov" : "avail-ok"}`}
        title={override ? `Date override${override.reason ? ` — ${override.reason}` : ""}` : undefined}
      >
        {schedule.working_hours?.start ?? "—"}–{schedule.working_hours?.end ?? "—"}
      </div>

      {schedule.break && (
        <div className="avail-cell avail-mu">{schedule.break.start}–{schedule.break.end}</div>
      )}

      {/* A part-day absence does not close the day, so it shows alongside the hours the
          technician still works rather than replacing them. */}
      {schedule.time_off && !schedule.time_off.all_day && (
        <div className="avail-cell avail-mu" title={schedule.time_off.reason ?? undefined}>
          Off {schedule.time_off.start}–{schedule.time_off.end}
        </div>
      )}

      {schedule.assignments_today.map(a => {
        const clash = overlapping.has(a.job_number);
        // The service name is what the provider recognises; the job number is the
        // fallback when a job has no resolvable offering, not the headline.
        const label = a.service_name ?? a.job_number;
        return (
          <button
            key={a.job_number}
            className={`avail-cell ${clash ? "avail-cf" : "avail-as"}`}
            onClick={onSelectJob ? event => { event.stopPropagation(); onSelectJob(a.job_id); } : undefined}
            title={clash
              ? `${a.job_number} — this job's window overlaps another beyond concurrent capacity.`
              : a.job_number}
          >
            {a.time_window ?? "Unscheduled"}
            <span className="avail-sub">{label}{clash ? " (Overlap)" : ""}</span>
          </button>
        );
      })}

      {schedule.daily_capacity?.limit != null && (
        <div style={{ fontSize: 9.5, marginTop: 5, fontWeight: full ? 700 : 400,
          color: full ? "var(--cell-ov-fg)" : "var(--text-tertiary)" }}>
          {schedule.assignments_today.length}/{schedule.daily_capacity.limit} jobs{full ? " · full" : ""}
        </div>
      )}

      {/* Jobs with no readable time window cannot be placed against concurrent capacity,
          so the conflict check silently could not see them. Saying so is the difference
          between "no clash" and "no clash that I could check". */}
      {(schedule.concurrent_capacity?.untimed_assignments ?? 0) > 0 && (
        <div style={{ fontSize: 9.5, color: "var(--text-tertiary)", marginTop: 3 }}>
          {schedule.concurrent_capacity!.untimed_assignments} untimed
        </div>
      )}
    </div>
  );
}

export function WeeklyGrid({
  technicians, days, scheduleFor, selectedStaffId, onSelectCell, onSelectJob, todayISO,
}: {
  technicians: GridTechnician[]; days: string[];
  scheduleFor: (staffId: string, date: string) => GridSchedule | undefined;
  selectedStaffId: string | null; onSelectCell: (id: string, date: string) => void;
  onSelectJob?: (jobId: string) => void; todayISO: string;
}) {
  return (
    <div className="avail-grid" style={{ flex: 1, minWidth: 0, overflowX: "auto",
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20 }}>
      <style>{GRID_TONES}</style>
      <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 700 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ padding: "11px 12px", fontWeight: 600, color: "var(--text-tertiary)", textAlign: "left", minWidth: 150 }}>Technician</th>
            {days.map(d => (
              <th key={d} style={{ padding: "9px 8px", fontWeight: 600, color: d === todayISO ? "var(--brand)" : "var(--text-tertiary)",
                textAlign: "center", minWidth: 108 }}>
                {new Date(d + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" })}
                <br/>
                <span style={{ fontWeight: 400, fontSize: 11 }}>{new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {technicians.map(t => (
            <tr key={t.id} style={{
              borderBottom: "1px solid var(--border)", cursor: "pointer",
              background: selectedStaffId === t.id ? "var(--accent-muted)" : "transparent",
            }}>
              <td style={{ padding: "10px 12px", verticalAlign: "top" }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{t.name}</div>
                {t.subtitle && (
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{t.subtitle}</div>
                )}
              </td>
              {days.map(d => (
                <td key={d} onClick={() => onSelectCell(t.id, d)} style={{ verticalAlign: "top", borderLeft: "1px solid var(--border)" }}>
                  <DayCell schedule={scheduleFor(t.id, d)} onSelectJob={onSelectJob}/>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </TableSurface>
    </div>
  );
}
