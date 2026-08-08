import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react-native";
import { AppProviders } from "../../../providers/AppProviders";
import { ReviewAndConfirmPhase } from "../ReviewAndConfirmPhase";
import * as controllerModule from "../../booking-review/useBookingReviewController";
import * as checklistModule from "../useServiceChecklist";

jest.mock("../../booking-review/useBookingReviewController");
jest.mock("../useServiceChecklist");

/**
 * Regression: "Rendered more hooks than during the previous render".
 *
 * The confirm-phase useEffect originally sat BELOW `if (loading) return ...`, so
 * on a loading render it was never reached and on the next render it was --
 * React counts hooks per render and threw the moment the summary finished
 * loading, taking the whole booking screen down.
 *
 * This renders the component in the loading state and then transitions it to
 * ready, which is precisely the sequence that crashed. Any hook that drifts back
 * below an early return fails here.
 */
/** renderWithProviders wraps the ROOT, so RNTL's `update` would replace the
 * providers along with the subtree. These tests re-render deliberately (that is
 * the whole point), so they compose the wrapper themselves. */
function renderPhase(props: Record<string, unknown>) {
  const tree = (p: Record<string, unknown>) => (
    <AppProviders>
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <ReviewAndConfirmPhase {...(p as any)} />
    </AppProviders>
  );
  const view = render(tree(props));
  return { ...view, rerenderPhase: (p: Record<string, unknown>) => view.update(tree(p)) };
}

function controllerState(overrides: Record<string, unknown> = {}) {
  return {
    uiState: "loading",
    loadStage: "checking_details",
    summary: null,
    confirmation: null,
    eligibility: { allowed: true, reasons: [] },
    errorMessage: null,
    availableSlots: null,
    slotsLoading: false,
    slotSelectionError: null,
    retry: jest.fn(),
    confirm: jest.fn(),
    addPhoto: jest.fn(),
    removePhoto: jest.fn(),
    loadAvailableSlots: jest.fn(),
    selectSlot: jest.fn(),
    ...overrides,
  };
}

const READY_SUMMARY = {
  draftId: "d1",
  categoryName: null,
  offeringName: "AC Service",
  jobTypeLabel: null,
  issueSummary: "Not cooling",
  answers: [],
  address: { city: "Ludhiana", zipcode: "141002", lines: [], serviceable: true, serviceabilityStatus: null },
  priceState: { kind: "inspection_based" },
  inspection: null,
  bargainAvailable: false,
  provider: null,
  photoCount: 0,
  photoUrls: [],
  preferredDate: null,
  promisedSlot: null,
  serviceSlaMinutes: null,
  serviceDueAt: null,
  isEmergency: false,
  emergencySurcharge: null,
  emergencySurchargePreview: null,
  readyForConfirmation: true,
  missing: [],
};

describe("ReviewAndConfirmPhase — hook order", () => {
  beforeEach(() => {
    (checklistModule.useServiceChecklist as jest.Mock).mockReturnValue({
      checklist: null, loading: false,
    });
  });
  afterEach(() => jest.clearAllMocks());

  it("survives the loading -> ready transition that crashed the screen", async () => {
    (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(controllerState());

    const props = { draftId: "d1", onTrackBooking: jest.fn(), onConfirmPhase: jest.fn() };
    const view = renderPhase(props);

    // Now the summary arrives -- the render that used to throw.
    (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(
      controllerState({ uiState: "ready", loadStage: null, summary: READY_SUMMARY }),
    );

    view.rerenderPhase(props);

    // Asserting on the RENDERED RESULT, not on `not.toThrow()`: an
    // ErrorBoundary catches the hooks error, so a throw-based assertion passed
    // even with the bug reintroduced. If the hook order regresses, the boundary
    // replaces the tree and this content disappears.
    expect(screen.getByText("When should the technician come?")).toBeTruthy();
  });

  it("survives ready -> confirming -> confirmed without a hook-count change", async () => {
    (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(
      controllerState({ uiState: "ready", loadStage: null, summary: READY_SUMMARY }),
    );
    const onConfirmPhase = jest.fn();
    const props = { draftId: "d1", onTrackBooking: jest.fn(), onConfirmPhase };
    const view = renderPhase(props);

    for (const next of [
      controllerState({ uiState: "confirming", loadStage: null, summary: READY_SUMMARY }),
      controllerState({
        uiState: "confirmed", loadStage: null, summary: READY_SUMMARY,
        confirmation: { bookingId: "b1", bookingNumber: "BK-1" },
      }),
    ]) {
      (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(next);
      view.rerenderPhase(props);
    }

    // The screen (not this component) renders the full-bleed layer, so the
    // phase must have been reported up.
    await waitFor(() =>
      expect(onConfirmPhase).toHaveBeenCalledWith(
        expect.objectContaining({ phase: "confirmed", bookingNumber: "BK-1" }),
      ),
    );
  });

  it("reopens the slot turn and withdraws the ready state when the customer goes back", async () => {
    (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(
      controllerState({
        uiState: "ready", loadStage: null,
        // A slot already chosen, so the turn offers Continue.
        summary: {
          ...READY_SUMMARY,
          promisedSlot: { date: "2026-08-09", daysAhead: 1, timeWindow: "14:00-15:00" },
        },
      }),
    );
    const onReviewReady = jest.fn();
    renderPhase({ draftId: "d1", onTrackBooking: jest.fn(), onReviewReady });

    // Walk the turns the way the customer does, so the sheet becomes ready.
    fireEvent.press(screen.getByLabelText("Continue"));
    await waitFor(() => expect(screen.getByText("Add a photo? (optional)")).toBeTruthy());
    fireEvent.press(screen.getByLabelText("Continue"));

    const ready = await waitFor(() => {
      const state = onReviewReady.mock.calls.map(([s]) => s).filter(Boolean).pop();
      expect(state).toBeTruthy();
      return state;
    });

    onReviewReady.mockClear();
    // Leaving the review must withdraw the ready state -- the screen clears its
    // dismissal on that null, which is the only thing that lets the sheet come
    // back after the turn is finished a second time. Without it the customer was
    // left on an empty transcript: no card (all turns done) and no sheet.
    act(() => ready.onEditSlot());

    await waitFor(() => expect(onReviewReady).toHaveBeenCalledWith(null));
    expect(screen.getByText("When should the technician come?")).toBeTruthy();
  });

  it("reports the phase back to null once no longer confirming", async () => {
    (controllerModule.useBookingReviewController as jest.Mock).mockReturnValue(
      controllerState({ uiState: "ready", loadStage: null, summary: READY_SUMMARY }),
    );
    const onConfirmPhase = jest.fn();
    renderPhase({ draftId: "d1", onTrackBooking: jest.fn(), onConfirmPhase });
    await waitFor(() => expect(onConfirmPhase).toHaveBeenCalledWith(null));
  });
});
