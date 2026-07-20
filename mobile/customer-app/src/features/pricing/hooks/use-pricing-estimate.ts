import { useEffect, useRef, useState } from "react";
import { useDraft } from "../../booking-draft/queries/draft-queries";
import { useCalculatePriceEstimate } from "../queries/pricing-queries";
import { evaluatePricingPreflight } from "../domain/pricing-preflight";
import { derivePricingState, type PricingState } from "../domain/pricing-state";
import type { ValidatedPriceOptions } from "../domain/pricing-schema";

/**
 * Composes the draft, the real preflight check, and the real
 * `match-and-price` mutation into one testable state machine
 * (CUSTOMER-L5-09 §38). Auto-triggers the first calculation once preflight
 * passes, exactly mirroring `ServiceabilityScreen`/`ProviderPreviewScreen`'s
 * established auto-run-once pattern — then exposes an explicit `refresh`
 * action for manual revalidation (the real backend has no separate
 * revalidate endpoint; refresh simply re-calls the same real mutation).
 */
export function usePricingEstimate(draftId: string) {
  const draftQuery = useDraft(draftId);
  const estimateMutation = useCalculatePriceEstimate();
  const previousOptions = useRef<ValidatedPriceOptions | null>(null);
  const hasTriggered = useRef(false);
  const [hasCalculatedBefore, setHasCalculatedBefore] = useState(false);

  const preflight = evaluatePricingPreflight(draftQuery.data);

  useEffect(() => {
    if (preflight.ready && !hasTriggered.current && estimateMutation.isIdle) {
      hasTriggered.current = true;
      estimateMutation.mutate(draftId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once preflight first becomes ready.
  }, [preflight.ready]);

  useEffect(() => {
    if (estimateMutation.isSuccess && estimateMutation.data) {
      setHasCalculatedBefore(true);
    }
  }, [estimateMutation.isSuccess, estimateMutation.data]);

  const state: PricingState = derivePricingState({
    preflightReasonKey: preflight.ready ? null : preflight.reasonKey,
    mutation: estimateMutation,
    hasCalculatedBefore,
    previousOptions: previousOptions.current,
  });

  if (state.kind === "ready") {
    previousOptions.current = state.options;
  }

  return {
    state,
    refresh: () => estimateMutation.mutate(draftId),
  };
}
