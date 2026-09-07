import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const { getOverview } = vi.hoisted(() => ({ getOverview: vi.fn() }));
vi.mock("../../../lib/api", () => ({ homeServicesSetupOverviewApi: { getOverview } }));
import { ServicesSetupProgress } from "../ServicesSetupProgress";

it("separates service completion from overall onboarding", async () => {
  getOverview.mockResolvedValue({ progress: { percentage: 40, completed_required: 2, total_required: 5 }, sections: [{ key: "SERVICES_PRICING", status: "not_started", percentage: 50, configured_count: 1, enabled_count: 2, blocking_reasons: [{ code: "PRICE", message: "Set the repair price." }] }] });
  const { rerender } = render(<ServicesSetupProgress revision={1} />);
  expect(screen.getByText("Step 3 of 8")).toBeInTheDocument();
  expect(await screen.findByText("50%")).toBeInTheDocument();
  expect(screen.getByText(/Overall onboarding: 40%/)).toBeInTheDocument();
  expect(screen.getByText("Set the repair price.")).toBeInTheDocument();
  expect(screen.getByText("In progress")).toBeInTheDocument();
  expect(screen.queryByText("100% complete")).not.toBeInTheDocument();
  getOverview.mockResolvedValue({ progress: { percentage: 40, completed_required: 2, total_required: 5 }, sections: [{ key: "SERVICES_PRICING", status: "complete", configured_count: 2, enabled_count: 2 }] });
  rerender(<ServicesSetupProgress revision={2} />);
  expect(await screen.findByText("100% complete")).toBeInTheDocument();
  expect(screen.getByText("100%")).toBeInTheDocument();
  expect(screen.getByText(/Overall onboarding: 40%/)).toBeInTheDocument();
});

it("does not invent a percentage when the progress request fails", async () => {
  getOverview.mockRejectedValue(new Error("offline"));
  render(<ServicesSetupProgress revision={1} />);
  expect(await screen.findByText("Setup progress is temporarily unavailable.")).toBeInTheDocument();
  expect(screen.queryByText("100% complete")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry progress" })).toBeInTheDocument();
});
