import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TenantDispatchBoard } from "../TenantDispatchBoard";
import type { HsDispatchProjection } from "../../../lib/api";

const job = {
  job_id: "job-1",
  job_number: "JOB-0001",
  booking_id: "booking-1",
  status: "scheduled",
  assignment_status: "unassigned",
  scheduled_date: "2026-09-04",
  scheduled_time_window: "09:00-11:00",
  customer_alias: "Customer HS-1234",
  locality: "Central",
  master_service_name: "AC Repair",
  minutes_until_due: 90,
};

const projection: HsDispatchProjection = {
  summary: {
    unassigned_count: 1,
    scheduled_count: 1,
    on_the_way_count: 0,
    capacity_used: 1,
    capacity_total: 3,
    conflict_count: 0,
  },
  unassigned_jobs: [job],
  scheduled_jobs: [{ ...job, assigned_staff_id: "staff-1", assignment_status: "assigned" }],
  technician_schedule: [{
    staff_member_id: "staff-1",
    name: "Jaspreet Singh",
    status: "active",
    capacity_used: 1,
    capacity_limit: 3,
    jobs_in_range: [{ ...job, assigned_staff_id: "staff-1", assignment_status: "assigned" }],
    jobs_today: [{ ...job, assigned_staff_id: "staff-1", assignment_status: "assigned" }],
  }],
  conflicts: 0,
  available_actions: ["assign"],
  pagination: { total: 1, limit: 25, offset: 0 },
  filters: { services: [], technicians: [] },
  view: "day",
  range_start: "2026-09-04",
  range_end: "2026-09-04",
  schedule_truncated: false,
  generated_at: "2026-09-04T09:00:00Z",
};

describe("TenantDispatchBoard", () => {
  it("renders the supplied compact dispatch hierarchy", () => {
    render(<TenantDispatchBoard board={projection} date="2026-09-04" selectedJobId={null} onSelectJob={() => {}} />);

    expect(screen.getByText("Scheduled today")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs a technician" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Technicians today" })).toBeInTheDocument();
    expect(screen.getByText("+ 2 open slots")).toBeInTheDocument();
  });

  it("keeps job selection connected to the assignment workspace", () => {
    const onSelectJob = vi.fn();
    render(<TenantDispatchBoard board={projection} date="2026-09-04" selectedJobId={null} onSelectJob={onSelectJob} />);

    fireEvent.click(screen.getByRole("button", { name: /JOB-0001 90m left/i }));
    expect(onSelectJob).toHaveBeenCalledWith("job-1");
  });

  it("keeps an explicit queue section when the day has no unassigned jobs", () => {
    render(<TenantDispatchBoard board={{ ...projection, unassigned_jobs: [], pagination: { ...projection.pagination, total: 0 }, summary: { ...projection.summary, unassigned_count: 0 } }} date="2026-09-04" selectedJobId={null} onSelectJob={() => {}} />);

    expect(screen.getByRole("heading", { name: "Needs a technician" })).toBeInTheDocument();
    expect(screen.getByText("No unassigned jobs for this date.")).toBeInTheDocument();
  });
});
