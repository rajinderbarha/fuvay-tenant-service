import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { playAlertTone } = vi.hoisted(() => ({ playAlertTone: vi.fn() }));
vi.mock("../../../lib/alertTone", () => ({ playAlertTone }));

import { JobAlertPopup } from "../JobAlertPopup";
import type { DashboardAlert } from "../../../lib/api";

const newJob: DashboardAlert = {
  job_id: "job-new", label: "FUV-1002", city: "Ludhiana", tone: "success",
  title: "New booking received", message: "AC service has been booked for today.",
  scheduled_date: "2026-09-02", scheduled_time_window: "14:00-16:00",
  assignment_deadline_at: new Date(Date.now() + 15 * 60_000).toISOString(),
};
const delayedJob: DashboardAlert = {
  job_id: "job-late", label: "FUV-1001", city: "Ludhiana", tone: "warning",
  title: "Job past its slot", message: "Update the customer or reschedule this job.",
  lateness_label: "20 minutes late", scheduled_date: "2026-09-02",
  scheduled_time_window: "10:00-12:00",
};

describe("JobAlertPopup", () => {
  beforeEach(() => playAlertTone.mockClear());

  it("leads with a live unassigned offer in a wide actionable dialog", () => {
    render(<JobAlertPopup alerts={[delayedJob, newJob]} newTotal={4} delayedTotal={3}
      onDismiss={vi.fn()} onOpenJob={vi.fn()} onSeeAllDelayed={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Job alerts" })).toBeInTheDocument();
    expect(screen.getByText("Newest booking")).toBeInTheDocument();
    expect(screen.getByText("5 more on the bookings board")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Assign technician" })).toBeInTheDocument();
    expect(playAlertTone).toHaveBeenCalledWith("success");
  });

  it("connects dismiss, board, and primary job actions", () => {
    const onDismiss = vi.fn();
    const onOpenJob = vi.fn();
    const onOpenBoard = vi.fn();
    render(<JobAlertPopup alerts={[delayedJob]} newTotal={0} delayedTotal={2}
      onDismiss={onDismiss} onOpenJob={onOpenJob}
      onSeeAllDelayed={vi.fn()} onOpenBoard={onOpenBoard} />);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss job alert" }));
    fireEvent.click(screen.getByRole("button", { name: "Open bookings board" }));
    fireEvent.click(screen.getByRole("button", { name: "Open job" }));
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onOpenBoard).toHaveBeenCalledOnce();
    expect(onOpenJob).toHaveBeenCalledWith("job-late");
  });

  it("renders nothing when there are no alerts", () => {
    const { container } = render(<JobAlertPopup alerts={[]} newTotal={0} delayedTotal={0}
      onDismiss={vi.fn()} onOpenJob={vi.fn()} onSeeAllDelayed={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
