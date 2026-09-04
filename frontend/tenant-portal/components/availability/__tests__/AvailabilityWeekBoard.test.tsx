import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AvailabilityWeekBoard } from "../AvailabilityWeekBoard";

const days = [
  "2026-08-30", "2026-08-31", "2026-09-01", "2026-09-02",
  "2026-09-03", "2026-09-04", "2026-09-05",
];

describe("AvailabilityWeekBoard", () => {
  it("renders the reference week cards and opens a selected day drawer", () => {
    const onSelectDay = vi.fn();
    render(
      <AvailabilityWeekBoard
        technicians={[{
          id: "staff-1",
          full_name: "Amandeep Kumar",
          designation: "Technician",
          status: "active",
          max_concurrent_jobs: 1,
          profile_photo_url: null,
          member_type: "technician",
        }]}
        schedules={days.map((date, index) => ({
          staff_id: "staff-1",
          date,
          available: index > 0 && index < 6,
          reasons: index === 0 || index === 6 ? ["business_closed"] : [],
          working_hours: index === 0 || index === 6 ? null : { start: "09:00", end: "18:00" },
          daily_capacity: { limit: index === 0 || index === 6 ? 0 : 6 },
          assignments_today: index === 4 ? [{
            job_id: "job-1",
            job_number: "JOB-001",
            status: "assigned",
            time_window: "14:00–16:00",
            service_name: "Geyser Service & Descaling",
          }] : [],
        }))}
        days={days}
        focusDate="2026-09-03"
        selectedStaffId={null}
        onSelectDay={onSelectDay}
        onCloseDrawer={vi.fn()}
        onOpenJob={vi.fn()}
      />,
    );

    expect(screen.getByText("On duty today")).toBeInTheDocument();
    expect(screen.getByText("Jobs this week")).toBeInTheDocument();
    expect(screen.getByText("Open capacity")).toBeInTheDocument();
    expect(screen.getByText("On leave")).toBeInTheDocument();
    expect(screen.getByText("Amandeep Kumar")).toBeInTheDocument();
    expect(screen.getByText(/Geyser Service & Descaling/)).toBeInTheDocument();
    expect(screen.getByText("Has jobs booked")).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Geyser Service & Descaling/).closest("button")!);
    expect(onSelectDay).toHaveBeenCalledWith("staff-1", "2026-09-03");
  });

  it("shows working hours, jobs and free capacity in the day drawer", () => {
    const onOpenJob = vi.fn();
    render(
      <AvailabilityWeekBoard
        technicians={[{
          id: "staff-1",
          full_name: "Amandeep Kumar",
          designation: "Technician",
          status: "active",
          max_concurrent_jobs: 1,
          profile_photo_url: null,
          member_type: "technician",
        }]}
        schedules={[{
          staff_id: "staff-1",
          date: "2026-09-03",
          available: true,
          reasons: [],
          working_hours: { start: "09:00", end: "18:00" },
          daily_capacity: { limit: 6 },
          assignments_today: [{
            job_id: "job-1",
            job_number: "JOB-001",
            status: "assigned",
            time_window: "14:00–16:00",
            service_name: "AC Gas Refill",
          }],
        }]}
        days={["2026-09-03"]}
        focusDate="2026-09-03"
        selectedStaffId="staff-1"
        onSelectDay={vi.fn()}
        onCloseDrawer={vi.fn()}
        onOpenJob={onOpenJob}
      />,
    );

    expect(screen.getByText("Working hours")).toBeInTheDocument();
    expect(screen.getByText("Booked jobs (1)")).toBeInTheDocument();
    expect(screen.getByText("5 more jobs could fit today")).toBeInTheDocument();
    fireEvent.click(screen.getAllByText("AC Gas Refill").at(-1)!);
    expect(onOpenJob).toHaveBeenCalledWith("job-1");
  });
});
