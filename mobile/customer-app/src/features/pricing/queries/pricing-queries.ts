import { useMutation, useQueryClient } from "@tanstack/react-query";
import { pricingApi } from "../api/pricing-api";
import { parsePriceEstimateResult, type ValidatedPriceEstimateResult } from "../domain/pricing-schema";
import { draftQueryKeys } from "../../booking-draft/queries/draft-queries";
import type { ValidatedBookingDraft } from "../../booking-draft/domain/draft-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/**
 * A mutation, not a query — mirrors `useMatchProvider`/`useCheckServiceability`
 * exactly (see CUSTOMER-L5-09-pricing-architecture.md). There is no
 * GET-able "current estimate" resource; every call re-derives fresh.
 */
export function useCalculatePriceEstimate() {
  const queryClient = useQueryClient();
  return useMutation<ValidatedPriceEstimateResult, ApiError, string>({
    mutationFn: async (draftId: string) => {
      logger.info("pricing_calculation_started", {});
      const response = await pricingApi.getEstimate(draftId);
      const parsed = parsePriceEstimateResult(response);
      if (!parsed) {
        logger.warn("pricing_calculation_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Price estimate response did not match the expected shape." });
      }
      logger.info("pricing_calculation_succeeded", { currency: parsed.selected_provider_price_options.currency });
      return parsed;
    },
    onSuccess: (result, draftId) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      queryClient.setQueryData<ValidatedBookingDraft | undefined>(draftQueryKeys.detail(draftId, locale, tenantId), (prev) =>
        prev ? { ...prev, status: result.draft_status, selected_tenant_id: result.selected_provider.tenant_id, provider_match_status: "matched" } : prev
      );
    },
    onError: () => {
      logger.warn("pricing_calculation_error", {});
    },
  });
}
