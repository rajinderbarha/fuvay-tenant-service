import React from "react";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { RequestJourneyStepper } from "../RequestJourneyStepper";

describe("RequestJourneyStepper", () => {
  it("never marks Service visit reached, at any stage this component renders for", () => {
    // This component only renders in the booking's earliest state (see
    // BookingDetailsScreen); once a job genuinely progresses, the screen
    // switches to JobProgressTimeline, which owns that evidence. Nothing
    // here may ever claim a visit is underway.
    for (const stage of ["request_confirmed", "provider_assignment", "provider_assigned", "unknown"] as const) {
      const { getByLabelText } = renderWithProviders(<RequestJourneyStepper stage={stage} />);
      expect(getByLabelText(/^Service visit/).props.accessibilityLabel).toContain("not yet reached");
    }
  });

  it("marks steps before the current one as done, the current one as current, and the rest as not yet reached", () => {
    // Three real visual states, not two: a step already passed (green,
    // done) must read differently from the one actually in progress
    // (brand colour, current) -- collapsing them would make the design's
    // current-step highlight meaningless.
    const { getByLabelText } = renderWithProviders(<RequestJourneyStepper stage="provider_assignment" />);
    expect(getByLabelText(/^Request confirmed/).props.accessibilityLabel).toContain("done");
    expect(getByLabelText(/^Provider assignment/).props.accessibilityLabel).toContain("current step");
    expect(getByLabelText(/^Visit scheduling/).props.accessibilityLabel).toContain("not yet reached");
  });
});
