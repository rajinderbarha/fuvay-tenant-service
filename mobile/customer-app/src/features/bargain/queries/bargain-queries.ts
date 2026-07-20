import { useMutation } from "@tanstack/react-query";
import { bargainApi } from "../api/bargain-api";
import { parseConfirmPriceChoiceResult, type ValidatedConfirmPriceChoiceResult, type PriceTier } from "../domain/bargain-schema";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/**
 * A mutation, not a query — there is no GET-able "current selection"
 * resource; the real endpoint both resolves and persists in one call
 * (CUSTOMER-L5-10-contract-matrix.md). Real, confirmed-safe to call
 * repeatedly with a different tier (the honest equivalent of "revise your
 * choice") — so, unlike `useCalculatePriceEstimate`, this mutation is
 * intentionally invoked more than once per screen visit when the customer
 * changes their mind, not just once on mount.
 */
export function useConfirmPriceChoice() {
  return useMutation<ValidatedConfirmPriceChoiceResult, ApiError, { draftId: string; tier: PriceTier }>({
    mutationFn: async ({ draftId, tier }) => {
      logger.info("bargain_offer_submit_started", { tier });
      const response = await bargainApi.confirmPriceChoice(draftId, tier);
      const parsed = parseConfirmPriceChoiceResult(response);
      if (!parsed) {
        logger.warn("bargain_offer_submit_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Confirm-price-choice response did not match the expected shape." });
      }
      logger.info("bargain_offer_submit_succeeded", { tier: parsed.booking_summary.selected_price_tier });
      return parsed;
    },
    onError: () => {
      logger.warn("bargain_offer_submit_error", {});
    },
  });
}
