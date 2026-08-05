"use client";
/**
 * Home Services Dispatch Board — read projection + assignment panel over the
 * canonical HomeServiceJobAssignmentService (app/engines/home_service_assignment).
 *
 * This page does NOT select or change the provider business (ServiceOS
 * matching already resolved that when the booking was confirmed), does not
 * compute customer prices, does not create bookings, and does not implement
 * a second assignment engine -- it renders GET /v1/tenant/home-services/dispatch
 * and /jobs/{id}/assignment-options, and calls the EXISTING assign/reassign/
 * cancel-assignment routes at /v1/provider/service-jobs/* for mutations.
 *
 * Scope proven this pass: day view, unassigned-jobs list, technician-schedule
 * timeline (row-per-technician, jobs rendered as blocks), assignment panel
 * with eligible + excluded technicians (real exclusion reason codes from the
 * backend), assign/reassign/unassign actions, manual refresh. NOT built this
 * pass: drag-and-drop, week view, auto-assignment (none exists canonically to
 * reuse), true real-time push (bounded manual refresh only) -- see the
 * session's final report for the complete disclosure.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronLeft, ChevronRight, RefreshCw, AlertTriangle, CheckCircle2,
  User as UserIcon, X, Info, CalendarDays, Truck, Users as UsersIcon,
} from "lucide-react";
import { Card, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import {
  homeServicesDispatchApi, ServiceOSError,
  type HsDispatchProjection, type HsDispatchJobSummary, type HsAssignmentOptions,
  type HsAssignmentOptionTechnician,
} from "../../../../lib/api";

const BOARD_START_HOUR = 9;
const BOARD_END_HOUR = 18;
const HOUR_LABELS = Array.from({ length: BOARD_END_HOUR - BOARD_START_HOUR + 1 }, (_, i) => {
  const h = BOARD_START_HOUR + i;
  return h === 12 ? "12 PM" : h > 12 ? `${h - 12} PM` : `${h} AM`;
});

/** Best-effort parse of a free-form scheduled_time_window into an hour range
 * within the board's 9AM-6PM window. Returns null (not fabricated) when the
 * label can't be honestly resolved to a time -- those jobs render in a
 * separate "Unscheduled time" strip instead of a fake position. */
function parseTimeWindow(label: string | null): { startHour: number; endHour: number } | null {
  if (!label) return null;
  const rangeMatch = label.match(/(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)/i);
  if (rangeMatch) {
    const to24 = (h: string, m: string | undefined, ap: string) => {
      let hour = parseInt(h, 10) % 12;
      if (/pm/i.test(ap)) hour += 12;
      return hour + (m ? parseInt(m, 10) / 60 : 0);
    };
    const start = to24(rangeMatch[1], rangeMatch[2], rangeMatch[3]);
    const end = to24(rangeMatch[4], rangeMatch[5], rangeMatch[6]);
    if (end > start) return { startHour: start, endHour: end };
  }
  const lower = label.toLowerCase();
  if (lower === "morning") return { startHour: 9, endHour: 12 };
  if (lower === "afternoon") return { startHour: 12, endHour: 15 };
  if (lower === "evening") return { startHour: 15, endHour: 18 };
  return null;
}

/** Renders a parsed hour range (e.g. {startHour:9, endHour:12}) as "9:00 AM – 12:00 PM".
 * Only ever called on ranges parseTimeWindow already resolved -- never invents a time. */
function fmtHourRange(startHour: number, endHour: number): string {
  const fmt = (h: number) => {
    const totalMin = Math.round(h * 60);
    const hh24 = Math.floor(totalMin / 60);
    const mm = totalMin % 60;
    const ap = hh24 >= 12 ? "PM" : "AM";
    const hh12 = hh24 % 12 === 0 ? 12 : hh24 % 12;
    return `${hh12}:${String(mm).padStart(2, "0")} ${ap}`;
  };
  return `${fmt(startHour)} – ${fmt(endHour)}`;
}

function todayISO(): string {
  // Local calendar date, never round-tripped through UTC -- toISOString()
  // converts to UTC first, which silently shifts the date near local
  // midnight for any timezone ahead of UTC (e.g. IST, UTC+5:30).
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" });
}

const MATCH_REASON_LABELS: Record<string, string> = {
  same_tenant: "Same business",
  active: "Active",
  technician: "Technician",
};

const EXCLUSION_LABELS: Record<string, string> = {
  STAFF_INACTIVE: "Inactive",
  STAFF_NOT_VERIFIED: "Not verified",
  JOB_TYPE_UNSUPPORTED: "Job type unsupported",
  TYPE_UNSUPPORTED: "Equipment type unsupported",
  BRAND_UNSUPPORTED: "Brand unsupported",
  OUTSIDE_AVAILABILITY: "No availability configured",
  SCHEDULE_CONFLICT: "Schedule conflict",
  CAPACITY_EXCEEDED: "Capacity exceeded",
  OUTSIDE_COVERAGE: "Outside coverage area",
  TENANT_MISMATCH: "Different tenant",
};

export default function DispatchBoardPage() {
  // Dark-by-default on first visit is already the app's real behavior --
  // app/layout.tsx's ThemeProvider has defaultPreference="dark" and its
  // inline bootstrap script defaults data-theme to "dark" whenever
  // localStorage["serviceos-theme"] is unset. No page-level override is
  // needed (and hooks/useTheme.ts must NOT be used here -- it reads/writes
  // a different, disconnected "serviceos-tenant-theme" key that has no
  // effect on the real rendered theme; wiring it in this page briefly
  // caused it to fight with and clobber the real ThemeProvider's value).
  const [date, setDate] = useState(todayISO());
  const [view, setView] = useState<"day" | "week">("day");
  const [board, setBoard] = useState<HsDispatchProjection | null>(null);

  /**
   * Order the queue by how soon each job is DUE, most urgent first.
   *
   * The customer is given a promised slot at booking time, so "which job is
   * closest to breaking its promise" is the only ordering that matters here;
   * arrival order is not it. Jobs with no recorded commitment
   * (`minutes_until_due === null`) sort last rather than being treated as
   * urgent -- the backend is explicit that null means "no commitment
   * recorded", never "due now".
   */
  const unassignedByUrgency = useMemo(() => {
    const jobs = board?.unassigned_jobs ?? [];
    return [...jobs].sort((a, b) => {
      const am = a.minutes_until_due ?? null;
      const bm = b.minutes_until_due ?? null;
      if (am === null && bm === null) return 0;
      if (am === null) return 1;
      if (bm === null) return -1;
      return am - bm;
    });
  }, [board]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ code?: string; message: string } | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [options, setOptions] = useState<HsAssignmentOptions | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    homeServicesDispatchApi.getDispatchBoard(date)
      .then(d => { setBoard(d); setLastUpdated(new Date()); })
      .catch((e: unknown) => {
        if (e instanceof ServiceOSError) {
          setError({ code: e.code, message: e.message });
        } else {
          setError({ message: "We couldn't load the dispatch board." });
        }
      })
      .finally(() => setLoading(false));
  }, [date]);

  useEffect(() => { load(); }, [load]);

  const loadOptions = useCallback((jobId: string) => {
    setSelectedJobId(jobId);
    setOptions(null);
    setOptionsError(null);
    setShowExcluded(false);
    setOptionsLoading(true);
    homeServicesDispatchApi.getAssignmentOptions(jobId)
      .then(setOptions)
      .catch((e: unknown) => setOptionsError(e instanceof ServiceOSError ? e.message : "Could not load assignment options."))
      .finally(() => setOptionsLoading(false));
  }, []);

  async function handleAssign(staffMemberId: string) {
    if (!selectedJobId || !options) return;
    setAssigning(staffMemberId);
    try {
      const hasCurrent = !!options.current_assignment;
      if (hasCurrent) {
        await homeServicesDispatchApi.reassign(selectedJobId, staffMemberId, "Reassigned from Dispatch Board");
      } else {
        await homeServicesDispatchApi.assign(
          selectedJobId, staffMemberId,
          options.job_context.scheduled_date ?? undefined,
          options.job_context.scheduled_time_window ?? undefined,
        );
      }
      load();
      loadOptions(selectedJobId);
    } catch (e) {
      setOptionsError(e instanceof ServiceOSError ? e.message : "Assignment failed.");
    } finally {
      setAssigning(null);
    }
  }

  async function handleUnassign() {
    if (!selectedJobId) return;
    setAssigning("unassign");
    try {
      await homeServicesDispatchApi.unassign(selectedJobId, "Unassigned from Dispatch Board");
      load();
      loadOptions(selectedJobId);
    } catch (e) {
      setOptionsError(e instanceof ServiceOSError ? e.message : "Could not unassign this job.");
    } finally {
      setAssigning(null);
    }
  }

  const summary = board?.summary;

  return (
    <div style={{ padding: 24, maxWidth: 1800, margin: "0 auto" }}>
      <style>{`
        .db-kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin: 20px 0; }
        @media (max-width: 1100px) { .db-kpis { grid-template-columns: repeat(2, 1fr); } }
        .db-workspace { display: grid; grid-template-columns: 320px minmax(0, 1fr) 360px; gap: 16px; align-items: start; }
        @media (max-width: 1500px) { .db-workspace { grid-template-columns: 280px minmax(0, 1fr); } .db-panel-col { grid-column: 1 / -1; } }
        @media (max-width: 900px) { .db-workspace { grid-template-columns: 1fr; } .db-panel-col { grid-column: auto; } }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Dispatch board</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Assign eligible technicians and manage today&apos;s schedule.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 4 }}>
            <button onClick={() => setDate(d => shiftDate(d, -1))} aria-label="Previous day"
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 6, display: "flex" }}>
              <ChevronLeft size={16}/>
            </button>
            <button onClick={() => setDate(todayISO())}
              style={{ background: date === todayISO() ? "var(--brand)" : "none", color: date === todayISO() ? "var(--text-on-brand)" : "var(--text-primary)",
                border: "none", borderRadius: 6, padding: "5px 10px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
              Today
            </button>
            <span style={{ fontSize: 13, color: "var(--text-primary)", padding: "0 6px", fontWeight: 600 }}>{fmtDate(date)}</span>
            <button onClick={() => setDate(d => shiftDate(d, 1))} aria-label="Next day"
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", padding: 6, display: "flex" }}>
              <ChevronRight size={16}/>
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 3 }}>
            <button onClick={() => setView("day")}
              style={{ background: view === "day" ? "var(--brand)" : "none", color: view === "day" ? "var(--text-on-brand)" : "var(--text-secondary)",
                border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
              Day
            </button>
            <button onClick={() => setView("week")}
              style={{ background: view === "week" ? "var(--brand)" : "none", color: view === "week" ? "var(--text-on-brand)" : "var(--text-secondary)",
                border: "none", borderRadius: 7, padding: "6px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
              Week
            </button>
          </div>
          <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Refresh</Btn>
          <Btn variant="primary">Review unassigned</Btn>
        </div>
      </div>

      {lastUpdated && (
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
          Last updated {lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
        </p>
      )}

      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)",
          border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginTop: 16 }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
          <span>
            {error.code === "VERTICAL_DISABLED" || error.code === "TENANT_VERTICAL_NOT_ACTIVE"
              ? "Home Services is not active for your account yet -- the Dispatch Board unlocks once your enrollment is approved."
              : error.message}
          </span>
        </div>
      )}

      {/* KPI cards */}
      {loading ? (
        <div className="db-kpis">{[0,1,2,3,4].map(i => <Skeleton key={i} height={90}/>)}</div>
      ) : summary && (
        <div className="db-kpis">
          <KpiCard label="Unassigned" value={summary.unassigned_count} icon={<UserIcon size={18}/>} variant="default" />
          <KpiCard label="Scheduled" value={summary.scheduled_count} icon={<CalendarDays size={18}/>} variant="success" />
          <KpiCard label="On the way" value={summary.on_the_way_count} icon={<Truck size={18}/>} variant="info" />
          <KpiCard label="Capacity" value={`${summary.capacity_used}/${summary.capacity_total}`} icon={<UsersIcon size={18}/>} variant="warning" />
          <KpiCard label="Conflicts" value={summary.conflict_count} icon={<AlertTriangle size={18}/>} variant={summary.conflict_count > 0 ? "danger" : "default"} />
        </div>
      )}

      {view === "week" && !loading && (
        <Card style={{ marginTop: 4 }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", textAlign: "center", padding: "40px 0" }}>
            Week view isn&apos;t built yet -- no canonical week-level projection exists to reuse.
            Switch back to Day to work the schedule.
          </p>
        </Card>
      )}

      {/* Workspace */}
      {view === "day" && loading ? (
        <div className="db-workspace" style={{ marginTop: 4 }}>
          <Skeleton height={520}/><Skeleton height={520}/>
        </div>
      ) : (view === "day" && board) && (
        <div className="db-workspace">
          {/* Unassigned jobs */}
          <Card padding={0}>
            <div style={{ padding: "16px 16px 10px" }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Unassigned jobs</h3>
            </div>
            <div style={{ maxHeight: 640, overflowY: "auto" }}>
              {board.unassigned_jobs.length === 0 && (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: 16 }}>No unassigned jobs today.</p>
              )}
              {unassignedByUrgency.map(job => (
                <UnassignedJobCard key={job.job_id} job={job} selected={job.job_id === selectedJobId}
                  onClick={() => loadOptions(job.job_id)} />
              ))}
            </div>
            <div style={{ padding: 12, borderTop: "1px solid var(--border)", fontSize: 11.5, color: "var(--text-tertiary)" }}>
              Showing {board.unassigned_jobs.length} of {board.unassigned_jobs.length} jobs
            </div>
          </Card>

          {/* Technician schedule — hourly timeline (9 AM - 6 PM) */}
          <Card padding={0}>
            <div style={{ padding: "16px 16px 10px" }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Technicians</h3>
            </div>
            <div style={{ maxHeight: 640, overflowY: "auto", overflowX: "auto" }}>
              {board.technician_schedule.length === 0 && (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: 16 }}>No technicians configured for this tenant.</p>
              )}
              {board.technician_schedule.length > 0 && (
                <div style={{ minWidth: 760 }}>
                  {/* Hour header */}
                  <div style={{ display: "grid", gridTemplateColumns: `140px repeat(${HOUR_LABELS.length - 1}, 1fr)`, borderBottom: "1px solid var(--border)" }}>
                    <div/>
                    {HOUR_LABELS.slice(0, -1).map(h => (
                      <div key={h} style={{ fontSize: 10.5, color: "var(--text-tertiary)", padding: "8px 4px", textAlign: "center" }}>{h}</div>
                    ))}
                  </div>
                  {board.technician_schedule.map(t => {
                    const positioned = t.jobs_today.map(j => ({ job: j, slot: parseTimeWindow(j.scheduled_time_window) }));
                    const unscheduled = positioned.filter(p => !p.slot).map(p => p.job);
                    const onGrid = positioned.filter(p => !!p.slot) as { job: HsDispatchJobSummary; slot: { startHour: number; endHour: number } }[];
                    // Real conflict: two on-grid jobs whose hour ranges overlap.
                    const hasConflict = onGrid.some((a, i) => onGrid.some((b, j) =>
                      i !== j && a.slot.startHour < b.slot.endHour && b.slot.startHour < a.slot.endHour));
                    return (
                      <div key={t.staff_member_id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", alignItems: "center", minHeight: 56 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px" }}>
                            <div style={{ width: 30, height: 30, borderRadius: "50%", background: "var(--accent-muted)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--accent)", fontWeight: 700, fontSize: 11.5 }}>
                              {t.name.slice(0, 2).toUpperCase()}
                            </div>
                            <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name}</p>
                          </div>
                          <div style={{ position: "relative", height: "100%", minHeight: 56 }}>
                            {hasConflict ? (
                              <div style={{ position: "absolute", inset: "6px 8px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
                                borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                                <AlertTriangle size={13} style={{ color: "var(--danger-text)" }}/>
                                <span style={{ fontSize: 11.5, fontWeight: 600, color: "var(--danger-text)" }}>Schedule conflict</span>
                              </div>
                            ) : onGrid.length === 0 && t.status === "active" ? (
                              <div style={{ position: "absolute", inset: "6px 8px", background: "var(--success-bg)", border: "1px solid var(--success-border)",
                                borderRadius: 8, display: "flex", alignItems: "center", paddingLeft: 12 }}>
                                <span style={{ fontSize: 11.5, fontWeight: 600, color: "var(--success-text)" }}>Available</span>
                              </div>
                            ) : onGrid.length === 0 ? (
                              <div style={{ position: "absolute", inset: "6px 8px", background: "var(--surface-sunken)", border: "1px solid var(--border)",
                                borderRadius: 8, display: "flex", alignItems: "center", paddingLeft: 12 }}>
                                <span style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-tertiary)" }}>{t.status}</span>
                              </div>
                            ) : (
                              onGrid.map(({ job, slot }) => {
                                const left = Math.max(0, (slot.startHour - BOARD_START_HOUR) / (BOARD_END_HOUR - BOARD_START_HOUR) * 100);
                                const width = Math.min(100 - left, (slot.endHour - slot.startHour) / (BOARD_END_HOUR - BOARD_START_HOUR) * 100);
                                return (
                                  <button key={job.job_id} onClick={() => loadOptions(job.job_id)}
                                    style={{ position: "absolute", top: 6, bottom: 6, left: `${left}%`, width: `${Math.max(width, 8)}%`,
                                      background: job.job_id === selectedJobId ? "var(--accent-muted)" : "var(--success-bg)",
                                      border: `1px solid ${job.job_id === selectedJobId ? "var(--brand)" : "var(--success-border)"}`,
                                      borderRadius: 8, padding: "4px 8px", cursor: "pointer", textAlign: "left", overflow: "hidden" }}>
                                    <p style={{ fontSize: 11, fontWeight: 600, color: "var(--success-text)", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{job.job_number}</p>
                                    <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                      {job.master_service_name ?? "Service"}
                                    </p>
                                    <p style={{ fontSize: 9.5, color: "var(--success-text)", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", opacity: 0.85 }}>
                                      {fmtHourRange(slot.startHour, slot.endHour)}
                                    </p>
                                  </button>
                                );
                              })
                            )}
                          </div>
                        </div>
                        {unscheduled.length > 0 && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", padding: "0 12px 10px 152px" }}>
                            {unscheduled.map(j => (
                              <button key={j.job_id} onClick={() => loadOptions(j.job_id)}
                                style={{ fontSize: 10.5, color: "var(--success-text)", background: "var(--success-bg)",
                                  border: "1px solid var(--success-border)", borderRadius: 6, padding: "3px 8px", cursor: "pointer" }}>
                                {j.job_number} · {j.scheduled_time_window ?? "time TBD"}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Card>

          {/* Assignment panel — persistent third column, matching the
              reference layout (not a modal overlay) */}
          <Card padding={0} style={{ position: "sticky", top: 24 }}>
            <div className="db-panel-col" style={{ padding: 20, maxHeight: 700, overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Assign technician</h3>
              {selectedJobId && (
                <button onClick={() => setSelectedJobId(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
                  <X size={18}/>
                </button>
              )}
            </div>

            {!selectedJobId && (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 16 }}>
                Select an unassigned job, or a scheduled job on a technician&apos;s row, to view or change its assignment.
              </p>
            )}

            {selectedJobId && optionsLoading && <Skeleton height={300}/>}

            {optionsError && (
              <div role="alert" style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--danger-bg)",
                border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 12.5, marginBottom: 12 }}>
                <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }}/><span>{optionsError}</span>
              </div>
            )}

            {options && (
              <>
                <div style={{ marginBottom: 4 }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", margin: "0 0 2px" }}>{options.job_context.job_number}</p>
                  <h4 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>
                    {options.job_context.master_service_name ?? "Service job"}
                  </h4>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12.5, marginBottom: 16 }}>
                  <DetailRow label="Requested" value={options.job_context.scheduled_time_window ?
                    `${options.job_context.scheduled_date ?? ""} · ${options.job_context.scheduled_time_window}` : "—"} />
                  <DetailRow label="Location" value={options.job_context.city ?? "—"} />
                  <DetailRow label="Customer" value={options.job_context.customer_name ?? "—"} />
                  <DetailRow label="Issue" value={options.job_context.issue_summary ?? "—"} />
                </div>

                {options.current_assignment && (
                  <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--info-bg)", border: "1px solid var(--info-border)",
                    fontSize: 12.5, color: "var(--info-text)", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span>Currently assigned</span>
                    <button onClick={handleUnassign} disabled={assigning === "unassign"}
                      style={{ background: "none", border: "none", color: "var(--danger-text)", fontWeight: 600, fontSize: 12, cursor: "pointer" }}>
                      {assigning === "unassign" ? "Unassigning…" : "Unassign"}
                    </button>
                  </div>
                )}

                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 10px" }}>
                  Eligible technicians
                </p>
                {options.eligible_technicians.length === 0 && (
                  <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 16 }}>No eligible technicians for this job right now.</p>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                  {options.eligible_technicians.map(t => (
                    <TechnicianRow key={t.staff_member_id} t={t}
                      actionLabel={assigning === t.staff_member_id ? "Assigning…" : "Assign"}
                      disabled={!!assigning}
                      onAssign={() => handleAssign(t.staff_member_id)} />
                  ))}
                </div>

                <button onClick={() => setShowExcluded(s => !s)}
                  style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer",
                    color: "var(--text-tertiary)", fontSize: 12, fontWeight: 600, padding: 0, marginBottom: 10 }}>
                  <Info size={13}/> {showExcluded ? "Hide" : "Show"} excluded technicians ({options.excluded_technicians.length})
                </button>
                {showExcluded && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {options.excluded_technicians.map(t => (
                      <div key={t.staff_member_id} style={{ padding: "10px 12px", borderRadius: 8, border: "1px solid var(--border)", opacity: 0.75 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{t.name}</p>
                          <Badge variant="danger" size="sm">Excluded</Badge>
                        </div>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {(t.exclusion_reason_codes ?? []).map(code => (
                            <span key={code} style={{ fontSize: 10.5, color: "var(--danger-text)", background: "var(--danger-bg)",
                              border: "1px solid var(--danger-border)", borderRadius: 6, padding: "2px 6px" }}>
                              {EXCLUSION_LABELS[code] ?? code}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

              </>
            )}

            <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 20, display: "flex", alignItems: "center", gap: 6 }}>
              <Info size={12}/> Provider business already matched by ServiceOS.
            </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function shiftDate(iso: string, days: number): string {
  // Pure UTC calendar arithmetic on the Y/M/D components -- never
  // reconstruct via local midnight + toISOString(), which round-trips
  // through UTC and silently cancels out the shift in timezones ahead of
  // UTC (see todayISO() for the same fix).
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt.toISOString().slice(0, 10);
}

function KpiCard({ label, value, icon, variant = "default" }: {
  label: string; value: string | number; icon?: React.ReactNode;
  variant?: "default" | "success" | "info" | "warning" | "danger";
}) {
  const colors: Record<string, { fg: string; bg: string }> = {
    default: { fg: "var(--text-secondary)", bg: "var(--surface-sunken)" },
    success: { fg: "var(--success-text)", bg: "var(--success-bg)" },
    info:    { fg: "var(--info-text)",    bg: "var(--info-bg)" },
    warning: { fg: "var(--warning-text)", bg: "var(--warning-bg)" },
    danger:  { fg: "var(--danger-text)",  bg: "var(--danger-bg)" },
  };
  const c = colors[variant];
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        {icon && (
          <span style={{ width: 32, height: 32, borderRadius: "50%", background: c.bg, color: c.fg,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            {icon}
          </span>
        )}
        <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0, fontWeight: 600 }}>{label}</p>
      </div>
      <p style={{ fontSize: 28, fontWeight: 800, color: c.fg, margin: 0 }}>{value}</p>
    </Card>
  );
}

/**
 * The SLA badge for a job awaiting a technician.
 *
 * The booking flow PROMISES the customer a slot up front -- there is no wait
 * window, and the clock starts when the request is created. The backend has
 * always returned `service_due_at` / `minutes_until_due` / `is_overdue` on
 * the assignable-jobs queue, but nothing in this portal displayed them, so a
 * provider had no way to see which promise was about to be broken. This is
 * that missing surface.
 *
 * `minutes_until_due` is null on legacy jobs that carry no slot; per the
 * backend's own contract that means "no commitment recorded" and must never
 * be rendered as "due now", so nothing is shown at all in that case.
 */
function SlaBadge({ job }: { job: HsDispatchJobSummary }) {
  const mins: number | null = job.minutes_until_due ?? null;
  if (mins === null) return null;

  const overdue = Boolean(job.is_overdue);
  const abs = Math.abs(mins);
  const label = abs >= 60
    ? `${Math.floor(abs / 60)}h ${abs % 60}m`
    : `${abs}m`;

  // Under an hour left is the point where a provider still has time to act.
  const urgent = !overdue && mins <= 60;
  const tone = overdue
    ? { bg: "var(--danger-bg)", fg: "var(--danger-text)", border: "var(--danger-border)" }
    : urgent
      ? { bg: "var(--warning-bg)", fg: "var(--warning-text)", border: "var(--warning-border)" }
      : { bg: "var(--surface-sunken)", fg: "var(--text-tertiary)", border: "var(--border)" };

  return (
    <span
      title={job.service_due_at ? `Due ${new Date(job.service_due_at).toLocaleString("en-IN")}` : undefined}
      style={{
        fontSize: 10.5, fontWeight: 700, padding: "2px 7px", borderRadius: 999,
        background: tone.bg, color: tone.fg, border: `1px solid ${tone.border}`,
        whiteSpace: "nowrap",
      }}
    >
      {overdue ? `${label} overdue` : `${label} left`}
    </span>
  );
}

function UnassignedJobCard({ job, selected, onClick }: {
  job: HsDispatchJobSummary; selected: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      display: "block", width: "100%", textAlign: "left", padding: "14px 16px",
      background: selected ? "var(--accent-muted)" : "transparent",
      border: "none", borderLeft: selected ? "3px solid var(--brand)" : "3px solid transparent",
      borderBottom: "1px solid var(--border)", cursor: "pointer",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", margin: 0 }}>{job.job_number}</p>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <SlaBadge job={job} />
          {job.scheduled_time_window && <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>{job.scheduled_time_window}</p>}
        </div>
      </div>
      <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
        {job.master_service_name ?? "Service"}
      </p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 4px" }}>{job.customer_name ?? "—"}</p>
      <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>{job.city ?? "—"}</p>
    </button>
  );
}

function TechnicianRow({ t, onAssign, actionLabel, disabled }: {
  t: HsAssignmentOptionTechnician; onAssign: () => void; actionLabel: string; disabled: boolean;
}) {
  const reasons = (t.match_reasons ?? []).map(r => MATCH_REASON_LABELS[r] ?? r);
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "10px 12px",
      borderRadius: 8, border: "1px solid var(--success-border)", background: "var(--success-bg)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--accent-muted)", color: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontWeight: 700, fontSize: 12,
          position: "relative" }}>
          {t.name.slice(0, 2).toUpperCase()}
          <span style={{ position: "absolute", bottom: -1, right: -1, width: 9, height: 9, borderRadius: "50%",
            background: "var(--success-text)", border: "2px solid var(--success-bg)" }}/>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <p style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name}</p>
            <CheckCircle2 size={13} style={{ color: "var(--success-text)", flexShrink: 0 }}/>
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {reasons.length > 0 ? `Eligible · ${reasons.join(" · ")}` : "Eligible"}
          </p>
        </div>
      </div>
      <Btn variant="primary" size="sm" disabled={disabled} onClick={onAssign}>{actionLabel}</Btn>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0, fontWeight: 500 }}>{value}</p>
    </div>
  );
}
