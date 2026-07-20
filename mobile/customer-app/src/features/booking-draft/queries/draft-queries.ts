import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { draftApi } from "../api/draft-api";
import { parseBookingDraft, parseCancelResponse, parseLinkPhotoResponse, type ValidatedBookingDraft } from "../domain/draft-schema";
import { parseServiceabilityResult } from "../domain/serviceability-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

/** Customer isolation comes from the backend (ownership-enforced on every draft endpoint) — the key still scopes by locale/tenant defensively, matching every previous sprint's pattern. */
export const draftQueryKeys = {
  detail: (draftId: string, locale: string, tenantId: string | undefined) => ["bookingDraft", "detail", draftId, locale, tenantId ?? "no-tenant"] as const,
};

export function useDraft(draftId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedBookingDraft>({
    queryKey: draftQueryKeys.detail(draftId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await draftApi.getDraft(draftId as string, { signal });
      const parsed = parseBookingDraft(response);
      if (!parsed) {
        logger.warn("draft_restore_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Draft response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: Boolean(draftId),
    staleTime: 0,
    retry: 1,
  });
}

export function useCreateDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { categorySlug: string; offeringSlug: string; aiSessionId?: string }) => {
      logger.info("draft_create_started", {});
      const response = await draftApi.createDraft(params);
      const parsed = parseBookingDraft(response);
      if (!parsed) {
        logger.warn("draft_create_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Draft creation response did not match the expected shape." });
      }
      logger.info("draft_create_succeeded", {});
      return parsed;
    },
    onSuccess: (draft) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      queryClient.setQueryData(draftQueryKeys.detail(draft.id, locale, tenantId), draft);
    },
  });
}

export function useUpdateDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { draftId: string; payload: Record<string, unknown> }) => {
      const response = await draftApi.updateDraft(params.draftId, params.payload);
      const parsed = parseBookingDraft(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Draft update response did not match the expected shape." });
      return parsed;
    },
    onSuccess: (draft) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      queryClient.setQueryData(draftQueryKeys.detail(draft.id, locale, tenantId), draft);
    },
  });
}

export function useCancelDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { draftId: string; reason?: string }) => {
      const response = await draftApi.cancelDraft(params.draftId, params.reason);
      const parsed = parseCancelResponse(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Cancel response did not match the expected shape." });
      return parsed;
    },
    onSuccess: (_result, variables) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      void queryClient.invalidateQueries({ queryKey: draftQueryKeys.detail(variables.draftId, locale, tenantId) });
    },
  });
}

export function useCheckServiceability() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (draftId: string) => {
      logger.info("serviceability_check_started", {});
      const response = await draftApi.checkServiceability(draftId);
      const parsed = parseServiceabilityResult(response);
      if (!parsed) {
        logger.warn("serviceability_check_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Serviceability response did not match the expected shape." });
      }
      logger.info("serviceability_check_completed", { serviceable: parsed.serviceable, matchedBy: parsed.matched_by });
      return parsed;
    },
    onSuccess: (result, draftId) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      queryClient.setQueryData<ValidatedBookingDraft | undefined>(draftQueryKeys.detail(draftId, locale, tenantId), (prev) =>
        prev ? { ...prev, status: result.draft_status, serviceability_status: result.serviceable ? "serviceable" : "not_serviceable" } : prev
      );
    },
  });
}

export function useLinkDraftPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { draftId: string; photoUrl: string; contentType: string }) => {
      const response = await draftApi.linkPhoto(params.draftId, params.photoUrl, params.contentType);
      const parsed = parseLinkPhotoResponse(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Photo-link response did not match the expected shape." });
      return parsed;
    },
    onSuccess: (result, variables) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      queryClient.setQueryData<ValidatedBookingDraft | undefined>(draftQueryKeys.detail(variables.draftId, locale, tenantId), (prev) =>
        prev ? { ...prev, photo_urls: result.photo_urls, status: result.draft_status } : prev
      );
    },
  });
}
