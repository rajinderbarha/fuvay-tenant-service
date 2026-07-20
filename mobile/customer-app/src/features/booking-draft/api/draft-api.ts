import { apiClient } from "../../../api/api-client";

/**
 * Real backend paths verified against
 * app/engines/home_service_booking/customer_router.py — see
 * CUSTOMER-L5-06-contract-matrix.md. `offering_slug` here refers to the
 * `admin_catalog` engine's `MasterService.slug`, not the `customer_flow`
 * engine's `MasterOffering.slug` that CUSTOMER-L5-04's real service-detail
 * screen uses — the two catalogs are unrelated tables with no confirmed
 * bridge. This client passes the real, already-fetched `service.slug`
 * through faithfully; a 422 `HOME_BOOKING_OFFERING_INVALID` is a real,
 * expected possible outcome, not a bug in this client.
 */
export const draftApi = {
  createDraft: (params: { categorySlug: string; offeringSlug: string; aiSessionId?: string }, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(
      "/v1/customer/home-services/booking-drafts",
      { category_slug: params.categorySlug, offering_slug: params.offeringSlug, ai_session_id: params.aiSessionId },
      { signal: options.signal }
    ),

  getDraft: (draftId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}`, { signal: options.signal }),

  updateDraft: (draftId: string, payload: Record<string, unknown>, options: { signal?: AbortSignal } = {}) =>
    apiClient.put<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}`, payload, { signal: options.signal }),

  cancelDraft: (draftId: string, reason?: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/cancel`, { reason }, { signal: options.signal }),

  linkPhoto: (draftId: string, photoUrl: string, contentType: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(
      `/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/photos`,
      { photo_url: photoUrl, content_type: contentType },
      { signal: options.signal }
    ),

  /** Real, ID-space-correct serviceability check — see CUSTOMER-L5-07-contract-matrix.md. */
  checkServiceability: (draftId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/serviceability-check`, undefined, {
      signal: options.signal,
    }),
};
