import { useEffect, useRef } from "react";
import { useDraft } from "../../booking-draft/queries/draft-queries";
import { evaluatePricingPreflight } from "../../pricing/domain/pricing-preflight";
import { useBookingReview } from "../queries/booking-confirmation-queries";
import { deriveReviewState } from "../domain/booking-state";

/**
 * Composes the draft, the real preflight check (reused from
 * CUSTOMER-L5-09 — draft exists/not expired/address selected/serviceable/
 * provider matched), and the real `/summary` mutation. Auto-triggers once
 * preflight passes, mirroring every previous sprint's established
 * auto-run-once pattern, then exposes an explicit `refresh` for a fresh
 * summary (e.g. after editing an earlier section and returning).
 */
export function useBookingReviewFlow(draftId: string) {
  const draftQuery = useDraft(draftId);
  const reviewMutation = useBookingReview();
  const hasTriggered = useRef(false);

  const preflight = evaluatePricingPreflight(draftQuery.data);

  useEffect(() => {
    if (preflight.ready && !hasTriggered.current && reviewMutation.isIdle) {
      hasTriggered.current = true;
      reviewMutation.mutate(draftId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once preflight first becomes ready.
  }, [preflight.ready]);

  const state = deriveReviewState({
    preflightReasonKey: preflight.ready ? null : preflight.reasonKey,
    review: reviewMutation,
  });

  return { state, refresh: () => reviewMutation.mutate(draftId) };
}
