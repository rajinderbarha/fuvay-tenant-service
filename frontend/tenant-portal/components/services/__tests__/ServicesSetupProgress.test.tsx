import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const { getOverview } = vi.hoisted(() => ({ getOverview: vi.fn() }));
vi.mock("../../../lib/api", () => ({ homeServicesSetupOverviewApi: { getOverview } }));
import { ServicesSetupProgress } from "../ServicesSetupProgress";

it("shows the server percentage and only marks the service section complete when ready", async () => {
  getOverview.mockResolvedValue({ progress: { percentage: 60, completed_required: 3, total_required: 5 }, sections: [{ key: "SERVICES_PRICING", status: "not_started" }] });
  const { rerender } = render(<ServicesSetupProgress revision={1} />);
  expect(screen.getByText("Step 3 of 8")).toBeInTheDocument();
  expect(await screen.findByText("60%")).toBeInTheDocument();
  expect(screen.getByText("In progress")).toBeInTheDocument();
  expect(screen.queryByText("100% complete")).not.toBeInTheDocument();
  getOverview.mockResolvedValue({ progress: { percentage: 100, completed_required: 5, total_required: 5 }, sections: [{ key: "SERVICES_PRICING", status: "complete" }] });
  rerender(<ServicesSetupProgress revision={2} />);
  expect(await screen.findByText("100% complete")).toBeInTheDocument();
});

it("does not invent a percentage when the progress request fails", async () => {
  getOverview.mockRejectedValue(new Error("offline"));
  render(<ServicesSetupProgress revision={1} />);
  expect(await screen.findByText("Setup progress is temporarily unavailable.")).toBeInTheDocument();
  expect(screen.queryByText("100% complete")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry progress" })).toBeInTheDocument();
});
