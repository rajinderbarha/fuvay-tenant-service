import { apiClient } from "../../../api/api-client";

export interface LocalFilePart {
  uri: string;
  name: string;
  type: string;
}

const BOOKING_ISSUE_PHOTO_CONTEXT = "booking_issue_photo";
const DRAFT_OWNER_TYPE = "booking_draft";

/**
 * Real backend paths verified against app/engines/media/new_router.py (the
 * Phase 0A engine — authoritative; the legacy signed-URL flow at
 * app/engines/media/router.py is deliberately not used) — see
 * CUSTOMER-L5-06-contract-matrix.md. `media_context="booking_issue_photo"`
 * is a real, already access-controlled context (customer-scoped,
 * server-side) that no caller in this codebase used before this sprint.
 */
export const mediaApi = {
  uploadBookingPhoto: (draftId: string, file: LocalFilePart, options: { signal?: AbortSignal } = {}) => {
    const form = new FormData();
    // React Native's FormData accepts this {uri, name, type} shape for file parts.
    form.append("file", file as unknown as Blob);
    form.append("media_context", BOOKING_ISSUE_PHOTO_CONTEXT);
    form.append("owner_type", DRAFT_OWNER_TYPE);
    form.append("owner_id", draftId);
    form.append("is_public", "false");
    return apiClient.uploadMultipart<unknown>("/v1/media/upload", form, { signal: options.signal });
  },

  listDraftMedia: (draftId: string, options: { signal?: AbortSignal } = {}) => {
    const query = new URLSearchParams({ media_context: BOOKING_ISSUE_PHOTO_CONTEXT, owner_type: DRAFT_OWNER_TYPE, owner_id: draftId, page_size: "25" });
    return apiClient.get<unknown>(`/v1/media?${query.toString()}`, { signal: options.signal });
  },

  replaceMedia: (mediaId: string, file: LocalFilePart, options: { signal?: AbortSignal } = {}) => {
    const form = new FormData();
    form.append("file", file as unknown as Blob);
    form.append("is_public", "false");
    return apiClient.uploadMultipart<unknown>(`/v1/media/${encodeURIComponent(mediaId)}/replace`, form, { signal: options.signal });
  },

  deleteMedia: (mediaId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.delete<unknown>(`/v1/media/${encodeURIComponent(mediaId)}`, { signal: options.signal }),
};
