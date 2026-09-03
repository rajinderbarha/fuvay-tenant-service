import { renderHook, waitFor, act } from "@testing-library/react-native";
import { useBookingReviewController } from "../useBookingReviewController";
import * as reviewApi from "../../../api/bookingReview/bookingReviewApi";
import * as confirmApi from "../../../api/bookingConfirmation/bookingConfirmationApi";
import * as questionFlowApi from "../../../api/questionFlow/questionFlowApi";
import * as idempotency from "../../../api/idempotency/idempotencyStore";

jest.mock("../../../api/bookingReview/bookingReviewApi");
jest.mock("../../../api/bookingConfirmation/bookingConfirmationApi");
jest.mock("../../../api/questionFlow/questionFlowApi");
jest.mock("../../../api/idempotency/idempotencyStore");

const draftId = "draft-1";

function completeEnvelope() {
  return {
    data: {
      envelope_version: 1, session_id: "sess-1", draft_id: draftId, workflow_version: null, question_flow_version: 3,
      scope: { category_id: "cat-1", offering_id: "off-1", job_type_id: "jt-1" },
      current_question: null,
      progress: { answered_count: 3, remaining_count: 0, complete: true },
      next_permitted_actions: ["proceed_to_serviceability"],
    },
  };
}

function draftDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    data: {
      id: draftId, customer_id: "cust-1", ai_session_id: "sess-1", category_id: "cat-1", offering_id: "off-1",
      job_type_id: "jt-1", status: "provider_matched", city: "Ludhiana", zipcode: "141002", issue_summary: "Not cooling",
      serviceability_status: "serviceable", price_status: "estimated", provider_match_status: "matched",
      price_snapshot: null, expires_at: null, created_at: null, updated_at: null,
      category_name: "AC & Cooling", job_type_label: "Repair", photo_urls: ["p1.jpg"],
      ...overrides,
    },
  };
}

function summaryDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    data: {
      booking_summary: {
        offering_name: "AC Repair", issue_summary: "Not cooling", address: { line1: "Model Town" },
        city: "Ludhiana", zipcode: "141002", preferred_date: null, preferred_time_window: null,
        price_estimate: { requires_inspection_estimate: true, visit_fee: 299, customer_message: null },
        selected_provider: { tenant_id: "t-1", provider_name: "CoolFix", public_badges: [{ name: "Verified", icon: "shield-check", color: "#3b82f6" }], rating: 4.5 },
        serviceability: { serviceable: true, status: "serviceable" },
        ready_for_confirmation: true, missing: [], errors: [],
        ...overrides,
      },
      draft_status: "ready_for_confirmation",
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  (questionFlowApi.getQuestionFlow as jest.Mock).mockResolvedValue(completeEnvelope());
  (reviewApi.checkServiceability as jest.Mock).mockResolvedValue({ data: { serviceable: true, message: "ok", draft_status: "serviceability_checked" } });
  (reviewApi.matchAndPrice as jest.Mock).mockResolvedValue({
    data: { selected_provider: { tenant_id: "t-1", provider_name: "CoolFix", public_badges: [{ name: "Verified", icon: "shield-check", color: "#3b82f6" }] }, standard_price: 499, price_snapshot: { requires_inspection_estimate: false, standard_price: 499 } },
  });
  (reviewApi.confirmPriceChoice as jest.Mock).mockResolvedValue({ data: { booking_summary: {}, draft_status: "provider_matched" } });
  (reviewApi.getDraft as jest.Mock).mockResolvedValue(draftDto());
  (reviewApi.buildBookingSummary as jest.Mock).mockResolvedValue(summaryDto());
  (idempotency.getOrCreateIdempotencyKey as jest.Mock).mockResolvedValue("idem-key-1");
  (idempotency.clearIdempotencyKey as jest.Mock).mockResolvedValue(undefined);
});

describe("useBookingReviewController", () => {
  it("runs the full load sequence and lands on a ready review with an inspection price", async () => {
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    expect(questionFlowApi.getQuestionFlow).toHaveBeenCalledWith(draftId);
    expect(reviewApi.checkServiceability).toHaveBeenCalledWith(draftId);
    expect(reviewApi.matchAndPrice).toHaveBeenCalledWith(draftId);
    expect(reviewApi.confirmPriceChoice).toHaveBeenCalledWith(draftId, "standard");
    expect(result.current.summary?.priceState).toEqual({ kind: "inspection_based" });
    expect(result.current.summary?.inspection?.visitFee).toEqual({ minorUnits: 29900, currency: "INR" });
    expect(result.current.eligibility).toEqual({ allowed: true });
  });

  it("reloads and binds every action to a replacement draft id", async () => {
    const { result, rerender } = renderHook(
      ({ id }) => useBookingReviewController(id),
      { initialProps: { id: draftId } },
    );
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    rerender({ id: "draft-2" });
    await waitFor(() => expect(questionFlowApi.getQuestionFlow).toHaveBeenCalledWith("draft-2"));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    (reviewApi.selectSlot as jest.Mock).mockResolvedValue(summaryDto({
      preferred_date: "2026-08-25",
      preferred_time_window: "10:00-11:00",
    }));
    await act(async () => {
      await result.current.selectSlot("2026-08-25", "10:00-11:00", false);
    });
    expect(reviewApi.selectSlot).toHaveBeenCalledWith(
      "draft-2", "2026-08-25", "10:00-11:00", false,
    );
  });

  it("blocks with draft_incomplete when the question flow is not yet complete, never calling match-and-price", async () => {
    (questionFlowApi.getQuestionFlow as jest.Mock).mockResolvedValue({
      data: { ...completeEnvelope().data, current_question: { question_id: "q-2", question_key: "brand", question_type: "single_select", text: "Brand?", help_text: null, required: true, options: [], photo_capable: false }, progress: { answered_count: 2, remaining_count: 1, complete: false } },
    });
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("blocked"));
    expect(result.current.blockedReason).toBe("draft_incomplete");
    expect(reviewApi.matchAndPrice).not.toHaveBeenCalled();
  });

  it("blocks with unserviceable when serviceability fails, never proceeding to matching", async () => {
    (reviewApi.checkServiceability as jest.Mock).mockResolvedValue({ data: { serviceable: false, message: "no", draft_status: "serviceability_checked" } });
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("blocked"));
    expect(result.current.blockedReason).toBe("unserviceable");
    expect(reviewApi.matchAndPrice).not.toHaveBeenCalled();
  });

  it("surfaces pricing_unavailable when a non-inspection booking has no fixed price", async () => {
    (reviewApi.matchAndPrice as jest.Mock).mockResolvedValue({
      data: { selected_provider: { tenant_id: "t-1", provider_name: "CoolFix", public_badges: [] }, standard_price: null },
    });
    (reviewApi.buildBookingSummary as jest.Mock).mockResolvedValue(summaryDto({ price_estimate: { requires_inspection_estimate: false, standard_price: null }, ready_for_confirmation: false }));
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(reviewApi.confirmPriceChoice).not.toHaveBeenCalled();
    expect(result.current.eligibility).toEqual({ allowed: false, reason: "pricing_unavailable" });
  });

  it("confirms exactly once, reuses the idempotency key, and clears it only after success", async () => {
    (confirmApi.confirmDraft as jest.Mock).mockResolvedValue({ data: { booking_number: "SB-1", booking_id: "b-1", idempotent: false } });
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.confirm(); });

    expect(idempotency.getOrCreateIdempotencyKey).toHaveBeenCalledWith(`booking-confirm:${draftId}`);
    expect(confirmApi.confirmDraft).toHaveBeenCalledTimes(1);
    expect(confirmApi.confirmDraft).toHaveBeenCalledWith(draftId, "idem-key-1");
    expect(idempotency.clearIdempotencyKey).toHaveBeenCalledWith(`booking-confirm:${draftId}`);
    expect(result.current.uiState).toBe("confirmed");
    expect(result.current.confirmation).toEqual({ bookingId: "b-1", bookingNumber: "SB-1", idempotent: false });
  });

  it("never calls confirm when eligibility is blocked (double-tap-safe by construction)", async () => {
    (reviewApi.buildBookingSummary as jest.Mock).mockResolvedValue(summaryDto({ ready_for_confirmation: false }));
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.confirm(); });

    expect(confirmApi.confirmDraft).not.toHaveBeenCalled();
    expect(result.current.uiState).toBe("ready");
  });

  it("ignores a second confirm() call fired while the first is still in flight (real concurrent double-tap)", async () => {
    // Never resolves within this test -- simulates a genuine in-flight
    // confirm request, so a second tap arriving before the first settles
    // must be dropped by the busyRef guard, not queued or sent twice.
    let resolveConfirm: (v: { data: unknown }) => void;
    const pending = new Promise<{ data: unknown }>(resolve => { resolveConfirm = resolve; });
    (confirmApi.confirmDraft as jest.Mock).mockReturnValue(pending);

    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    act(() => {
      result.current.confirm();
      result.current.confirm();
    });

    await waitFor(() => expect(result.current.uiState).toBe("confirming"));
    expect(confirmApi.confirmDraft).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveConfirm({ data: { booking_number: "SB-1", booking_id: "b-1", idempotent: false } });
    });
    await waitFor(() => expect(result.current.uiState).toBe("confirmed"));
    expect(confirmApi.confirmDraft).toHaveBeenCalledTimes(1);
  });

  it("re-enables confirmation controls after a recoverable confirm error", async () => {
    const { DomainError } = jest.requireActual("../../../domain/errors");
    (confirmApi.confirmDraft as jest.Mock).mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "Price changed, please retry." }),
    );
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.confirm(); });

    await waitFor(() => expect(result.current.uiState).toBe("recoverable_error"));
    expect(result.current.errorMessage).toBe("Price changed, please retry.");

    // Controls must genuinely re-enable -- a second confirm() attempt
    // must be allowed to go through, not be permanently stuck busy.
    (confirmApi.confirmDraft as jest.Mock).mockResolvedValue({ data: { booking_number: "SB-2", booking_id: "b-2", idempotent: false } });
    await act(async () => { await result.current.retry(); });
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.confirm(); });
    await waitFor(() => expect(result.current.uiState).toBe("confirmed"));
    expect(confirmApi.confirmDraft).toHaveBeenCalledTimes(2);
  });

  it("never calls confirm-price-choice for an inspection-mode offering (standard_price null) -- the ₹0 Booking Review regression", async () => {
    // AC Gas Refilling's real shape after the pricing-contract fix:
    // match-and-price returns standard_price=null (never 0) for an
    // inspection-mode offering. The controller must skip confirm-price-
    // choice entirely rather than calling it with a tier that doesn't
    // apply, and the summary already carries ready_for_confirmation=true
    // without any selected_price_tier.
    (reviewApi.matchAndPrice as jest.Mock).mockResolvedValue({
      data: { selected_provider: { tenant_id: "t-1", provider_name: "Guramrit", public_badges: [] }, standard_price: null },
    });
    (reviewApi.buildBookingSummary as jest.Mock).mockResolvedValue(summaryDto({
      price_estimate: { requires_inspection_estimate: true, visit_fee: 299, customer_message: null, standard_price: null },
      ready_for_confirmation: true,
    }));
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    expect(reviewApi.confirmPriceChoice).not.toHaveBeenCalled();
    expect(result.current.summary?.priceState).toEqual({ kind: "inspection_based" });
    expect(result.current.summary?.inspection?.visitFee).toEqual({ minorUnits: 29900, currency: "INR" });
    expect(result.current.eligibility).toEqual({ allowed: true });
  });

  it("distinguishes a pricing-configuration failure (PRICE_OPTIONS_UNAVAILABLE) from a genuine no-provider failure at match-and-price", async () => {
    const { DomainError } = jest.requireActual("../../../domain/errors");
    (reviewApi.matchAndPrice as jest.Mock).mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "no valid price", telemetryMeta: { backendCode: "PRICE_OPTIONS_UNAVAILABLE" } }),
    );
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("blocked"));
    expect(result.current.blockedReason).toBe("pricing_unavailable");
  });

  it("still reports no_provider for a genuine no-eligible-provider match-and-price failure", async () => {
    const { DomainError } = jest.requireActual("../../../domain/errors");
    (reviewApi.matchAndPrice as jest.Mock).mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "no provider", telemetryMeta: { backendCode: "HOME_BOOKING_NO_PROVIDER_AVAILABLE" } }),
    );
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("blocked"));
    expect(result.current.blockedReason).toBe("no_provider");
  });

  it("passes the emergency flag through to both the list and select-slot API calls", async () => {
    (reviewApi.getAvailableSlots as jest.Mock).mockResolvedValue({ data: { slots: [] } });
    (reviewApi.selectSlot as jest.Mock).mockResolvedValue(summaryDto());
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.loadAvailableSlots(true); });
    expect(reviewApi.getAvailableSlots).toHaveBeenCalledWith(draftId, true);

    await act(async () => { await result.current.selectSlot("2026-08-10", "10:00-11:00", true); });
    expect(reviewApi.selectSlot).toHaveBeenCalledWith(draftId, "2026-08-10", "10:00-11:00", true);
  });

  it("defaults emergency to false when the caller omits it", async () => {
    (reviewApi.getAvailableSlots as jest.Mock).mockResolvedValue({ data: { slots: [] } });
    const { result } = renderHook(() => useBookingReviewController(draftId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    await act(async () => { await result.current.loadAvailableSlots(); });
    expect(reviewApi.getAvailableSlots).toHaveBeenCalledWith(draftId, false);
  });

  it("maps every load stage to the correct, semantically-accurate activity label (not a reused question-flow label)", async () => {
    const { bookingReviewLoadLabel } = jest.requireActual("../useBookingReviewController");
    expect(bookingReviewLoadLabel("checking_details")).toBe("Checking your booking details…");
    expect(bookingReviewLoadLabel("checking_serviceability")).toBe("Confirming service availability…");
    // Customer-facing wording -- these labels are shown in the booking chat,
    // so they must never name internal architecture (was "backend pricing").
    expect(bookingReviewLoadLabel("checking_pricing")).toBe("Checking the price for you…");
    expect(bookingReviewLoadLabel("finding_provider")).toBe("Finding an eligible professional…");
    expect(bookingReviewLoadLabel("preparing_review")).toBe("Preparing your review…");
  });
});
