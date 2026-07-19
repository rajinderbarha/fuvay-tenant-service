import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ComplaintWorkspace, DisputePresentation } from "../ComplaintWorkspace";
import { complaintDetailFixture, disputeFixture } from "../../../lib/ux04/fixtures";

describe("ComplaintWorkspace / DisputePresentation — no tenant resolution/refund authority", () => {
  it("ComplaintWorkspace renders no resolve/refund button", () => {
    render(<ComplaintWorkspace complaint={complaintDetailFixture} />);
    expect(screen.queryByRole("button", { name: /resolve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /refund/i })).not.toBeInTheDocument();
  });

  it("ComplaintWorkspace marks an internal-only timeline entry distinctly from customer-visible ones", () => {
    render(<ComplaintWorkspace complaint={complaintDetailFixture} />);
    expect(screen.getByText(/\(internal\)/i)).toBeInTheDocument();
  });

  it("DisputePresentation states the platform issues a Customer Service Credit, never a cash refund, and has no tenant control to issue one", () => {
    render(<DisputePresentation dispute={disputeFixture} />);
    expect(screen.getByText(/customer service credit/i)).toBeInTheDocument();
    expect(screen.getByText(/never a cash refund/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
