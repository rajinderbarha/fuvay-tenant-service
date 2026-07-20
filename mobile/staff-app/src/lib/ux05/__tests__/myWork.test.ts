import { classifyJob, groupJobs, filterJobs } from "../myWork";
import type { Job } from "../../api";

function job(overrides: Partial<Job>): Job {
  return {
    id: "j1", job_number: "SJ-001", booking_id: "bk1", tenant_id: "t1",
    customer_id: "c1", assigned_staff_id: "s1",
    scheduled_date: null, scheduled_time_window: null,
    city: "Delhi", zipcode: "110001",
    status: "assigned", assignment_status: "pending", failure_reason: null,
    completion_data: null, created_at: "2026-07-20T09:00:00Z", updated_at: "2026-07-20T09:00:00Z",
    ...overrides,
  };
}

describe("classifyJob", () => {
  it("classifies an in-progress status as current", () => {
    expect(classifyJob(job({ status: "reached_site" }))).toBe("current");
    expect(classifyJob(job({ status: "service_started" }))).toBe("current");
  });

  it("classifies assigned/quote_required as needs_action, not current", () => {
    expect(classifyJob(job({ status: "assigned" }))).toBe("needs_action");
    expect(classifyJob(job({ status: "quote_required" }))).toBe("needs_action");
  });

  it("classifies completed/cancelled/failed as completed", () => {
    expect(classifyJob(job({ status: "completed" }))).toBe("completed");
    expect(classifyJob(job({ status: "cancelled" }))).toBe("completed");
    expect(classifyJob(job({ status: "failed" }))).toBe("completed");
  });

  it("classifies an accepted job scheduled today as today", () => {
    const now = new Date("2026-07-20T12:00:00Z");
    expect(classifyJob(job({ status: "accepted", scheduled_date: "2026-07-20" }), now)).toBe("today");
  });

  it("classifies an accepted job scheduled in the future as upcoming", () => {
    const now = new Date("2026-07-20T12:00:00Z");
    expect(classifyJob(job({ status: "accepted", scheduled_date: "2026-08-01" }), now)).toBe("upcoming");
  });
});

describe("groupJobs", () => {
  it("buckets every job into exactly one group", () => {
    const jobs = [
      job({ id: "a", status: "assigned" }),
      job({ id: "b", status: "reached_site" }),
      job({ id: "c", status: "completed" }),
    ];
    const groups = groupJobs(jobs);
    expect(groups.needs_action.map(j => j.id)).toEqual(["a"]);
    expect(groups.current.map(j => j.id)).toEqual(["b"]);
    expect(groups.completed.map(j => j.id)).toEqual(["c"]);
    expect(groups.today).toEqual([]);
    expect(groups.upcoming).toEqual([]);
  });
});

describe("filterJobs", () => {
  it("filters by exact status", () => {
    const jobs = [job({ id: "a", status: "assigned" }), job({ id: "b", status: "completed" })];
    expect(filterJobs(jobs, { status: "completed" }).map(j => j.id)).toEqual(["b"]);
  });

  it("filters to needs-action-only", () => {
    const jobs = [job({ id: "a", status: "assigned" }), job({ id: "b", status: "reached_site" })];
    expect(filterJobs(jobs, { needsActionOnly: true }).map(j => j.id)).toEqual(["a"]);
  });
});
