import { deriveReviewState, categorizeConfirmFailure, type ReviewMutationSnapshot } from "../booking-state";

const readySummary = { ready_for_confirmation: true };
const notReadySummary = { ready_for_confirmation: false };

const idle: ReviewMutationSnapshot = { isIdle: true, isPending: false, isError: false };
const pending: ReviewMutationSnapshot = { isIdle: false, isPending: true, isError: false };
const errored: ReviewMutationSnapshot = { isIdle: false, isPending: false, isError: true };
const readyResult: ReviewMutationSnapshot = { isIdle: false, isPending: false, isError: false, data: { booking_summary: readySummary } };
const notReadyResult: ReviewMutationSnapshot = { isIdle: false, isPending: false, isError: false, data: { booking_summary: notReadySummary } };

describe("deriveReviewState", () => {
  it("returns preflight_failed before considering the review mutation at all", () => {
    const state = deriveReviewState({ preflightReasonKey: "pricing.preflight.draftExpired", review: idle });
    expect(state).toEqual({ kind: "preflight_failed", reasonKey: "pricing.preflight.draftExpired" });
  });

  it("returns loading while idle or pending", () => {
    expect(deriveReviewState({ preflightReasonKey: null, review: idle })).toEqual({ kind: "loading" });
    expect(deriveReviewState({ preflightReasonKey: null, review: pending })).toEqual({ kind: "loading" });
  });

  it("returns unavailable on a real fetch error", () => {
    expect(deriveReviewState({ preflightReasonKey: null, review: errored })).toEqual({ kind: "unavailable" });
  });

  it("returns ready when the real ready_for_confirmation flag is true", () => {
    expect(deriveReviewState({ preflightReasonKey: null, review: readyResult })).toEqual({ kind: "ready", summary: readySummary });
  });

  it("returns not_ready when the real ready_for_confirmation flag is false — never fabricates readiness", () => {
    expect(deriveReviewState({ preflightReasonKey: null, review: notReadyResult })).toEqual({ kind: "not_ready", summary: notReadySummary });
  });
});

describe("categorizeConfirmFailure", () => {
  it("treats timeout/network/server/unknown/maintenance/rate-limited as uncertain (may have committed)", () => {
    for (const category of ["timeout", "network_error", "server_error", "unknown_error", "maintenance", "rate_limited"] as const) {
      expect(categorizeConfirmFailure(category)).toBe("uncertain");
    }
  });

  it("treats validation/not-found/forbidden/conflict as failed (certainly did not commit)", () => {
    for (const category of ["validation_error", "not_found", "forbidden", "conflict"] as const) {
      expect(categorizeConfirmFailure(category)).toBe("failed");
    }
  });
});
