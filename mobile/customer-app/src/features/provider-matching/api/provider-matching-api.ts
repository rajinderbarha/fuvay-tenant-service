import { apiClient } from "../../../api/api-client";

/**
 * Real path verified against
 * app/engines/home_service_booking/customer_router.py — see
 * CUSTOMER-L5-08-contract-matrix.md. The deprecated list-based
 * `match-providers`/`select-provider` endpoints are never called by this
 * client (confirmed unreachable from any real caller, backend-side).
 */
export const providerMatchingApi = {
  matchAndGetProvider: (draftId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/match-and-price`, undefined, {
      signal: options.signal,
    }),
};
