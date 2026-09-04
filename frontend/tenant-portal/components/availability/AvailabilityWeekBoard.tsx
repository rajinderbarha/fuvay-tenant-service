"use client";

import React, { useMemo } from "react";
import { X } from "lucide-react";

export interface AvailabilityTechnician {
  id: string;
  full_name: string;
  designation: string | null;
  status: string;
  max_concurrent_jobs: number | null;
  profile_photo_url: string | null;
  member_type: string;
}

export interface AvailabilitySchedule {
  staff_id: string;
  date: string;
  available: boolean;
  reasons: string[];
  working_hours: { start: string | null; end: string | null } | null;
  daily_capacity: { limit: number | null; used?: number; remaining?: number | null } | null;
  assignments_today: Array<{
    job_id: string;
    job_number: string;
    status: string;
    time_window: string | null;
    service_name: string | null;
  }>;
}

interface BoardProps {
  technicians: AvailabilityTechnician[];
  schedules: AvailabilitySchedule[];
  days: string[];
  focusDate: string;
  selectedStaffId: string | null;
  onSelectDay: (staffId: string, date: string) => void;
  onCloseDrawer: () => void;
  onOpenJob: (jobId: string) => void;
}

const LEAVE_REASONS = new Set(["on_time_off", "staff_time_off"]);
const OFF_REASONS = new Set([
  "business_closed",
  "staff_inactive",
  "staff_setup_incomplete",
  "staff_date_override_closed",
  "on_time_off",
  "staff_time_off",
]);

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return `${parts[0][0]}${parts.length > 1 ? parts.at(-1)?.[0] ?? "" : ""}`.toUpperCase();
}

function dayLabel(iso: string): { dow: string; date: string } {
  const date = new Date(`${iso}T00:00:00`);
  const month = date.toLocaleDateString("en-IN", { month: "short" }).toUpperCase();
  return {
    dow: date.toLocaleDateString("en-IN", { weekday: "short" }).toUpperCase(),
    date: `${String(date.getDate()).padStart(2, "0")} ${month === "SEP" ? "SEPT" : month}`,
  };
}

function scheduleIsOff(schedule: AvailabilitySchedule | undefined): boolean {
  if (!schedule) return true;
  const reasons = schedule.reasons.map(reason => reason.toLowerCase());
  return !schedule.available
    && schedule.assignments_today.length === 0
    && reasons.some(reason => OFF_REASONS.has(reason));
}

function scheduleHours(schedule: AvailabilitySchedule | undefined): string {
  const start = schedule?.working_hours?.start;
  const end = schedule?.working_hours?.end;
  return start && end ? `${start}–${end}` : "—";
}

function TechnicianAvatar({ technician }: { technician: AvailabilityTechnician }) {
  return technician.profile_photo_url ? (
    <img className="availability-tech-avatar" src={technician.profile_photo_url} alt="" />
  ) : (
    <span className="availability-tech-avatar is-initials">{initials(technician.full_name)}</span>
  );
}

function AvailabilityKpis({ technicians, schedules, focusDate }: {
  technicians: AvailabilityTechnician[];
  schedules: AvailabilitySchedule[];
  focusDate: string;
}) {
  const focusSchedules = schedules.filter(schedule => schedule.date === focusDate);
  const onDuty = focusSchedules.filter(schedule => !scheduleIsOff(schedule)).length;
  const jobs = schedules.reduce((total, schedule) => total + schedule.assignments_today.length, 0);
  const totalCapacity = schedules.reduce((total, schedule) => total + (schedule.daily_capacity?.limit ?? 0), 0);
  const onLeave = new Set(
    schedules
      .filter(schedule => schedule.reasons.some(reason => LEAVE_REASONS.has(reason.toLowerCase())))
      .map(schedule => schedule.staff_id),
  ).size;
  const values = [
    { label: "On duty today", value: onDuty, note: "technicians working" },
    { label: "Jobs this week", value: jobs, note: "across the team" },
    { label: "Open capacity", value: Math.max(totalCapacity - jobs, 0), note: "slots free to fill" },
    { label: "On leave", value: onLeave, note: "not working this week" },
  ];

  return (
    <div className="availability-kpi-grid">
      {values.map(item => (
        <section className="availability-kpi" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.note}</small>
        </section>
      ))}
    </div>
  );
}

function TechnicianWeekCard({ technician, days, schedules, onSelectDay }: {
  technician: AvailabilityTechnician;
  days: string[];
  schedules: AvailabilitySchedule[];
  onSelectDay: (staffId: string, date: string) => void;
}) {
  const technicianSchedules = days.map(date => schedules.find(schedule => schedule.staff_id === technician.id && schedule.date === date));
  const jobs = technicianSchedules.reduce((total, schedule) => total + (schedule?.assignments_today.length ?? 0), 0);
  const capacity = technicianSchedules.reduce((total, schedule) => total + (schedule?.daily_capacity?.limit ?? 0), 0);
  const worksThisWeek = technicianSchedules.some(schedule => schedule && !scheduleIsOff(schedule));

  return (
    <article className="availability-tech-card">
      <header className="availability-tech-header">
        <TechnicianAvatar technician={technician} />
        <span className="availability-tech-identity">
          <strong>{technician.full_name}</strong>
          <small>{technician.designation ?? "Technician"}</small>
        </span>
        <span className={`availability-status-pill${worksThisWeek ? "" : " is-off"}`}>
          {worksThisWeek ? "Available" : "Unavailable"}
        </span>
        <span className="availability-week-load">
          <strong>{jobs}/{capacity || "—"} jobs</strong>
          <small>jobs this week</small>
        </span>
      </header>

      <div className="availability-days-grid">
        {days.map((date, index) => {
          const schedule = technicianSchedules[index];
          const labels = dayLabel(date);
          const off = scheduleIsOff(schedule);
          const jobsToday = schedule?.assignments_today ?? [];
          const limit = schedule?.daily_capacity?.limit ?? null;
          const full = !off && limit != null && limit > 0 && jobsToday.length >= limit;
          return (
            <button
              type="button"
              className={`availability-day-card${off ? " is-off" : jobsToday.length ? " has-jobs" : " is-available"}${full ? " is-full" : ""}`}
              key={date}
              onClick={() => onSelectDay(technician.id, date)}
            >
              <span className="availability-day-heading"><strong>{labels.dow}</strong><small>{labels.date}</small></span>
              {off ? (
                <><span className="availability-off-copy">Off</span><span className="availability-hours">—</span></>
              ) : (
                <>
                  <span className="availability-hours">{scheduleHours(schedule)}</span>
                  <span className="availability-job-list">
                    {jobsToday.map(job => (
                      <span className="availability-job-chip" key={job.job_id}>
                        {job.time_window ?? "Unscheduled"} {job.service_name ?? job.job_number}
                      </span>
                    ))}
                  </span>
                  <span className="availability-job-count">{jobsToday.length} job{jobsToday.length === 1 ? "" : "s"}</span>
                </>
              )}
            </button>
          );
        })}
      </div>
    </article>
  );
}

function AvailabilityLegend() {
  return (
    <div className="availability-board-legend" aria-label="Availability legend">
      <span><i className="is-available" />Available</span>
      <span><i className="has-jobs" />Has jobs booked</span>
      <span><i className="is-off" />Off</span>
      <span><i className="is-full" />Fully booked</span>
    </div>
  );
}

function AvailabilityDayDrawer({ technician, schedule, date, onClose, onOpenJob }: {
  technician: AvailabilityTechnician;
  schedule: AvailabilitySchedule | undefined;
  date: string;
  onClose: () => void;
  onOpenJob: (jobId: string) => void;
}) {
  const labels = dayLabel(date);
  const off = scheduleIsOff(schedule);
  const jobs = schedule?.assignments_today ?? [];
  const capacity = schedule?.daily_capacity?.limit ?? null;
  const remaining = capacity == null ? null : Math.max(capacity - jobs.length, 0);
  return (
    <>
      <button type="button" className="availability-drawer-backdrop" onClick={onClose} aria-label="Close schedule details" />
      <aside className="availability-day-drawer" aria-label={`Schedule for ${technician.full_name} on ${labels.date}`}>
        <header>
          <span><small>{labels.dow} · {labels.date}</small><strong>{technician.full_name}</strong></span>
          <button type="button" onClick={onClose} aria-label="Close"><X size={15} /></button>
        </header>
        <div className="availability-drawer-body">
          {off ? (
            <div className="availability-day-off">Not scheduled to work this day.</div>
          ) : (
            <>
              <section className="availability-working-hours">
                <small>Working hours</small>
                <strong>{scheduleHours(schedule)}</strong>
              </section>
              <h3>{jobs.length ? `Booked jobs (${jobs.length})` : "No jobs booked yet"}</h3>
              {jobs.map(job => (
                <button type="button" className="availability-drawer-job" key={job.job_id} onClick={() => onOpenJob(job.job_id)}>
                  <strong>{job.time_window ?? "Unscheduled"}</strong>
                  <span>{job.service_name ?? job.job_number}</span>
                </button>
              ))}
              {remaining == null ? (
                <div className="availability-free-capacity">Daily capacity is not configured.</div>
              ) : remaining > 0 ? (
                <div className="availability-free-capacity">{remaining} more job{remaining === 1 ? "" : "s"} could fit today</div>
              ) : null}
            </>
          )}
        </div>
      </aside>
    </>
  );
}

export function AvailabilityWeekBoard({
  technicians,
  schedules,
  days,
  focusDate,
  selectedStaffId,
  onSelectDay,
  onCloseDrawer,
  onOpenJob,
}: BoardProps) {
  const selectedTechnician = technicians.find(technician => technician.id === selectedStaffId);
  const selectedSchedule = selectedTechnician
    ? schedules.find(schedule => schedule.staff_id === selectedTechnician.id && schedule.date === focusDate)
    : undefined;

  const orderedTechnicians = useMemo(
    () => [...technicians].sort((left, right) => left.full_name.localeCompare(right.full_name)),
    [technicians],
  );

  return (
    <div className="availability-board">
      <AvailabilityKpis technicians={technicians} schedules={schedules} focusDate={focusDate} />
      <div className="availability-tech-list">
        {orderedTechnicians.map(technician => (
          <TechnicianWeekCard
            key={technician.id}
            technician={technician}
            days={days}
            schedules={schedules}
            onSelectDay={onSelectDay}
          />
        ))}
      </div>
      {!orderedTechnicians.length && <div className="availability-empty">No technicians are configured for this tenant.</div>}
      <AvailabilityLegend />
      {selectedTechnician && (
        <AvailabilityDayDrawer
          technician={selectedTechnician}
          schedule={selectedSchedule}
          date={focusDate}
          onClose={onCloseDrawer}
          onOpenJob={onOpenJob}
        />
      )}
    </div>
  );
}
