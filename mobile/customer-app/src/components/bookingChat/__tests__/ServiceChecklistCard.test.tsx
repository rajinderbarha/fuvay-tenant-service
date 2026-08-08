import React from "react";
import { screen, waitFor, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ServiceChecklistCard } from "../ServiceChecklistCard";
import { ServiceChecklist } from "../../../domain/serviceChecklist";

/**
 * The reveal is a CHAIN of setTimeouts -- each revealed point re-renders and
 * schedules the next. Fake timers do not advance cleanly through that chain, so
 * these use real timers with an explicit budget rather than waitFor's 1s
 * default, which the staged reveal legitimately exceeds under full-suite load.
 * (Passing alone but failing in a full run is exactly the flake this prevents.)
 */
const REVEAL_BUDGET_MS = 6000;

function checklist(overrides: Partial<ServiceChecklist> = {}): ServiceChecklist {
  return {
    totalPoints: 3,
    photoPoints: 1,
    providerSelected: true,
    sections: [
      {
        title: "Before starting",
        points: [
          { id: "a", label: "Confirmed the reported problem", helpText: null, requiresPhoto: false },
          { id: "b", label: "Photographed the unit", helpText: null, requiresPhoto: true },
        ],
      },
      {
        title: "Before leaving",
        points: [
          { id: "c", label: "Left the work area clean", helpText: null, requiresPhoto: false },
        ],
      },
    ],
    ...overrides,
  };
}

describe("ServiceChecklistCard", () => {
  it("renders NOTHING when the service has no authored checklist", () => {
    // The honesty rule: an unauthored service must not be dressed up with
    // generic reassurance the provider is not actually committed to. Absence is
    // asserted on the card's own content -- the test provider wrapper is always
    // in the tree, so the root is never null.
    renderWithProviders(
      <ServiceChecklistCard
        checklist={checklist({ totalPoints: 0, sections: [] })}
        onContinue={() => {}}
      />,
    );
    expect(screen.queryByText("What your technician will do")).toBeNull();
    expect(screen.queryByLabelText("Continue")).toBeNull();
  });

  it("renders nothing when the count is positive but no points came through", () => {
    // Guards a contract drift where total_points disagrees with sections:
    // showing a count with no list would be worse than showing nothing.
    renderWithProviders(
      <ServiceChecklistCard
        checklist={checklist({ totalPoints: 5, sections: [] })}
        onContinue={() => {}}
      />,
    );
    expect(screen.queryByText("What your technician will do")).toBeNull();
    expect(screen.queryByText(/5 checks/)).toBeNull();
  });

  it("states the real number of checks and how many are photographed", () => {
    renderWithProviders(<ServiceChecklistCard checklist={checklist()} onContinue={() => {}} />);
    expect(screen.getByText(/3 checks on this visit/)).toBeTruthy();
    expect(screen.getByText(/1 photographed for you/)).toBeTruthy();
  });

  it("omits the photo clause entirely when nothing is photographed", () => {
    renderWithProviders(
      <ServiceChecklistCard checklist={checklist({ photoPoints: 0 })} onContinue={() => {}} />,
    );
    expect(screen.getByText(/3 checks on this visit/)).toBeTruthy();
    expect(screen.queryByText(/photographed for you/)).toBeNull();
  });

  it("reveals every authored point, grouped under its real section heading", async () => {
    renderWithProviders(<ServiceChecklistCard checklist={checklist()} onContinue={() => {}} />);
    // Points arrive one at a time; wait for the LAST one rather than a frame.
    await waitFor(
      () => expect(screen.getByText("Left the work area clean")).toBeTruthy(),
      { timeout: REVEAL_BUDGET_MS },
    );
    expect(screen.getByText("Confirmed the reported problem")).toBeTruthy();
    expect(screen.getByText("Photographed the unit")).toBeTruthy();
    expect(screen.getByText("Before starting")).toBeTruthy();
    expect(screen.getByText("Before leaving")).toBeTruthy();
  });

  it("never invents a point that was not in the checklist", async () => {
    renderWithProviders(<ServiceChecklistCard checklist={checklist()} onContinue={() => {}} />);
    await waitFor(
      () => expect(screen.getByText("Left the work area clean")).toBeTruthy(),
      { timeout: REVEAL_BUDGET_MS },
    );
    // A plausible-sounding step the backend did NOT author must not appear.
    expect(screen.queryByText(/gas pressure/i)).toBeNull();
    expect(screen.queryByText(/warranty/i)).toBeNull();
  });

  it("continues the flow when the customer accepts the list", () => {
    const onContinue = jest.fn();
    renderWithProviders(<ServiceChecklistCard checklist={checklist()} onContinue={onContinue} />);
    fireEvent.press(screen.getByLabelText("Continue"));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });
});
