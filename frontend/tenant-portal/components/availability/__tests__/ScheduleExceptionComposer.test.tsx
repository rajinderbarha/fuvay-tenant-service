import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScheduleExceptionComposer } from "../ScheduleExceptionComposer";

const calendar = {
  country: "IN",
  states: ["Punjab"],
  subdivisions: ["PB"],
  source: "python-holidays",
  from_date: "2026-09-25",
  to_date: "2027-09-25",
  holidays: [{
    date: "2026-10-02",
    name: "Mahatma Gandhi's Jayanti",
    scope: "national" as const,
    subdivisions: ["PB"],
    already_closed: false,
    exception_id: null,
  }],
};

describe("ScheduleExceptionComposer", () => {
  it("adds a synced holiday without asking the provider to type", async () => {
    const onAdd = vi.fn().mockResolvedValue(true);
    render(<ScheduleExceptionComposer calendar={calendar} exceptions={[]} minDate="2026-09-25" saving={false} onAdd={onAdd}/>);

    expect(screen.queryByPlaceholderText("Enter a short closure reason")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Holiday"), { target: { value: "2026-10-02" } });
    expect(screen.getByText("Mahatma Gandhi's Jayanti")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add holiday closure" }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith({
      date: "2026-10-02",
      reason: "Mahatma Gandhi's Jayanti",
      source: "holiday_calendar",
    }));
  });

  it("keeps guided custom closures for provider-specific days", async () => {
    const onAdd = vi.fn().mockResolvedValue(true);
    render(<ScheduleExceptionComposer calendar={calendar} exceptions={[]} minDate="2026-09-25" saving={false} onAdd={onAdd}/>);

    fireEvent.click(screen.getByRole("button", { name: "Custom closure" }));
    fireEvent.change(screen.getByLabelText("Closure date"), { target: { value: "2026-10-05" } });
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "Staff training" } });
    fireEvent.click(screen.getByRole("button", { name: "Add custom closure" }));

    await waitFor(() => expect(onAdd).toHaveBeenCalledWith({
      date: "2026-10-05", reason: "Staff training", source: "custom",
    }));
  });

  it("does not offer a holiday that is already closed", () => {
    render(<ScheduleExceptionComposer
      calendar={{ ...calendar, holidays: [{ ...calendar.holidays[0], already_closed: true }] }}
      exceptions={[]} minDate="2026-09-25" saving={false} onAdd={vi.fn()}
    />);

    expect(screen.getByText("All holidays in the current calendar range are already closed.")).toBeInTheDocument();
  });
});
