import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { mediaApi, type LocalFilePart } from "../api/media-api";
import { parseUploadResponse, parseMediaAssetList, parseDeleteResponse, parseReplaceResponse, type ValidatedMediaAsset } from "../domain/media-asset-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

export const mediaQueryKeys = {
  draftMedia: (draftId: string, locale: string, tenantId: string | undefined) => ["bookingMedia", "list", draftId, locale, tenantId ?? "no-tenant"] as const,
};

export function useDraftMedia(draftId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery<ValidatedMediaAsset[]>({
    queryKey: mediaQueryKeys.draftMedia(draftId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await mediaApi.listDraftMedia(draftId as string, { signal });
      const parsed = parseMediaAssetList(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Media list response did not match the expected shape." });
      if (parsed.droppedCount > 0) logger.warn("media_list_items_dropped", { droppedCount: parsed.droppedCount });
      return parsed.items;
    },
    enabled: Boolean(draftId),
    staleTime: 30_000,
  });
}

export function useUploadBookingPhoto() {
  return useMutation({
    mutationFn: async (params: { draftId: string; file: LocalFilePart }) => {
      logger.info("upload_started", { fileSizeBucket: undefined });
      const response = await mediaApi.uploadBookingPhoto(params.draftId, params.file);
      const parsed = parseUploadResponse(response);
      if (!parsed) {
        logger.warn("upload_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Upload response did not match the expected shape." });
      }
      logger.info("upload_finalization_succeeded", { mediaAssetId: parsed.id });
      return parsed;
    },
  });
}

export function useDeleteMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { mediaId: string; draftId: string }) => {
      const response = await mediaApi.deleteMedia(params.mediaId);
      const parsed = parseDeleteResponse(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Delete response did not match the expected shape." });
      return parsed;
    },
    onSuccess: (_result, variables) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      void queryClient.invalidateQueries({ queryKey: mediaQueryKeys.draftMedia(variables.draftId, locale, tenantId) });
    },
  });
}

export function useReplaceMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { mediaId: string; draftId: string; file: LocalFilePart }) => {
      const response = await mediaApi.replaceMedia(params.mediaId, params.file);
      const parsed = parseReplaceResponse(response);
      if (!parsed) throw new ApiError({ category: "validation_error", message: "Replace response did not match the expected shape." });
      return parsed;
    },
    onSuccess: (_result, variables) => {
      const locale = getRequestLocale();
      const tenantId = getRequestTenantId();
      void queryClient.invalidateQueries({ queryKey: mediaQueryKeys.draftMedia(variables.draftId, locale, tenantId) });
    },
  });
}
