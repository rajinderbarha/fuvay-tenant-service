/**
 * Canonical query-key factory for customer bookings -- shared by the
 * Confirmation Receipt, Booking Details, and the future My Bookings list
 * hook, replacing the earlier ad hoc `["bookings", "list"]` guess (which
 * had no producer to actually verify it matched). Every booking-scoped
 * query in this app must derive its key from here so a future list hook
 * and this phase's detail/receipt hooks can invalidate each other
 * correctly without agreeing on a raw array by convention alone.
 */
export interface BookingFilters {
  /** active | completed | all -- which tab is selected. */
  bucket?: string;
  /** An exact `ServiceBooking.status` narrowing WITHIN the bucket, set by
   * the filter sheet. Distinct from `bucket`: the two combine. */
  status?: string;
  page?: number;
  /** Free-text search term. Part of the key so each distinct search is
   * cached separately and a stale result can never render under a newer
   * term. */
  q?: string;
}

export const bookingQueryKeys = {
  all: ["customer", "bookings"] as const,
  lists: () => [...bookingQueryKeys.all, "list"] as const,
  list: (filters: BookingFilters = {}) => [...bookingQueryKeys.lists(), filters] as const,
  details: () => [...bookingQueryKeys.all, "detail"] as const,
  detail: (bookingId: string) => [...bookingQueryKeys.details(), bookingId] as const,
} as const;
