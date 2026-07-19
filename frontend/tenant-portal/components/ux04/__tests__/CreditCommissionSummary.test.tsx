import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreditCommissionSummary } from "../CreditCommissionSummary";
import { creditCommissionFixture } from "../../../lib/ux04/fixtures";

describe("CreditCommissionSummary — credit/commission/deposit/payment separation", () => {
  it("never renders a payout/withdrawal/settlement action", () => {
    render(<CreditCommissionSummary view={creditCommissionFixture} />);
    expect(screen.queryByRole("button", { name: /payout/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /withdraw/i })).not.toBeInTheDocument();
  });

  it("explicitly states credit is not customer money and commission is not a payout", () => {
    render(<CreditCommissionSummary view={creditCommissionFixture} />);
    expect(screen.getByText(/not customer money/i)).toBeInTheDocument();
    expect(screen.getByText(/not a payout/i)).toBeInTheDocument();
  });
});
