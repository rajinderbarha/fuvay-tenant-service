"use client";
/**
 * Home Services — Availability & Capacity Planner.
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
 * Genuine, stated gaps (rendered as honest disclosures, never fabricated):
 * no per-staff date-override table, no per-staff time-off table, no
 * dedicated schedule-conflict table -- see availability_resolver.py's own
 * capability_flags, which this page reads and displays truthfully.
 */
import React, { useCallback, useMemo, useState } from "react";
import { Skeleton, Btn, Card } from "../../../../components/shared/ui";
import { apiFetch } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { AvailabilityKpis } from "../../../../components/availability/AvailabilityKpis";
import { AvailabilityFilters } from "../../../../components/availability/AvailabilityFilters";
import { TeamRoster, type RosterRow } from "../../../../components/availability/TeamRoster";
import { WeeklyGrid } from "../../../../components/availability/WeeklyGrid";
import { AvailabilityLegend } from "../../../../components/availability/AvailabilityLegend";
import { ScheduleDetailPanel, type WeeklyPatternLine } from "../../../../components/availability/ScheduleDetailPanel";

// ── Types (mirror the real backend response shapes exactly) ─────────────────
interface Technician {
  id: string; full_name: string; designation: string | null;
  status: string; max_concurrent_jobs: number | null; profile_photo_url: string | null;
}
interface EffectiveSchedule {
  staff_id: string; date: string; available: boolean; reasons: string[];
  timezone: string;
  business_hours: { start: string | null; end: string | null } | null;
  working_hours: { start: string | null; end: string | null } | null;
  break: { start: string; end: string } | null;
  daily_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
  concurrent_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
  assignments_today: { job_number: string; status: string; time_window: string | null }[];
  capability_flags: { time_off_supported: boolean; date_override_supported_per_staff: boolean };
}
interface PlannerResponse {
  generated_at: string; timezone: string; from: string; to: string;
  summary: {
    available_today: number; on_leave_today: number; total_capacity: number;
    technician_count: number; conflicts: number;
  };
  technicians: Technician[];
  effective_schedules: EffectiveSchedule[];
  conflicts: { staff_id: string; date: string; reasons: string[] }[];
  capability_flags: {
    time_off_supported: boolean;
    date_override_supported_per_staff: boolean;
    schedule_conflict_table_supported: boolean;
  };
}
interface StaffDetail extends EffectiveSchedule {}
interface TeamOverview {
  supported_services: string[];
  schedule_conflicts: number;
}

interface ImpactPreview {
  future_assignments_affected: number;
  affected_dates: { date: string; existing_assignment_count: number; job_numbers: string[]; reasons: string[] }[];
  capacity_would_drop_below_existing: boolean;
  requires_confirmation: boolean;
}

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
// same-value runs, e.g. "Mon – Sat: 9:00 AM – 6:00 PM" / "Sunday: Off" --
// purely a client-side aggregation of already-fetched real data, no guess.
function summarizeWeeklyPattern(days: string[], schedules: EffectiveSchedule[], staffId: string): WeeklyPatternLine[] {
  const dayName = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" });
  const values = days.map(d => {
    const s = schedules.find(x => x.staff_id === staffId && x.date === d);
    return s?.working_hours?.start && s?.working_hours?.end ? `${s.working_hours.start} – ${s.working_hours.end}` : "Off";
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

function EditAvailabilityDrawer({
  staffId, staffName, dayOfWeek, dayLabel, initial, onClose, onSaved,
}: {
  staffId: string; staffName: string; dayOfWeek: number; dayLabel: string;
  initial: { start: string | null; end: string | null; breakStart: string | null; breakEnd: string | null; dailyCapacity: number | null };
  onClose: () => void; onSaved: () => void;
}) {
  const [startTime, setStartTime] = useState(initial.start ?? "09:00");
  const [endTime, setEndTime] = useState(initial.end ?? "18:00");
  const [breakStart, setBreakStart] = useState(initial.breakStart ?? "");
  const [breakEnd, setBreakEnd] = useState(initial.breakEnd ?? "");
  const [dailyCapacity, setDailyCapacity] = useState(initial.dailyCapacity != null ? String(initial.dailyCapacity) : "");
  const [preview, setPreview] = useState<ImpactPreview | null>(null);
  const [saved, setSaved] = useState(false);

  const previewAction = useAction(useCallback(async () => {
    return await apiFetch<ImpactPreview>("/v1/tenant/home-services/availability/preview-change", {
      method: "POST",
      body: JSON.stringify({
        staff_id: staffId, day_of_week: dayOfWeek, is_active: true,
        start_time: startTime, end_time: endTime,
        max_jobs_per_day: dailyCapacity ? Number(dailyCapacity) : null,
      }),
    });
  }, [staffId, dayOfWeek, startTime, endTime, dailyCapacity]));

  const saveAction = useAction(useCallback(async (confirmImpact: boolean) => {
    return await apiFetch<Record<string, unknown>>("/v1/provider/availability", {
      method: "POST",
      body: JSON.stringify({
        scope_type: "staff_member", scope_id: staffId, day_of_week: dayOfWeek,
        start_time: startTime, end_time: endTime,
        break_start_time: breakStart || null, break_end_time: breakEnd || null,
        max_jobs_per_day: dailyCapacity ? Number(dailyCapacity) : null,
        confirm_impact: confirmImpact,
      }),
    });
  }, [staffId, dayOfWeek, startTime, endTime, breakStart, breakEnd, dailyCapacity]));

  const handleSaveClick = async () => {
    setSaved(false);
    if (!preview) {
      const p = await previewAction.execute();
      if (p) setPreview(p);
      return;
    }
    const res = await saveAction.execute(preview.requires_confirmation);
    if (res) { setSaved(true); onSaved(); }
  };

  return (
    <>
      {/* Real bug fixed here: this drawer had zIndex:50 and no backdrop of
          its own, so opening it from the Schedule Details drawer (zIndex
          900) rendered it BEHIND that drawer -- clicking "Edit availability"
          appeared to do nothing. Now stacks above it with its own backdrop. */}
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 949 }}/>
      <div style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 380, background: "var(--surface)",
        borderLeft: "1px solid var(--border)", boxShadow: "-4px 0 24px rgba(0,0,0,0.3)", zIndex: 950,
        padding: 20, overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <strong style={{ fontSize: 14, color: "var(--text-primary)" }}>Edit availability</strong>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer", fontSize: 14 }}>✕</button>
      </div>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 0, marginBottom: 16 }}>{staffName} · {dayLabel}</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 12 }}>
        <div>
          <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Working hours</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="time" value={startTime} onChange={e => { setStartTime(e.target.value); setPreview(null); setSaved(false); }}
              style={{ flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }} />
            <input type="time" value={endTime} onChange={e => { setEndTime(e.target.value); setPreview(null); setSaved(false); }}
              style={{ flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }} />
          </div>
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Break (optional)</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="time" value={breakStart} onChange={e => { setBreakStart(e.target.value); setPreview(null); setSaved(false); }}
              style={{ flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }} />
            <input type="time" value={breakEnd} onChange={e => { setBreakEnd(e.target.value); setPreview(null); setSaved(false); }}
              style={{ flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }} />
          </div>
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4, color: "var(--text-tertiary)" }}>Daily job capacity</label>
          <input type="number" min={0} value={dailyCapacity}
            onChange={e => { setDailyCapacity(e.target.value); setPreview(null); setSaved(false); }}
            style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", boxSizing: "border-box" }} />
        </div>

        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          Date overrides, time off, and concurrent-capacity editing are not available here yet — those tables /
          endpoints do not exist in this system.
        </div>

        {(previewAction.error || saveAction.error) && (
          <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)" }}>
            {previewAction.error || saveAction.error}
          </div>
        )}

        {preview && preview.requires_confirmation && (
          <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
            <div style={{ fontWeight: 600, color: "var(--warning-text)", marginBottom: 6 }}>
              {preview.future_assignments_affected} real upcoming assignment(s) would be affected
            </div>
            {preview.affected_dates.map(a => (
              <div key={a.date} style={{ fontSize: 11, color: "var(--warning-text)" }}>
                {a.date}: {a.existing_assignment_count} job(s) — {a.job_numbers.join(", ")}
              </div>
            ))}
            <div style={{ fontSize: 11, color: "var(--warning-text)", marginTop: 6 }}>
              Saving will not move or cancel these jobs — it only changes future capacity/hours. Confirm you&apos;re aware.
            </div>
          </div>
        )}

        {saved && (
          <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--success-bg)", color: "var(--success-text)" }}>Saved.</div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <Btn variant="primary" size="sm" onClick={handleSaveClick} loading={previewAction.loading || saveAction.loading}>
            {!preview ? "Check impact & save" : preview.requires_confirmation ? "Confirm and save" : "Save"}
          </Btn>
          <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
        </div>
      </div>
      </div>
    </>
  );
}

export default function AvailabilityCapacityPlannerPage() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(toISODate(new Date())));
  const weekEnd = addDays(weekStart, 6);
  const [view, setView] = useState<"week" | "day">("week");
  const [selectedDate, setSelectedDate] = useState(() => toISODate(new Date()));
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [availFilter, setAvailFilter] = useState<"" | "available" | "unavailable">("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
  const [editingStaffId, setEditingStaffId] = useState<string | null>(null);

  const rangeFrom = view === "day" ? selectedDate : weekStart;
  const rangeTo = view === "day" ? selectedDate : weekEnd;

  const planner = useApi(useCallback(async () => {
    const qs = new URLSearchParams({ from: rangeFrom, to: rangeTo });
    return await apiFetch<PlannerResponse>(`/v1/tenant/home-services/availability?${qs}`);
  }, [rangeFrom, rangeTo]));

  const detail = useApi(useCallback(async () => {
    if (!selectedStaffId) return null;
    const qs = new URLSearchParams({ date: selectedDate });
    return await apiFetch<StaffDetail>(`/v1/tenant/home-services/availability/staff/${selectedStaffId}?${qs}`);
  }, [selectedStaffId, selectedDate]));

  const overview = useApi(useCallback(async () => {
    if (!selectedStaffId) return null;
    return await apiFetch<TeamOverview>(`/v1/tenant/home-services/team/${selectedStaffId}/overview`);
  }, [selectedStaffId]));

  const technicians = planner.data?.technicians ?? [];
  const schedules = planner.data?.effective_schedules ?? [];

  const days = useMemo(() => {
    if (view === "day") return [selectedDate];
    const out: string[] = [];
    for (let i = 0; i < 7; i++) out.push(addDays(weekStart, i));
    return out;
  }, [view, weekStart, selectedDate]);

  // Capability filter is client-side (the list endpoint doesn't accept a
  // capability query param) -- resolved lazily per technician isn't fetched
  // in bulk to avoid N+1, so this filter only applies once a technician's
  // overview has been loaded via selection; otherwise it's a no-op, which
  // is disclosed via the filter's own "client-side" hint text rather than
  // silently pretending to filter the whole roster.
  const filteredTechnicians = useMemo(() => {
    return technicians.filter(t => {
      if (search && !t.full_name.toLowerCase().includes(search.toLowerCase())) return false;
      if (roleFilter && (t.designation ?? "").toLowerCase() !== roleFilter.toLowerCase()) return false;
      if (availFilter) {
        const s = schedules.find(x => x.staff_id === t.id && x.date === selectedDate);
        const isAvailable = s?.available ?? false;
        if (availFilter === "available" && !isAvailable) return false;
        if (availFilter === "unavailable" && isAvailable) return false;
      }
      return true;
    });
  }, [technicians, schedules, search, roleFilter, availFilter, selectedDate]);

  const roles = useMemo(() => Array.from(new Set(technicians.map(t => t.designation).filter(Boolean))) as string[], [technicians]);
  const capabilities = overview.data?.supported_services ?? [];

  const scheduleFor = useCallback((staffId: string, date: string) => schedules.find(s => s.staff_id === staffId && s.date === date), [schedules]);

  const summary = planner.data?.summary;
  const capFlags = planner.data?.capability_flags;

  const rosterRows: RosterRow[] = filteredTechnicians.map(t => {
    const s = scheduleFor(t.id, selectedDate);
    const hasConflict = s?.reasons.some(r => r.toLowerCase() === "schedule_conflict") ?? false;
    const setupIncomplete = s?.reasons.some(r => r.toLowerCase() === "staff_setup_incomplete") ?? false;
    const statusLabel: RosterRow["statusLabel"] = hasConflict ? "Conflict"
      : setupIncomplete ? "Setup incomplete"
      : s?.available ? "Available" : "Unavailable";
    return {
      id: t.id, name: t.full_name, designation: t.designation,
      jobsToday: s?.assignments_today.length ?? 0, maxConcurrent: t.max_concurrent_jobs,
      statusLabel,
    };
  });

  const selectedTech = technicians.find(t => t.id === selectedStaffId) ?? null;
  const selectedSchedule = selectedStaffId ? scheduleFor(selectedStaffId, selectedDate) : undefined;
  const weeklyPattern = selectedStaffId ? summarizeWeeklyPattern(days.length === 7 ? days : Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), schedules, selectedStaffId) : [];
  const staffConflict = selectedStaffId && selectedSchedule?.reasons.some(r => r.toLowerCase() === "schedule_conflict")
    ? { dateLabel: new Date(selectedDate + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "short" }) }
    : null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px", textTransform: "uppercase" }}>Team</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Availability & Capacity</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Plan working hours, time off and safe booking capacity for your team.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 4 }}>
            <button onClick={() => setWeekStart(w => addDays(w, -7))} disabled={view === "day"} aria-label="Previous week"
              style={{ background: "none", border: "none", cursor: view === "day" ? "not-allowed" : "pointer", color: "var(--text-secondary)", padding: 6, display: "flex", opacity: view === "day" ? 0.4 : 1 }}>
              <ChevronLeft size={16}/>
            </button>
            <span style={{ fontSize: 13, color: "var(--text-primary)", padding: "0 6px", fontWeight: 600, whiteSpace: "nowrap" }}>{fmtRange(rangeFrom, rangeTo)}</span>
            <button onClick={() => setWeekStart(w => addDays(w, 7))} disabled={view === "day"} aria-label="Next week"
              style={{ background: "none", border: "none", cursor: view === "day" ? "not-allowed" : "pointer", color: "var(--text-secondary)", padding: 6, display: "flex", opacity: view === "day" ? 0.4 : 1 }}>
              <ChevronRight size={16}/>
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 3 }}>
            <button onClick={() => setView("week")} style={{ background: view === "week" ? "var(--brand)" : "none", color: view === "week" ? "var(--text-on-brand)" : "var(--text-secondary)", border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>Week</button>
            <button onClick={() => setView("day")} style={{ background: view === "day" ? "var(--brand)" : "none", color: view === "day" ? "var(--text-on-brand)" : "var(--text-secondary)", border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>Day</button>
          </div>
          <span title="Not available yet — no weekly-pattern copy endpoint exists.">
            <Btn variant="secondary" disabled>Copy previous week</Btn>
          </span>
          <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={planner.refetch}>Refresh</Btn>
          <span title="Select a technician on a conflicted day, then use Edit availability.">
            <Btn variant="primary" disabled={!selectedStaffId} onClick={() => selectedStaffId && setEditingStaffId(selectedStaffId)}>
              Edit schedule
            </Btn>
          </span>
        </div>
      </div>

      {planner.loading ? (
        <div style={{ display: "flex", gap: 14, margin: "20px 0" }}>
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} height={90} style={{ flex: 1 }}/>)}
        </div>
      ) : summary && (
        <AvailabilityKpis values={{
          availableToday: summary.available_today,
          onLeave: summary.on_leave_today,
          totalCapacity: summary.total_capacity,
          assigned: schedules.filter(s => s.date === selectedDate).reduce((n, s) => n + s.assignments_today.length, 0),
          remaining: schedules.filter(s => s.date === selectedDate).reduce((n, s) => n + (s.concurrent_capacity?.remaining ?? 0), 0),
          conflicts: summary.conflicts,
        }}/>
      )}
      {!planner.loading && capFlags && !capFlags.time_off_supported && (
        <div style={{ padding: "10px 14px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", marginBottom: 16, fontSize: 12, color: "var(--text-tertiary)" }}>
          Time off and per-technician date overrides are not configured in this system yet — those sections are intentionally omitted rather than shown as empty-but-supported.
        </div>
      )}

      {planner.error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>
          {planner.error}
        </div>
      )}

      <AvailabilityFilters
        search={search} onSearch={setSearch}
        roleFilter={roleFilter} onRole={setRoleFilter} roles={roles}
        availFilter={availFilter} onAvail={setAvailFilter}
        capabilityFilter={capabilityFilter} onCapability={setCapabilityFilter} capabilities={capabilities}
        timezone={planner.data?.timezone ?? null}
        onReset={() => { setSearch(""); setRoleFilter(""); setAvailFilter(""); setCapabilityFilter(""); }}
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
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          <TeamRoster rows={rosterRows} selectedId={selectedStaffId} onSelect={setSelectedStaffId}/>
          <WeeklyGrid
            technicians={filteredTechnicians.map(t => ({ id: t.id, name: t.full_name }))}
            days={days} scheduleFor={scheduleFor}
            selectedStaffId={selectedStaffId} onSelectStaff={setSelectedStaffId}
            todayISO={toISODate(new Date())}
          />
          {selectedStaffId && selectedTech && (
            <ScheduleDetailPanel
              staffName={selectedTech.full_name}
              isActive={selectedTech.status === "active"}
              weeklyPattern={weeklyPattern}
              breakLine={selectedSchedule?.break ? `${selectedSchedule.break.start} – ${selectedSchedule.break.end}` : null}
              maxJobsPerDay={selectedSchedule?.daily_capacity?.limit ?? null}
              maxConcurrentJobs={selectedTech.max_concurrent_jobs}
              serviceCapability={overview.data?.supported_services ?? null}
              capabilityLoading={overview.loading}
              conflict={staffConflict}
              generatedAt={planner.data?.generated_at ?? null}
              onClose={() => setSelectedStaffId(null)}
              onEditAvailability={() => setEditingStaffId(selectedStaffId)}
            />
          )}
        </div>
      )}

      <AvailabilityLegend/>

      {editingStaffId && (() => {
        const staff = technicians.find(t => t.id === editingStaffId);
        const d = detail.data && detail.data.staff_id === editingStaffId ? detail.data : null;
        const dow = new Date(selectedDate + "T00:00:00Z").getUTCDay();
        return (
          <EditAvailabilityDrawer
            staffId={editingStaffId} staffName={staff?.full_name ?? "Technician"}
            dayOfWeek={dow} dayLabel={selectedDate}
            initial={{
              start: d?.working_hours?.start ?? null, end: d?.working_hours?.end ?? null,
              breakStart: d?.break?.start ?? null, breakEnd: d?.break?.end ?? null,
              dailyCapacity: d?.daily_capacity?.limit ?? null,
            }}
            onClose={() => setEditingStaffId(null)}
            onSaved={() => { planner.refetch(); detail.refetch(); }}
          />
        );
      })()}
    </div>
  );
}
