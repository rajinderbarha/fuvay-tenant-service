import { apiClient } from "../../../api/api-client";

/**
 * Real paths verified against
 * app/engines/home_service_booking/customer_router.py and
 * app/engines/final_records/customer_router.py — see
 * CUSTOMER-L5-11-contract-matrix.md.
 */
export const bookingConfirmationApi = {
  getReview: (draftId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/summary`, undefined, {
      signal: options.signal,
    }),

  /**
   * Sends the same stable idempotency key on both real headers this
   * backend recognizes: `Idempotency-Key` (read directly by this
   * endpoint, stored on the `CustomerBookingConfirmation` audit record —
   * though the actual functional dedup guard is a DB-unique constraint on
   * `(draft_type, draft_id)`, not this header value) and
   * `X-Idempotency-Key` (read by the separate, app-wide
   * `IdempotencyMiddleware`, which caches and replays the full HTTP
   * response for 24h). Sending both gets the benefit of both real, layered
   * mechanisms — see CUSTOMER-L5-11-idempotency-contract.md.
   */
  confirmBooking: (draftId: string, idempotencyKey: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(`/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/confirm`, undefined, {
      signal: options.signal,
      headers: { "Idempotency-Key": idempotencyKey, "X-Idempotency-Key": idempotencyKey },
    }),

  getBooking: (bookingId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/my-activity/bookings/${encodeURIComponent(bookingId)}`, { signal: options.signal }),
};
