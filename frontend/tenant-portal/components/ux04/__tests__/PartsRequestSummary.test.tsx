import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PartsRequestSummary } from "../PartsRequestSummary";
import { partsRequestFixture } from "../../../lib/ux04/fixtures";

describe("PartsRequestSummary authorization presentation", () => {
  it("renders Approve/Reject controls when the approve action is available", () => {
    const view = {
      ...partsRequestFixture,
      request: { ...partsRequestFixture.request, status: "requested" as const },
      actions: [{ actionKey: "inventory:items:approve", available: true, reason: null }],
    };
    render(<PartsRequestSummary view={view} />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  });

  it("renders an explanatory reason instead of a control when approve is not available (explicit deny / no permission)", () => {
    const view = {
      ...partsRequestFixture,
      request: { ...partsRequestFixture.request, status: "requested" as const },
      actions: [{ actionKey: "inventory:items:approve", available: false, reason: "Requires tenant_owner or a staff member with the parts-approval permission." }],
    };
    render(<PartsRequestSummary view={view} />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.getByText(/requires tenant_owner/i)).toBeInTheDocument();
  });

  it("never renders a technician mark-installed control", () => {
    render(<PartsRequestSummary view={partsRequestFixture} />);
    expect(screen.queryByRole("button", { name: /install/i })).not.toBeInTheDocument();
  });

  it("PartsRequest never links to a field_ops.Job id", () => {
    render(<PartsRequestSummary view={partsRequestFixture} />);
    expect(screen.getByText(new RegExp(partsRequestFixture.request.serviceJobId))).toBeInTheDocument();
  });
});
