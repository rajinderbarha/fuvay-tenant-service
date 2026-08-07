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

  it("marks only the reached step and everything before it as done", () => {
    const { getByLabelText } = renderWithProviders(<RequestJourneyStepper stage="provider_assignment" />);
    expect(getByLabelText(/^Request confirmed/).props.accessibilityLabel).toContain("done");
    expect(getByLabelText(/^Provider assignment/).props.accessibilityLabel).toContain("done");
    expect(getByLabelText(/^Visit scheduling/).props.accessibilityLabel).toContain("not yet reached");
  });

  it("reports progress as a step fraction, not a percentage that implies elapsed time", () => {
    const { getByLabelText } = renderWithProviders(<RequestJourneyStepper stage="request_confirmed" />);
    expect(getByLabelText(/^Booking progress/).props.accessibilityLabel).toBe("Booking progress: step 1 of 4");
  });
});
