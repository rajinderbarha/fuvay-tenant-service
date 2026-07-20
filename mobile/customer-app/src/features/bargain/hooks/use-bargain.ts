import { useEffect, useRef, useState } from "react";
import { useDraft } from "../../booking-draft/queries/draft-queries";
import { useCalculatePriceEstimate } from "../../pricing/queries/pricing-queries";
import { evaluatePricingPreflight } from "../../pricing/domain/pricing-preflight";
import { useConfirmPriceChoice } from "../queries/bargain-queries";
import type { PriceTier } from "../domain/bargain-schema";
import { deriveBargainState } from "../domain/bargain-state";

/**
 * Composes the draft, the real preflight check, a fresh price-estimate
 * fetch (reusing CUSTOMER-L5-09's `useCalculatePriceEstimate` — the same
 * real `match-and-price` endpoint, re-derived fresh so the tier choice is
 * always made against the current price, never a stale one carried over
 * from the pricing screen), and the real `confirm-price-choice` mutation.
 * See CUSTOMER-L5-10-bargain-architecture.md for why re-fetching here
 * (rather than passing the previous screen's numbers via route params) is
 * the correct, honest design.
 */
export function useBargain(draftId: string) {
  const draftQuery = useDraft(draftId);
  const estimateMutation = useCalculatePriceEstimate();
  const confirmMutation = useConfirmPriceChoice();
  const hasTriggered = useRef(false);
  const [selectedTier, setSelectedTier] = useState<PriceTier | null>(null);

  const preflight = evaluatePricingPreflight(draftQuery.data);

  useEffect(() => {
    if (preflight.ready && !hasTriggered.current && estimateMutation.isIdle) {
      hasTriggered.current = true;
      estimateMutation.mutate(draftId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once preflight first becomes ready.
  }, [preflight.ready]);

  function chooseTier(tier: PriceTier) {
    setSelectedTier(tier);
    confirmMutation.mutate({ draftId, tier });
  }

  function changeSelection() {
    setSelectedTier(null);
    confirmMutation.reset();
  }

  const state = deriveBargainState({
    preflightReasonKey: preflight.ready ? null : preflight.reasonKey,
    estimate: estimateMutation,
    confirm: confirmMutation,
    selectedTier,
  });

  return {
    state,
    chooseTier,
    changeSelection,
    refreshEstimate: () => estimateMutation.mutate(draftId),
  };
}
