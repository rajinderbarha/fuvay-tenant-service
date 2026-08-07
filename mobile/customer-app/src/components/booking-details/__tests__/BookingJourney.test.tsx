import React from "react";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { BookingJourney } from "../BookingJourney";

/**
 * The visual state of each step is a correctness concern, not decoration:
 * colouring "Schedule" as reached on a booking with no visit scheduled
 * would tell the customer something untrue. The accessible label is the
 * assertable surface for that state.
 */
function labels(stage: Parameters<typeof BookingJourney>[0]["stage"]) {
  const { getByLabelText } = renderWithProviders(<BookingJourney stage={stage} />);
  return {
    requestConfirmed: getByLabelText(/^Request confirmed/),
    providerAssignment: getByLabelText(/^Provider assignment/),
    visitScheduling: getByLabelText(/^Visit scheduling/),
  };
}

describe("BookingJourney step states", () => {
  it("marks only the reached step as current while the rest stay ahead", () => {
    const l = labels("provider_assignment");
    expect(l.requestConfirmed.props.accessibilityLabel).toContain("done");
    expect(l.providerAssignment.props.accessibilityLabel).toContain("current step");
    expect(l.visitScheduling.props.accessibilityLabel).toContain("not yet reached");
  });

  it("never shows scheduling as reached before the booking is scheduled", () => {
    // The reference design draws all three steps filled; doing that
    // literally would claim a visit exists when none does.
    for (const stage of ["request_confirmed", "provider_assignment", "provider_assigned"] as const) {
      const { getByLabelText } = renderWithProviders(<BookingJourney stage={stage} />);
      expect(getByLabelText(/^Visit scheduling/).props.accessibilityLabel).toContain("not yet reached");
    }
  });

  it("treats an unknown stage as the earliest step rather than guessing forward", () => {
    const l = labels("unknown");
    expect(l.requestConfirmed.props.accessibilityLabel).toContain("current step");
    expect(l.visitScheduling.props.accessibilityLabel).toContain("not yet reached");
  });
});
