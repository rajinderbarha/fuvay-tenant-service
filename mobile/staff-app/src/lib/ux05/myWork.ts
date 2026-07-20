/**
 * My Work grouping logic (workstream 5) -- pure functions so the grouping
 * rule is unit-testable independent of any screen/render layer.
 *
 * Groups: current / today / upcoming / needs_action / completed.
 * "current" = the single active-in-progress job (post-accept, pre-complete).
 * "needs_action" = jobs whose next status requires the technician to act
 * right now (assigned needing accept/reject, or a completed inspection
 * waiting on a quote decision) -- distinct from "current" which is the one
 * job physically being worked.
 */
import type { Job } from "../api";
import type { MyWorkGroup } from "../../types/ux05";

/** MyWorkGroup plus the UI-only "all" (unfiltered) tab. groupJobs() itself
 * never returns an "all" bucket -- callers handle that case separately
 * (see JobsListScreen). */
export type MyWorkGroupKey = MyWorkGroup | "all";

const IN_PROGRESS = new Set([
  "on_the_way", "reached_site", "inspection_started", "inspection_done",
  "service_started", "work_done",
]);
const NEEDS_ACTION = new Set(["assigned", "quote_required"]);

export function classifyJob(job: Job, now: Date = new Date()): MyWorkGroup {
  if (job.status === "completed" || job.status === "cancelled" || job.status === "failed") return "completed";
  if (IN_PROGRESS.has(job.status)) return "current";
  if (NEEDS_ACTION.has(job.status)) return "needs_action";
  const scheduled = job.scheduled_date ? new Date(job.scheduled_date) : null;
  if (scheduled && isSameDay(scheduled, now)) return "today";
  return "upcoming";
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function groupJobs(jobs: Job[], now: Date = new Date()): Record<MyWorkGroup, Job[]> {
  const groups: Record<MyWorkGroup, Job[]> = {
    current: [], today: [], upcoming: [], needs_action: [], completed: [],
  };
  for (const job of jobs) groups[classifyJob(job, now)].push(job);
  return groups;
}

export interface MyWorkFilter {
  status?: string;
  needsActionOnly?: boolean;
}

export function filterJobs(jobs: Job[], filter: MyWorkFilter): Job[] {
  let result = jobs;
  if (filter.status) result = result.filter(j => j.status === filter.status);
  if (filter.needsActionOnly) result = result.filter(j => NEEDS_ACTION.has(j.status));
  return result;
}
