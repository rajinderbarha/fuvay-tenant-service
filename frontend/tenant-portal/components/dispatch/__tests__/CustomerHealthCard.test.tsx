import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CustomerHealthCard } from "../CustomerHealthCard";

describe("CustomerHealthCard", () => {
  it("makes payment risk and the protection rule unmistakable", () => {
    render(<CustomerHealthCard health={{
      score: 38,
      band: "restricted",
      can_book: true,
      advance_required_pct: 50,
      signals: { payment_reliability: 25, customer_behavior: 90 },
    }} />);

    expect(screen.getByLabelText("Customer health")).toHaveTextContent("High-risk customer");
    expect(screen.getByText("Payment reliability · 80%")).toBeInTheDocument();
    expect(screen.getByText("25/100")).toBeInTheDocument();
    expect(screen.getByText("Poor payment history")).toBeInTheDocument();
    expect(screen.getByText("Payment protection: collect 50% advance before service.")).toBeInTheDocument();
  });

  it("shows a trusted customer as an excellent customer", () => {
    render(<CustomerHealthCard health={{
      score: 92,
      band: "trusted",
      can_book: true,
      signals: { payment_reliability: 95, customer_behavior: 80 },
    }} />);

    expect(screen.getByText("Excellent customer")).toBeInTheDocument();
    expect(screen.getByText("Reliable payment history")).toBeInTheDocument();
  });
});
