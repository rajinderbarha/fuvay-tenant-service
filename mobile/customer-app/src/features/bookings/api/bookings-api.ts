import { apiClient } from "../../../api/api-client";

/**
 * Real paths verified against
 * app/engines/home_service_assignment/customer_router.py — see
 * CUSTOMER-L5-12-contract-matrix.md. Deliberately distinct from
 * CUSTOMER-L5-11's `features/booking-confirmation/api/booking-confirmation-api.ts`,
 * which calls the separate, less complete `final_records` router — this
 * feature uses the richer, already-customer-safe assignment-aware
 * router instead (see baseline-verification.md's Central Findings).
 */
export const bookingsApi = {
  listBookings: (page: number, pageSize: number, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/bookings?page=${page}&page_size=${pageSize}`, { signal: options.signal }),

  getBooking: (bookingId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/bookings/${encodeURIComponent(bookingId)}`, { signal: options.signal }),

  getBookingTracking: (bookingId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/bookings/${encodeURIComponent(bookingId)}/tracking`, { signal: options.signal }),

  getBookingReviewStatus: (bookingId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/bookings/${encodeURIComponent(bookingId)}/rating`, { signal: options.signal }),
};
