import { apiClient } from "../../../api/api-client";

/**
 * Real path verified against
 * app/engines/home_service_booking/customer_router.py — see
 * CUSTOMER-L5-09-contract-matrix.md. Deliberately reuses the exact same
 * `match-and-price` endpoint CUSTOMER-L5-08 already calls — there is no
 * separate estimate/revalidation endpoint (confirmed: the backend has no
 * revalidate/refresh/invalidate method anywhere in this engine). Calling
 * it again is itself the real revalidation mechanism (it always re-derives
 * fresh, see the Idempotency section of CUSTOMER-L5-08's contract-matrix).
 */
export const pricingApi = {
  getEstimate: (draftId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/match-and-price`, undefined, {
      signal: options.signal,
    }),
};
