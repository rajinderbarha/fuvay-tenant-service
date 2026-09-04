"use client";

import React from "react";
import { CalendarClock, ChevronLeft, ChevronRight, UserRoundCheck, UserRoundX } from "lucide-react";
import type {
  HsDispatchJobSummary,
  HsDispatchProjection,
  HsDispatchTechnician,
} from "../../lib/api";

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase() || "TM";
}

function serviceLabel(job: HsDispatchJobSummary) {
  return job.master_service_name || job.issue_summary || "Service job";
}

function slotLabel(job: HsDispatchJobSummary) {
  return job.scheduled_time_window || job.requested_time_window || "Time pending";
}

function urgency(job: HsDispatchJobSummary) {
  if (job.is_overdue) return { label: `${Math.abs(job.minutes_until_due ?? 0)}m overdue`, tone: "danger" };
  if (job.minutes_until_due != null && job.minutes_until_due <= 120) return { label: `${Math.max(0, job.minutes_until_due)}m left`, tone: "warning" };
  return { label: "On track", tone: "success" };
}

function jobsForDay(technician: HsDispatchTechnician, date: string) {
  const jobs = technician.jobs_today?.length ? technician.jobs_today : technician.jobs_in_range;
  return jobs.filter(job => !job.scheduled_date || job.scheduled_date === date);
}

export function DispatchDateNavigator({
  dateLabel,
  onPrevious,
  onNext,
}: {
  dateLabel: string;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return <div className="tenant-dispatch-date-nav" aria-label="Dispatch date">
    <button type="button" aria-label="Previous day" onClick={onPrevious}><ChevronLeft size={15} /></button>
    <span>{dateLabel}</span>
    <button type="button" aria-label="Next day" onClick={onNext}><ChevronRight size={15} /></button>
  </div>;
}

function DispatchKpis({ board }: { board: HsDispatchProjection }) {
  const techniciansOnDuty = board.technician_schedule.filter(technician => technician.status !== "inactive" && technician.status !== "offboarded").length;
  const cards = [
    { label: "Unassigned", value: board.summary.unassigned_count, note: "need a technician", icon: <UserRoundX size={15} />, tone: "warning" },
    { label: "Scheduled today", value: board.summary.scheduled_count, note: "assigned visits", icon: <CalendarClock size={15} />, tone: "neutral" },
    { label: "Technicians on duty", value: techniciansOnDuty, note: "available to assign", icon: <UserRoundCheck size={15} />, tone: "neutral" },
  ];
  return <section className="tenant-dispatch-kpis" aria-label="Dispatch summary">
    {cards.map(card => <div className="tenant-dispatch-kpi" data-tone={card.tone} key={card.label}>
      <span className="tenant-dispatch-kpi-label"><span>{card.label}</span><i>{card.icon}</i></span>
      <strong>{card.value}</strong>
      <small>{card.note}</small>
    </div>)}
  </section>;
}

function UnassignedJobCard({ job, selected, onSelect }: {
  job: HsDispatchJobSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const due = urgency(job);
  return <button type="button" className="tenant-dispatch-unassigned-card" aria-current={selected} onClick={onSelect}>
    <span className="tenant-dispatch-job-top"><strong>{job.job_number}</strong><i data-tone={due.tone}>{due.label}</i></span>
    <b>{serviceLabel(job)}</b>
    <span>{job.customer_alias || "Private customer"}{job.locality ? ` · ${job.locality}` : ""}</span>
    <span className="tenant-dispatch-job-foot"><code>{slotLabel(job)}</code><em>Assign →</em></span>
  </button>;
}

function TechnicianCard({ technician, date, selectedJobId, onSelect }: {
  technician: HsDispatchTechnician;
  date: string;
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
}) {
  const jobs = jobsForDay(technician, date);
  const capacityLimit = Math.max(technician.capacity_limit ?? jobs.length, jobs.length);
  const capacityUsed = technician.capacity_used ?? jobs.length;
  const openSlots = Math.max(0, capacityLimit - capacityUsed);
  const specialties = Array.from(new Set(jobs.map(serviceLabel))).slice(0, 2).join(" · ") || "Ready for assignment";
  return <article className="tenant-dispatch-technician">
    <header>
      <span className="tenant-dispatch-avatar">
        {technician.profile_photo_url ? <img src={technician.profile_photo_url} alt="" /> : initials(technician.name)}
      </span>
      <span className="tenant-dispatch-technician-name"><strong>{technician.name}</strong><small>{specialties}</small></span>
      <span className="tenant-dispatch-capacity">{capacityUsed}/{capacityLimit} jobs</span>
    </header>
    <div className="tenant-dispatch-slots">
      {jobs.map(job => <button type="button" key={job.job_id} aria-current={selectedJobId === job.job_id} onClick={() => onSelect(job.job_id)}>
        <strong>{slotLabel(job)}</strong><span>{serviceLabel(job)}</span>
      </button>)}
      {openSlots > 0 && <span className="tenant-dispatch-open-slot">+ {openSlots} open slot{openSlots === 1 ? "" : "s"}</span>}
      {!jobs.length && !openSlots && <span className="tenant-dispatch-open-slot">No capacity configured</span>}
    </div>
  </article>;
}

export function TenantDispatchBoard({
  board,
  date,
  selectedJobId,
  onSelectJob,
}: {
  board: HsDispatchProjection;
  date: string;
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
}) {
  return <div className="tenant-dispatch-reference">
    <DispatchKpis board={board} />

    {board.unassigned_jobs.length > 0 && <section className="tenant-dispatch-section tenant-dispatch-needs">
      <header><h2><i />Needs a technician</h2><span>{board.pagination.total || board.unassigned_jobs.length} waiting</span></header>
      <div className="tenant-dispatch-unassigned-grid">
        {board.unassigned_jobs.map(job => <UnassignedJobCard key={job.job_id} job={job} selected={selectedJobId === job.job_id} onSelect={() => onSelectJob(job.job_id)} />)}
      </div>
    </section>}

    <section className="tenant-dispatch-section tenant-dispatch-today">
      <header><h2>Technicians today</h2><p>Tap a technician&apos;s job to see details, or an open slot after selecting a job.</p></header>
      <div className="tenant-dispatch-technician-list">
        {board.technician_schedule.map(technician => <TechnicianCard key={technician.staff_member_id} technician={technician} date={date} selectedJobId={selectedJobId} onSelect={onSelectJob} />)}
        {!board.technician_schedule.length && <div className="tenant-dispatch-empty">No technicians are on duty for this date.</div>}
      </div>
    </section>

    <style>{`
      .tenant-dispatch-reference{display:flex;flex-direction:column;gap:22px}
      .tenant-dispatch-date-nav{display:flex;align-items:center;gap:8px}.tenant-dispatch-date-nav button{display:grid;place-items:center;width:38px;height:38px;border:1px solid var(--border);border-radius:11px;background:var(--surface);color:var(--text-secondary);cursor:pointer}.tenant-dispatch-date-nav span{height:38px;padding:0 14px;border-radius:11px;background:var(--accent-muted);color:var(--brand);font-size:13px;font-weight:700;line-height:38px;white-space:nowrap}
      .tenant-dispatch-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.tenant-dispatch-kpi{display:flex;min-height:109px;flex-direction:column;gap:10px;padding:13px;border:1px solid var(--border);border-radius:15px;background:var(--surface)}.tenant-dispatch-kpi[data-tone=warning]{border-color:var(--warning-border)}.tenant-dispatch-kpi-label{display:flex;align-items:center;justify-content:space-between;gap:8px;color:var(--text-tertiary);font:500 10px/1.2 "IBM Plex Mono",var(--font-family-mono);letter-spacing:.08em;text-transform:uppercase}.tenant-dispatch-kpi-label i{display:grid;place-items:center;width:24px;height:24px;border-radius:8px;background:var(--surface-sunken);color:var(--text-tertiary);font-style:normal}.tenant-dispatch-kpi[data-tone=warning] .tenant-dispatch-kpi-label i{background:var(--warning-bg);color:var(--warning-text)}.tenant-dispatch-kpi strong{color:var(--text-primary);font:650 28px/1 "IBM Plex Mono",var(--font-family-mono)}.tenant-dispatch-kpi small{color:var(--text-tertiary);font-size:11px}
      .tenant-dispatch-section{padding:16px;border:1px solid var(--border);border-radius:18px;background:var(--surface)}.tenant-dispatch-section>header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.tenant-dispatch-section h2{display:flex;align-items:center;gap:9px;margin:0;color:var(--text-primary);font-size:15px}.tenant-dispatch-section h2 i{width:8px;height:8px;border-radius:50%;background:var(--danger);box-shadow:none}.tenant-dispatch-section>header>span{color:var(--text-tertiary);font:500 12px/1 "IBM Plex Mono",var(--font-family-mono)}.tenant-dispatch-section>header p{margin:0;color:var(--text-tertiary);font-size:11.5px}
      .tenant-dispatch-unassigned-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.tenant-dispatch-unassigned-card{display:flex;min-width:0;flex-direction:column;gap:7px;padding:13px;border:1px solid var(--border);border-radius:13px;background:var(--surface-sunken);color:var(--text-secondary);text-align:left;cursor:pointer}.tenant-dispatch-unassigned-card:hover,.tenant-dispatch-unassigned-card[aria-current=true]{border-color:var(--brand)}.tenant-dispatch-job-top,.tenant-dispatch-job-foot{display:flex;align-items:center;justify-content:space-between;gap:8px}.tenant-dispatch-job-top strong{color:var(--text-primary);font-size:13px}.tenant-dispatch-job-top i{padding:4px 7px;border-radius:999px;background:var(--accent-muted);color:var(--brand);font:600 10px/1 "IBM Plex Mono",var(--font-family-mono);font-style:normal}.tenant-dispatch-job-top i[data-tone=danger]{background:var(--danger-bg);color:var(--danger-text)}.tenant-dispatch-job-top i[data-tone=warning]{background:var(--warning-bg);color:var(--warning-text)}.tenant-dispatch-unassigned-card>b{font-size:13px}.tenant-dispatch-unassigned-card>span:not(.tenant-dispatch-job-top):not(.tenant-dispatch-job-foot){overflow:hidden;font-size:11.5px;text-overflow:ellipsis;white-space:nowrap}.tenant-dispatch-job-foot{margin-top:2px;padding-top:8px;border-top:1px solid var(--border)}.tenant-dispatch-job-foot code{color:var(--text-primary);font:500 11px/1 "IBM Plex Mono",var(--font-family-mono)}.tenant-dispatch-job-foot em{color:var(--brand);font-size:11.5px;font-style:normal;font-weight:700}
      .tenant-dispatch-technician-list{display:flex;flex-direction:column;gap:10px}.tenant-dispatch-technician{padding:13px;border:1px solid var(--border);border-radius:13px;background:var(--surface)}.tenant-dispatch-technician>header{display:flex;align-items:center;gap:10px}.tenant-dispatch-avatar{display:grid;width:34px;height:34px;flex:none;place-items:center;overflow:hidden;border-radius:50%;background:var(--accent-muted);color:var(--brand);font-size:11px;font-weight:800}.tenant-dispatch-avatar img{width:100%;height:100%;object-fit:cover}.tenant-dispatch-technician-name{display:flex;min-width:0;flex:1;flex-direction:column;gap:2px}.tenant-dispatch-technician-name strong{color:var(--text-primary);font-size:13px}.tenant-dispatch-technician-name small{overflow:hidden;color:var(--text-tertiary);font-size:10.5px;text-overflow:ellipsis;white-space:nowrap}.tenant-dispatch-capacity{padding:4px 8px;border-radius:7px;background:var(--accent-muted);color:var(--brand);font:600 10px/1 "IBM Plex Mono",var(--font-family-mono)}.tenant-dispatch-slots{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}.tenant-dispatch-slots button,.tenant-dispatch-open-slot{display:flex;min-height:48px;flex-direction:column;justify-content:center;gap:2px;padding:7px 11px;border:1px solid var(--border);border-radius:10px;background:var(--surface);color:var(--text-primary);text-align:left}.tenant-dispatch-slots button{cursor:pointer}.tenant-dispatch-slots button:hover,.tenant-dispatch-slots button[aria-current=true]{border-color:var(--brand);background:var(--accent-muted)}.tenant-dispatch-slots button strong{font-size:11.5px}.tenant-dispatch-slots button span{font-size:10.5px}.tenant-dispatch-open-slot{border-style:dashed;color:var(--text-tertiary);font-size:11px}.tenant-dispatch-empty{padding:30px;text-align:center;color:var(--text-tertiary);font-size:12px}
      @media(max-width:820px){.tenant-dispatch-kpis{grid-template-columns:1fr}.tenant-dispatch-unassigned-grid{grid-template-columns:1fr}.tenant-dispatch-section>header{align-items:flex-start;flex-direction:column}.tenant-dispatch-today>header p{max-width:460px}}
    `}</style>
  </div>;
}
