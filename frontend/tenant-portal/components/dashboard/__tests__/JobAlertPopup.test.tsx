import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { playAlertTone } = vi.hoisted(() => ({ playAlertTone: vi.fn() }));
vi.mock("../../../lib/alertTone", () => ({ playAlertTone }));

import { JobAlertPopup } from "../JobAlertPopup";
import type { DashboardAlert } from "../../../lib/api";

const newJob: DashboardAlert = {
  job_id: "job-new",
  label: "FUV-1002",
  city: "Ludhiana",
  tone: "success",
  title: "New booking received",
  message: "AC service has been booked for today.",
  scheduled_date: "2026-09-02",
  scheduled_time_window: "14:00-16:00",
};

const delayedJob: DashboardAlert = {
  job_id: "job-late",
  label: "FUV-1001",
  city: "Ludhiana",
  tone: "warning",
  title: "Job past its slot",
  message: "Update the customer or reschedule this job.",
  lateness_label: "20 minutes late",
  scheduled_date: "2026-09-02",
  scheduled_time_window: "10:00-12:00",
};

describe("JobAlertPopup", () => {
  beforeEach(() => playAlertTone.mockClear());

  it("leads with the most urgent job and exposes the real queue totals", () => {
    render(<JobAlertPopup
      alerts={[newJob, delayedJob]}
      newTotal={4}
      delayedTotal={3}
      onDismiss={vi.fn()}
      onOpenJob={vi.fn()}
      onSeeAllDelayed={vi.fn()}
    />);

    expect(screen.getByRole("dialog", { name: "Job past its slot" })).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("3 past slot · 4 new · 5 more")).toBeInTheDocument();
    expect(playAlertTone).toHaveBeenCalledWith("warning");
  });

  it("connects dismiss, queue, and primary job actions", () => {
    const onDismiss = vi.fn();
    const onOpenJob = vi.fn();
    const onSeeAllDelayed = vi.fn();
    render(<JobAlertPopup
      alerts={[delayedJob]}
      newTotal={0}
      delayedTotal={2}
      onDismiss={onDismiss}
      onOpenJob={onOpenJob}
      onSeeAllDelayed={onSeeAllDelayed}
    />);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss job alert" }));
    fireEvent.click(screen.getByRole("button", { name: "See all delayed" }));
    fireEvent.click(screen.getByRole("button", { name: "Open job" }));

    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onSeeAllDelayed).toHaveBeenCalledOnce();
    expect(onOpenJob).toHaveBeenCalledWith("job-late");
  });

  it("renders nothing when there are no alerts", () => {
    const { container } = render(<JobAlertPopup
      alerts={[]}
      newTotal={0}
      delayedTotal={0}
      onDismiss={vi.fn()}
      onOpenJob={vi.fn()}
      onSeeAllDelayed={vi.fn()}
    />);
    expect(container).toBeEmptyDOMElement();
  });
});
