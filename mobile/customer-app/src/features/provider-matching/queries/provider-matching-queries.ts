import { useMutation, useQueryClient } from "@tanstack/react-query";
import { providerMatchingApi } from "../api/provider-matching-api";
import { parseProviderMatchResult, type ValidatedProviderMatchResult } from "../domain/provider-match-schema";
import { draftQueryKeys } from "../../booking-draft/queries/draft-queries";
import type { ValidatedBookingDraft } from "../../booking-draft/domain/draft-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

export function useMatchProvider() {
  const queryClient = useQueryClient();
  return useMutation<ValidatedProviderMatchResult, ApiError, string>({
    mutationFn: async (draftId: string) => {
      logger.info("provider_match_started", {});
      const response = await providerMatchingApi.matchAndGetProvider(draftId);
      const parsed = parseProviderMatchResult(response);
      if (!parsed) {
        logger.warn("provider_match_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Provider match response did not match the expected shape." });
      }
      logger.info("provider_match_completed", { badgeCount: parsed.selected_provider.public_badges.length });
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
      logger.warn("provider_match_no_match", {});
    },
  });
}
