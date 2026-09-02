"use client";
/**
 * Home Services â€” Availability & Capacity Planner.
 *
 * Data layer is unchanged from the original build this session:
 *   GET /v1/tenant/home-services/availability?from=&to=&staff_id=
 *     (availability_planner_router.py -> availability_resolver.resolve_tenant_week())
 *   GET /v1/tenant/home-services/availability/staff/{staff_id}
 *     (availability_resolver.resolve_staff_day())
 *   GET /v1/tenant/home-services/team/{staff_id}/overview
 *     (team_directory_router.py -- real supported_services for the detail panel)
 *
 * Presentation layer is rebuilt with dedicated components
 * (components/availability/*) matching the approved reference design
 * exactly, replacing the generic @serviceos/design-system PageHeader/Card/
 * Button primitives used in the first pass.
 *
 * Per-technician date overrides and time off are REAL as of migration 242
 * and are read/written here:
 *   GET/PUT/DELETE /v1/provider/team/{staff_id}/overrides
 *   GET/POST/DELETE /v1/provider/team/{staff_id}/time-off
 * The page used to carry disclosures saying neither table existed. They do
 * now, the resolver reads them, and the disclosures have been removed
 * rather than left to contradict the data on screen.
 *
 * Conflicts are DERIVED, not stored: the resolver reports the peak number
 * of assignment windows running at once against the technician's
 * max_concurrent_jobs, and the jobs involved. There is still no conflict
 * table, which is what capability_flags.schedule_conflict_table_supported
 * continues to say.
 */
import React, { Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Skeleton, Btn, Card, Pagination } from "../../../../components/shared/ui";
import { apiFetch } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { PageHeader, PageShell } from "@serviceos/design-system";
import { AvailabilityKpis } from "../../../../components/availability/AvailabilityKpis";
import { AvailabilityFilters } from "../../../../components/availability/AvailabilityFilters";
import { TeamRoster, type RosterRow } from "../../../../components/availability/TeamRoster";
import { WeeklyGrid } from "../../../../components/availability/WeeklyGrid";
import { AvailabilityLegend } from "../../../../components/availability/AvailabilityLegend";
import {
  ScheduleDetailPanel, to12h,
  type WeeklyPatternLine, type DateOverride, type TimeOffEntry, type ConflictDetail,
  type ReadinessState,
} from "../../../../components/availability/ScheduleDetailPanel";

// â”€â”€ Types (mirror the real backend response shapes exactly) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface Technician {
  id: string; full_name: string; designation: string | null;
  status: string; max_concurrent_jobs: number | null; profile_photo_url: string | null;
  member_type: string; supported_service_ids: string[];
  supported_services: { id: string; name: string }[];
}
interface EffectiveSchedule {
  staff_id: string; date: string; available: boolean; reasons: string[];
  timezone: string;
  business_hours: { start: string | null; end: string | null } | null;
  working_hours: { start: string | null; end: string | null } | null;
  break: { start: string; end: string } | null;
  daily_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
  concurrent_capacity: {
    limit: number | null; used?: number; remaining?: number | null;
    untimed_assignments?: number;
  } | null;
  assignments_today: {
    job_id: string; job_number: string; status: string; time_window: string | null; service_name: string | null;
  }[];
  capability_flags: { time_off_supported: boolean; date_override_supported_per_staff: boolean };
  date_override: { start: string | null; end: string | null; full_day_closed: boolean; reason: string | null } | null;
  time_off: { id: string; all_day: boolean; start: string | null; end: string | null; reason: string | null; source: string } | null;
  overlapping_jobs: string[];
}
interface PlannerResponse {
  generated_at: string; timezone: string; from: string; to: string;
  summary: {
    available_today: number; on_leave_today: number; total_capacity: number;
    technician_count: number; conflicts: number;
  };
  technicians: Technician[];
  effective_schedules: EffectiveSchedule[];
  conflicts: {
    staff_id: string; date: string; reasons: string[];
    overlapping_jobs: string[]; concurrent_limit: number | null; peak_concurrent: number | null;
  }[];
  capability_flags: {
    time_off_supported: boolean;
    date_override_supported_per_staff: boolean;
    schedule_conflict_table_supported: boolean;
    schedule_conflict_derived: boolean;
  };
  pagination: { total: number; limit: number; offset: number; has_next: boolean };
  available_filters: {
    designations: string[];
    capabilities: { id: string; name: string }[];
  };
}
interface StaffDetail extends EffectiveSchedule {}

// The impact-preview shape lived here for the weekly-pattern editor this page used to
// carry. That editor is gone -- weekly patterns are not what customers book against --
// so the type went with it. /v1/tenant/home-services/availability/preview-change is
// untouched and still serves whoever edits a pattern; this page is simply no longer that
// caller.

function toISODate(d: Date): string { return d.toISOString().slice(0, 10); }
function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return toISODate(d);
}
function startOfWeek(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - d.getUTCDay());
  return toISODate(d);
}
function fmtRange(from: string, to: string): string {
  const f = new Date(from + "T00:00:00");
  const t = new Date(to + "T00:00:00");
  const fs = f.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  const ts = t.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  return from === to ? t.toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "short", year: "numeric" }) : `${fs} – ${ts}`;
}

// Groups the current week's 7 daily working-hours ranges into contiguous
// same-value runs, e.g. "Mon â€“ Sat: 9:00 AM â€“ 6:00 PM" / "Sunday: Off" --
// purely a client-side aggregation of already-fetched real data, no guess.
function summarizeWeeklyPattern(days: string[], schedules: EffectiveSchedule[], staffId: string): WeeklyPatternLine[] {
  const dayName = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" });
  const values = days.map(d => {
    const s = schedules.find(x => x.staff_id === staffId && x.date === d);
    // The panel writes hours out the way a person would ("9:00 AM â€“ 6:00 PM"); the grid
    // keeps 24-hour because its cells have no room for the suffix.
    return s?.working_hours?.start && s?.working_hours?.end
      ? `${to12h(s.working_hours.start)} – ${to12h(s.working_hours.end)}`
      : "Off";
  });
  const lines: WeeklyPatternLine[] = [];
  let i = 0;
  while (i < values.length) {
    let j = i;
    while (j + 1 < values.length && values[j + 1] === values[i]) j++;
    const label = i === j ? dayName(days[i]) : `${dayName(days[i])} – ${dayName(days[j])}`;
    lines.push({ label, value: values[i] });
    i = j + 1;
  }
  return lines;
}

/** Books a technician off for a date or a range.
 *
 * Writes to POST /v1/provider/team/{id}/time-off, which records it approved -- the owner
 * is entering it, so there is nobody left to approve it. The resolver picks it up on the
 * next read, which is why this closes and refetches rather than patching local state:
 * whether a day actually went unavailable is the resolver's answer, not this form's. */
function AddTimeOffModal({ staffId, staffName, defaultDate, onClose, onSaved }: {
  staffId: string; staffName: string; defaultDate: string;
  onClose: () => void; onSaved: () => void;
}) {
  const [startDate, setStartDate] = useState(defaultDate);
  const [endDate, setEndDate] = useState(defaultDate);
  const [allDay, setAllDay] = useState(true);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("13:00");
  const [reason, setReason] = useState("");

  const save = useAction(useCallback(async () => {
    return await apiFetch<{ id: string }>(`/v1/provider/team/${staffId}/time-off`, {
      method: "POST",
      body: JSON.stringify({
        start_date: startDate,
        // A single day is start == end, the same shape the range uses -- the backend
        // treats the range as inclusive.
        end_date: endDate < startDate ? startDate : endDate,
        all_day: allDay,
        start_time: allDay ? null : startTime,
        end_time: allDay ? null : endTime,
        reason: reason.trim() || null,
      }),
    });
  }, [staffId, startDate, endDate, allDay, startTime, endTime, reason]));

  const handleSave = async () => {
    const res = await save.execute();
    if (res) { onSaved(); onClose(); }
  };

  const input: React.CSSProperties = {
    width: "100%", boxSizing: "border-box", padding: "6px 8px", borderRadius: 6,
    border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)",
  };

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 959 }}/>
      <div role="dialog" aria-label="Add time off" style={{
        position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
        width: 380, maxWidth: "92vw", background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 14, boxShadow: "0 12px 40px rgba(0,0,0,0.4)", zIndex: 960, padding: 20,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <strong style={{ fontSize: 14, color: "var(--text-primary)" }}>Add time off</strong>
          <button aria-label="Close" onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer" }}>×</button>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{staffName}</p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 12 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>From</label>
              <input type="date" value={startDate} style={input}
                onChange={e => {
                  setStartDate(e.target.value);
                  // Keeps the range valid as you type instead of waiting for the server
                  // to reject end-before-start.
                  if (endDate < e.target.value) setEndDate(e.target.value);
                }}/>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>To</label>
              <input type="date" value={endDate} min={startDate} style={input}
                onChange={e => setEndDate(e.target.value)}/>
            </div>
          </div>

          <label style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={allDay} onChange={e => setAllDay(e.target.checked)}/>
            All day
          </label>

          {!allDay && (
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Start</label>
                <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} style={input}/>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>End</label>
                <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} style={input}/>
              </div>
            </div>
          )}

          <div>
            <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Reason (optional)</label>
            <input type="text" value={reason} maxLength={300} placeholder="Annual leave, sick, training…"
              onChange={e => setReason(e.target.value)} style={input}/>
          </div>

          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            A part-day absence blocks only those hours — the technician stays bookable for the rest of the day.
          </p>

          {save.error && (
            <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--danger-bg)",
              border: "1px solid var(--danger-border)", color: "var(--danger-text)" }}>{save.error}</div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <Btn variant="primary" size="sm" onClick={handleSave} loading={save.loading}>Book time off</Btn>
            <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
          </div>
        </div>
      </div>
    </>
  );
}

/** Changes ONE technician's hours for ONE date.
 *
 * This drawer used to edit the technician's recurring weekly pattern too, with an
 * impact-preview step. That was the wrong control on the wrong page. Bookable slots come
 * from the BUSINESS hours -- opening time, slot length, and bookings per slot, which the
 * provider sizes against how many technicians they have -- and none of that is
 * per-technician. Editing a technician's weekly pattern here changed a number the booking
 * engine does not read, so the page offered a setting that looked load-bearing and was
 * not. Business hours are edited in one place now, Business > Business Hours, and this
 * drawer does the thing that genuinely is per-person and per-day: a one-off override.
 */
function DateOverrideDrawer({
  staffId, staffName, dateISO, initial, onClose, onSaved,
}: {
  staffId: string; staffName: string; dateISO: string;
  initial: { start: string | null; end: string | null };
  onClose: () => void; onSaved: () => void;
}) {
  const [startTime, setStartTime] = useState(initial.start ?? "09:00");
  const [endTime, setEndTime] = useState(initial.end ?? "18:00");
  const [closed, setClosed] = useState(false);
  const [reason, setReason] = useState("");
  const [saved, setSaved] = useState(false);

  const save = useAction(useCallback(async () => {
    return await apiFetch<Record<string, unknown>>(`/v1/provider/team/${staffId}/overrides`, {
      method: "PUT",
      body: JSON.stringify({
        override_date: dateISO,
        start_time: closed ? null : startTime,
        end_time: closed ? null : endTime,
        full_day_closed: closed,
        reason: reason.trim() || null,
      }),
    });
  }, [staffId, dateISO, closed, startTime, endTime, reason]));

  const handleSave = async () => {
    const res = await save.execute();
    if (res) { setSaved(true); onSaved(); }
  };

  const input: React.CSSProperties = {
    flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)",
    background: "var(--surface-sunken)", color: "var(--text-primary)",
  };
  const dateLabel = new Date(dateISO + "T00:00:00").toLocaleDateString("en-IN", {
    weekday: "long", day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <>
      {/* Stacks above the Schedule Details drawer (z 900) with its own backdrop --
          without one it rendered behind, and the button appeared to do nothing. */}
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 949 }}/>
      <div style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 380, background: "var(--surface)",
        borderLeft: "1px solid var(--border)", boxShadow: "-4px 0 24px rgba(0,0,0,0.3)", zIndex: 950,
        padding: 20, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <strong style={{ fontSize: 14, color: "var(--text-primary)" }}>Override this date</strong>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer", fontSize: 14 }}>✕</button>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 0, marginBottom: 16 }}>
          {staffName} · {dateLabel}
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 12 }}>
          <label style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={closed} onChange={e => { setClosed(e.target.checked); setSaved(false); }}/>
            Not working this day
          </label>

          <div style={{ display: closed ? "none" : "block" }}>
            <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Hours for this date</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input type="time" value={startTime} style={input}
                onChange={e => { setStartTime(e.target.value); setSaved(false); }}/>
              <input type="time" value={endTime} style={input}
                onChange={e => { setEndTime(e.target.value); setSaved(false); }}/>
            </div>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Reason (optional)</label>
            <input type="text" value={reason} maxLength={300} placeholder="Late start, half day, training…"
              onChange={e => setReason(e.target.value)}
              style={{ ...input, width: "100%", boxSizing: "border-box" }}/>
          </div>

          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            Applies to {dateLabel} only. The weekly pattern is untouched, and bookable slots still
            come from your business hours.
          </p>

          {save.error && (
            <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--danger-bg)",
              border: "1px solid var(--danger-border)", color: "var(--danger-text)" }}>{save.error}</div>
          )}
          {saved && (
            <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--success-bg)", color: "var(--success-text)" }}>Saved.</div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <Btn variant="primary" size="sm" onClick={handleSave} loading={save.loading}>Save override</Btn>
            <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
          </div>
        </div>
      </div>
    </>
  );
}

export default function AvailabilityCapacityPlannerPage() {
  return <Suspense fallback={<PageShell><Skeleton height={520} /></PageShell>}><AvailabilityCapacityPlannerContent /></Suspense>;
}

function AvailabilityCapacityPlannerContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [weekStart, setWeekStart] = useState(() => startOfWeek(toISODate(new Date())));
  const weekEnd = addDays(weekStart, 6);
  const [view, setView] = useState<"week" | "day">("week");
  const [selectedDate, setSelectedDate] = useState(() => toISODate(new Date()));
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [availFilter, setAvailFilter] = useState<"" | "available" | "unavailable">("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;
  // Team member detail links here with staff_id. Honour it on first render so
  // "Manage availability" opens the intended technician rather than a
  // generic board that makes the provider search for the same person again.
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(() => searchParams.get("staff_id"));
  const [editingStaffId, setEditingStaffId] = useState<string | null>(null);
  const [addingTimeOffFor, setAddingTimeOffFor] = useState<string | null>(null);
  // Bumped after any write. Every read that a write can invalidate depends on it, so the
  // board, the grid cells and the drawer lists all re-resolve together -- a technician
  // booked off must not stay green in the grid because only the drawer refetched.
  const [mutationSeq, setMutationSeq] = useState(0);
  const bumpMutation = useCallback(() => setMutationSeq(n => n + 1), []);

  const rangeFrom = view === "day" ? selectedDate : weekStart;
  const rangeTo = view === "day" ? selectedDate : weekEnd;
  const moveRange = (direction: -1 | 1) => {
    if (view === "day") {
      const next = addDays(selectedDate, direction);
      setSelectedDate(next);
      setWeekStart(startOfWeek(next));
    } else {
      setWeekStart(current => addDays(current, direction * 7));
      setSelectedDate(current => addDays(current, direction * 7));
    }
    setPage(1);
  };
  const goToday = () => {
    const today = toISODate(new Date());
    setSelectedDate(today);
    setWeekStart(startOfWeek(today));
    setPage(1);
  };

  // Every useApi here passes its deps TWICE on purpose: once to useCallback and once to
  // useApi. useApi memoizes its effect on the second argument and ignores the fetcher's
  // own identity, so omitting it -- as this page previously did -- meant the week arrows
  // and technician selection changed the closure and never re-ran the fetch. The
  // technician drawer in particular then rendered "no upcoming time off" for a
  // technician the grid was simultaneously showing on leave.
  const planner = useApi(useCallback(async () => {
    const qs = new URLSearchParams({
      from: rangeFrom, to: rangeTo, focus_date: selectedDate,
      limit: String(pageSize), offset: String((page - 1) * pageSize),
    });
    if (search.trim()) qs.set("search", search.trim());
    if (roleFilter) qs.set("designation", roleFilter);
    if (availFilter) qs.set("availability", availFilter);
    if (capabilityFilter) qs.set("capability", capabilityFilter);
    return await apiFetch<PlannerResponse>(`/v1/tenant/home-services/availability?${qs}`);
  }, [rangeFrom, rangeTo, selectedDate, page, search, roleFilter, availFilter, capabilityFilter, mutationSeq]),
  [rangeFrom, rangeTo, selectedDate, page, search, roleFilter, availFilter, capabilityFilter, mutationSeq]);

  const detail = useApi(useCallback(async () => {
    if (!selectedStaffId) return null;
    const qs = new URLSearchParams({ date: selectedDate });
    return await apiFetch<StaffDetail>(`/v1/tenant/home-services/availability/staff/${selectedStaffId}?${qs}`);
  }, [selectedStaffId, selectedDate, mutationSeq]), [selectedStaffId, selectedDate, mutationSeq]);

  // Fetched per selected technician rather than for the whole roster: the list endpoints
  // are per-staff, and pulling them for everyone to fill one drawer would be N+1 requests
  // for data only the open drawer shows.
  const overridesQ = useApi(useCallback(async () => {
    if (!selectedStaffId) return null;
    const res = await apiFetch<{ overrides: DateOverride[] }>(
      `/v1/provider/team/${selectedStaffId}/overrides?from_date=${weekStart}`);
    return res.overrides;
  }, [selectedStaffId, weekStart, mutationSeq]), [selectedStaffId, weekStart, mutationSeq]);

  const timeOffQ = useApi(useCallback(async () => {
    if (!selectedStaffId) return null;
    const res = await apiFetch<{ time_off: TimeOffEntry[] }>(
      `/v1/provider/team/${selectedStaffId}/time-off?upcoming_only=true`);
    return res.time_off;
  }, [selectedStaffId, mutationSeq]), [selectedStaffId, mutationSeq]);

  const cancelTimeOff = useAction(useCallback(async (id: string) => {
    await apiFetch(`/v1/provider/team/${selectedStaffId}/time-off/${id}`, { method: "DELETE" });
  }, [selectedStaffId]), { onSuccess: () => bumpMutation() });

  const removeOverride = useAction(useCallback(async (date: string) => {
    await apiFetch(`/v1/provider/team/${selectedStaffId}/overrides/${date}`, { method: "DELETE" });
  }, [selectedStaffId]), { onSuccess: () => bumpMutation() });

  const technicians = planner.data?.technicians ?? [];
  const schedules = planner.data?.effective_schedules ?? [];

  const days = useMemo(() => {
    if (view === "day") return [selectedDate];
    const out: string[] = [];
    for (let i = 0; i < 7; i++) out.push(addDays(weekStart, i));
    return out;
  }, [view, weekStart, selectedDate]);

  const filteredTechnicians = technicians;
  const roles = planner.data?.available_filters.designations ?? [];
  const capabilities = planner.data?.available_filters.capabilities ?? [];

  const scheduleFor = useCallback((staffId: string, date: string) => schedules.find(s => s.staff_id === staffId && s.date === date), [schedules]);

  const summary = planner.data?.summary;
  const capFlags = planner.data?.capability_flags;

  const rosterRows: RosterRow[] = filteredTechnicians.map(t => {
    const s = scheduleFor(t.id, selectedDate);
    const codes = (s?.reasons ?? []).map(r => r.toLowerCase());
    const hasConflict = codes.includes("schedule_conflict");
    const setupIncomplete = codes.includes("staff_setup_incomplete");
    // Either leave code. The two record who entered it, not a different kind of absence.
    const onLeave = codes.includes("on_time_off") || codes.includes("staff_time_off");
    const full = codes.includes("daily_capacity_exceeded") || codes.includes("concurrent_capacity_exceeded");
    const statusLabel: RosterRow["statusLabel"] = hasConflict ? "Conflict"
      : onLeave ? "On leave"
      : setupIncomplete ? "Setup incomplete"
      : s?.available ? "Available"
      // Checked after the hard blocks: a technician on leave is not "fully booked",
      // even though the resolver marks both unavailable.
      : full ? "Fully booked" : "Unavailable";
    return {
      id: t.id, name: t.full_name, designation: t.designation,
      jobsToday: s?.assignments_today.length ?? 0,
      // The day's job COUNT over the day's LIMIT. This divided the count by
      // max_concurrent_jobs instead, so a technician allowed 4 jobs a day but only 1 at
      // a time read "4/1 jobs" -- a ratio of two different things, and one that looks
      // like a technician 400% over capacity when they are exactly full.
      dailyLimit: s?.daily_capacity?.limit ?? null,
      photoUrl: t.profile_photo_url,
      statusLabel,
    };
  });

  const selectedTech = technicians.find(t => t.id === selectedStaffId) ?? null;
  const selectedSchedule = selectedStaffId ? scheduleFor(selectedStaffId, selectedDate) : undefined;
  const weeklyPattern = selectedStaffId ? summarizeWeeklyPattern(days.length === 7 ? days : Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), schedules, selectedStaffId) : [];
  // The panel reports the technician's NEXT conflict anywhere in the visible range, not
  // just on the selected date. A provider who lands on the board with "Conflicts 1" and
  // clicks the flagged technician should be told which day it is -- requiring them to
  // first guess the date defeats the tile.
  const staffConflict: ConflictDetail | null = useMemo(() => {
    if (!selectedStaffId) return null;
    const all = planner.data?.conflicts ?? [];
    const mine = all.filter(c => c.staff_id === selectedStaffId);
    if (mine.length === 0) return null;
    const c = mine.find(x => x.date === selectedDate) ?? mine[0];
    return {
      dateLabel: new Date(c.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "short" }),
      jobNumbers: c.overlapping_jobs ?? [],
      peak: c.peak_concurrent ?? null,
      limit: c.concurrent_limit ?? null,
      dispatchHref: `/home-services/dispatch?date=${c.date}&technician=${selectedStaffId}&focus=conflicts`,
    };
  }, [selectedStaffId, selectedDate, planner.data]);

  const conflictCount = planner.data?.conflicts.length ?? 0;

  // The line under the drawer's title. Read off the resolver's own reasons for the
  // selected date rather than a stored "status" -- what the provider wants to know is
  // whether this person can take work right now, which no column records.
  const readiness: ReadinessState = useMemo(() => {
    if (!selectedSchedule) return { label: "No schedule resolved", tone: "muted" };
    const codes = selectedSchedule.reasons.map(r => r.toLowerCase());
    if (codes.includes("schedule_conflict")) return { label: "Has a conflict", tone: "bad" };
    if (codes.some(c => ["on_time_off", "staff_time_off"].includes(c))) return { label: "On leave", tone: "muted" };
    if (codes.includes("staff_date_override_closed")) return { label: "Not working this day", tone: "muted" };
    if (codes.includes("staff_setup_incomplete")) return { label: "Weekly pattern not set", tone: "warn" };
    if (codes.includes("staff_inactive")) return { label: "Inactive", tone: "muted" };
    if (codes.includes("business_closed")) return { label: "Business closed", tone: "muted" };
    if (codes.some(c => ["daily_capacity_exceeded", "concurrent_capacity_exceeded"].includes(c)))
      return { label: "Fully booked", tone: "warn" };
    return selectedSchedule.available
      ? { label: "Ready", tone: "ok" }
      : { label: "Unavailable", tone: "muted" };
  }, [selectedSchedule]);

  return (
    <PageShell>
      <style>{`
        .availability-workspace{display:flex;gap:16px;align-items:flex-start}
        @media(max-width:1280px){.availability-workspace{display:grid;grid-template-columns:260px minmax(0,1fr)}.availability-workspace>aside:last-child{grid-column:1/-1}}
        @media(max-width:820px){.availability-workspace{grid-template-columns:1fr}.availability-workspace>aside{position:static!important;width:auto!important}}
      `}</style>
      <PageHeader
        eyebrow="Daily work"
        context="Team planning"
        title="Availability & Capacity"
        description="Plan working hours, time off and safe booking capacity for your team."
        actions={<>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 4 }}>
            <button onClick={() => moveRange(-1)} aria-label={view === "day" ? "Previous day" : "Previous week"}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 6, display: "flex" }}>
              <ChevronLeft size={16}/>
            </button>
            <span style={{ fontSize: 13, color: "var(--text-primary)", padding: "0 6px", fontWeight: 600, whiteSpace: "nowrap" }}>{fmtRange(rangeFrom, rangeTo)}</span>
            <button onClick={() => moveRange(1)} aria-label={view === "day" ? "Next day" : "Next week"}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 6, display: "flex" }}>
              <ChevronRight size={16}/>
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 3 }}>
            <button onClick={() => setView("week")} style={{ background: view === "week" ? "var(--brand)" : "none", color: view === "week" ? "var(--text-on-brand)" : "var(--text-secondary)", border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>Week</button>
            <button onClick={() => setView("day")} style={{ background: view === "day" ? "var(--brand)" : "none", color: view === "day" ? "var(--text-on-brand)" : "var(--text-secondary)", border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>Day</button>
          </div>
          <Btn variant="secondary" onClick={goToday}>Today</Btn>
          {/* Jumps to the first overlapping-assignment conflict in the visible range and
              opens that technician's panel, where the day and the jobs are named. */}
          <Btn
            variant="secondary"
            disabled={conflictCount === 0}
            onClick={() => {
              const first = planner.data?.conflicts[0];
              if (!first) return;
              setSelectedStaffId(first.staff_id);
              setSelectedDate(first.date);
            }}
          >
            Review conflicts {conflictCount > 0 ? conflictCount : ""}
          </Btn>
          <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={planner.refetch}>Refresh</Btn>
          {/* The primary action on this page is NOT editing a technician's schedule.
              What customers can book is set by the business's own opening hours, slot
              length and bookings per slot, so that is where the button goes. This board
              plans people against those hours; it does not define them. */}
          <Btn variant="primary" onClick={() => router.push("/business/coverage-hours")}>
            Business hours
          </Btn>
        </>}
      />

      {planner.loading ? (
        <div style={{ display: "flex", gap: 14, margin: "20px 0" }}>
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} height={90} style={{ flex: 1 }}/>)}
        </div>
      ) : summary && (() => {
        const today = schedules.filter(s => s.date === selectedDate);
        const assigned = today.reduce((n, s) => n + s.assignments_today.length, 0);
        return (
          <AvailabilityKpis dateLabel={selectedDate === toISODate(new Date()) ? "today" : new Date(selectedDate + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short" })} values={{
            availableToday: summary.available_today,
            onLeave: summary.on_leave_today,
            totalCapacity: summary.total_capacity,
            assigned,
            // Deliberately Total minus Assigned rather than a sum of per-technician
            // concurrent remainders. Those two answer different questions, and showing
            // the second under a tile sitting between Total and Assigned invited the
            // provider to read three numbers that did not add up.
            remaining: Math.max(summary.total_capacity - assigned, 0),
            conflicts: summary.conflicts,
          }}/>
        );
      })()}

      {planner.error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>
          {planner.error}
        </div>
      )}

      <AvailabilityFilters
        search={search} onSearch={value => { setSearch(value); setPage(1); }}
        roleFilter={roleFilter} onRole={value => { setRoleFilter(value); setPage(1); }} roles={roles}
        availFilter={availFilter} onAvail={value => { setAvailFilter(value); setPage(1); }}
        capabilityFilter={capabilityFilter} onCapability={value => { setCapabilityFilter(value); setPage(1); }} capabilities={capabilities}
        timezone={planner.data?.timezone ?? null}
        onReset={() => { setSearch(""); setRoleFilter(""); setAvailFilter(""); setCapabilityFilter(""); setPage(1); }}
      />

      {planner.loading ? (
        <div style={{ display: "flex", gap: 16 }}>
          <Skeleton height={420} style={{ width: 260 }}/>
          <Skeleton height={420} style={{ flex: 1 }}/>
        </div>
      ) : rosterRows.length === 0 ? (
        <Card style={{ textAlign: "center" }}>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>No technicians match this view.</p>
        </Card>
      ) : (
        <div className="availability-workspace">
          <TeamRoster
            rows={rosterRows}
            selectedId={selectedStaffId}
            onSelect={setSelectedStaffId}
            onManageTeam={() => router.push("/home-services/team")}
          />
          {/* The legend belongs to the grid, so it lives in the grid's column and lines
              up with its left edge. Rendered as a page-level sibling it started under
              the roster instead, reading as a footer for the whole page. */}
          <div style={{ flex: 1, minWidth: 0 }}>
          <WeeklyGrid
            technicians={filteredTechnicians.map(t => {
              const s = scheduleFor(t.id, selectedDate);
              const cap = s?.daily_capacity?.limit;
              return {
                id: t.id,
                name: t.full_name,
                // Mirrors the roster's "2/4 jobs" so the two panels read as one row.
                subtitle: cap != null ? `${s?.assignments_today.length ?? 0}/${cap} jobs` : "—",
              };
            })}
            days={days} scheduleFor={scheduleFor}
            selectedStaffId={selectedStaffId}
            onSelectCell={(staffId, date) => { setSelectedStaffId(staffId); setSelectedDate(date); }}
            onSelectJob={jobId => router.push(`/service-jobs/${jobId}`)}
            todayISO={toISODate(new Date())}
          />
          <AvailabilityLegend
            timezone={planner.data?.timezone ?? null}
            // Named from the selected technician's actual break, not a hardcoded
            // "13:00-14:00" -- the design's label is that tenant's break, not a constant.
            breakLabel={selectedSchedule?.break
              ? `${selectedSchedule.break.start}–${selectedSchedule.break.end}`
              : null}
          />
          </div>
          {selectedStaffId && selectedTech && (
            <ScheduleDetailPanel
              staffName={selectedTech.full_name}
              isActive={selectedTech.status === "active"}
              readiness={readiness}
              weeklyPattern={weeklyPattern}
              breakLine={selectedSchedule?.break
                ? `${to12h(selectedSchedule.break.start)} – ${to12h(selectedSchedule.break.end)}`
                : null}
              maxJobsPerDay={selectedSchedule?.daily_capacity?.limit ?? null}
              maxConcurrentJobs={selectedTech.max_concurrent_jobs}
              serviceCapability={selectedTech.supported_services.map(s => s.name)}
              capabilityLoading={false}
              conflict={staffConflict}
              generatedAt={planner.data?.generated_at ?? null}
              onClose={() => setSelectedStaffId(null)}
              onEditAvailability={() => setEditingStaffId(selectedStaffId)}
              overrides={overridesQ.data}
              overridesLoading={overridesQ.loading}
              overridesError={overridesQ.error}
              timeOff={timeOffQ.data}
              timeOffLoading={timeOffQ.loading}
              timeOffError={timeOffQ.error}
              onAddTimeOff={() => setAddingTimeOffFor(selectedStaffId)}
              onCancelTimeOff={id => cancelTimeOff.execute(id)}
              onRemoveOverride={date => removeOverride.execute(date)}
              mutating={cancelTimeOff.loading || removeOverride.loading}
            />
          )}
        </div>
      )}

      {planner.data && <Pagination page={page} pageSize={pageSize} total={planner.data.pagination.total}
        hasNext={planner.data.pagination.has_next} onPage={setPage} itemLabel="technicians" />}

      {editingStaffId && (() => {
        const staff = technicians.find(t => t.id === editingStaffId);
        const d = detail.data && detail.data.staff_id === editingStaffId ? detail.data : null;
        return (
          <DateOverrideDrawer
            staffId={editingStaffId} staffName={staff?.full_name ?? "Technician"}
            dateISO={selectedDate}
            initial={{ start: d?.working_hours?.start ?? null, end: d?.working_hours?.end ?? null }}
            onClose={() => setEditingStaffId(null)}
            onSaved={() => { bumpMutation(); detail.refetch(); }}
          />
        );
      })()}

      {addingTimeOffFor && (
        <AddTimeOffModal
          staffId={addingTimeOffFor}
          staffName={technicians.find(t => t.id === addingTimeOffFor)?.full_name ?? "Technician"}
          defaultDate={selectedDate}
          onClose={() => setAddingTimeOffFor(null)}
          onSaved={() => { bumpMutation(); detail.refetch(); }}
        />
      )}
    </PageShell>
  );
}
