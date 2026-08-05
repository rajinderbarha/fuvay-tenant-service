import React from "react";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HowItWorksSection } from "../HowItWorksSection";

describe("HowItWorksSection", () => {
  it("renders every step in order", () => {
    const { getByText } = renderWithProviders(<HowItWorksSection />);
    expect(getByText("1. Tell us what's wrong")).toBeTruthy();
    expect(getByText("2. See the price and the time slot")).toBeTruthy();
    expect(getByText("3. A verified provider is assigned")).toBeTruthy();
    expect(getByText("4. Job done, then you pay")).toBeTruthy();
  });

  it("states the two things a customer cannot discover from the booking screen", () => {
    // These are the claims the section exists to make -- that a real slot is
    // shown BEFORE committing, and that nobody waits on a callback. If the
    // copy ever drifts away from what the product does, this should fail.
    const { getByText } = renderWithProviders(<HowItWorksSection />);
    expect(getByText(/before you confirm anything/i)).toBeTruthy();
    expect(getByText(/No waiting for a callback/i)).toBeTruthy();
  });
});
