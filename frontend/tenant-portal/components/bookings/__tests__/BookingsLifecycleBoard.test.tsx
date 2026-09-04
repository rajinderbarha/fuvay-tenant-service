import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BookingsLifecycleBoard } from "../BookingsLifecycleBoard";
import type { BJItem } from "../../../lib/api";

function job(overrides: Partial<BJItem>): BJItem {
  return {
    service_job_id: "job-1",
    job_number: "BAS-JOB-0001",
    booking_number: "BAS-BK-0001",
    stage: "new",
    customer_alias: "Customer HS-9E8A",
    service_name: "AC Repair",
    assigned_staff_name: null,
    scheduled_time_window: "09:00–11:00",
    sla: { sla_status: "BREACHED", minutes_overdue: 42, minutes_remaining: null },
    ...overrides,
  } as BJItem;
}

describe("BookingsLifecycleBoard", () => {
  it("renders the complete lifecycle and groups live jobs into their stages", () => {
    render(<BookingsLifecycleBoard items={[
      job({}),
      job({ service_job_id: "job-2", job_number: "BAS-JOB-0002", stage: "scheduled", assigned_staff_name: "Amandeep Kumar" }),
    ]} selectedJobId={null} onOpen={() => {}} />);

    expect(screen.getAllByRole("region")).toHaveLength(9);
    expect(within(screen.getByRole("region", { name: "New, 1 jobs" })).getByText("BAS-JOB-0001")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Scheduled, 1 jobs" })).getByText("Amandeep Kumar")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Completed, 0 jobs" })).toBeInTheDocument();
  });

  it("opens the existing job preview from a board card", () => {
    const onOpen = vi.fn();
    render(<BookingsLifecycleBoard items={[job({})]} selectedJobId={null} onOpen={onOpen} />);

    fireEvent.click(screen.getByRole("button", { name: /BAS-JOB-0001/i }));
    expect(onOpen).toHaveBeenCalledWith("job-1");
  });
});
