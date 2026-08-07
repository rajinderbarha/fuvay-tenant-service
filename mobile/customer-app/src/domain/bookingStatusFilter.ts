/**
 * Options for the My Bookings filter sheet.
 *
 * Every entry maps to a REAL `ServiceBooking.status` value that the
 * backend writes and that GET /v1/customer/my-activity/bookings already
 * accepts through its `status` query parameter -- see
 * final_records/customer_router.py, which narrows on exact status
 * alongside the bucket. Nothing here is a client-side invention, and no
 * option is offered that the endpoint cannot actually filter on.
 *
 * The customer-facing wording is deliberately gentler than the raw enum
 * (`pending_assignment` -> "Finding a professional"), but the mapping is
 * one-to-one so a chosen filter always means exactly one backend state.
 */
export interface BookingStatusFilterOption {
  /** Raw ServiceBooking.status, or null for "no status narrowing". */
  value: string | null;
  label: string;
}

/** Ordered as a booking actually progresses, so the sheet reads as a
 * timeline. Every value was confirmed present in `service_bookings.status`
 * and/or written by engine code -- `on_the_way` in particular is a real
 * status the execution engine writes (workflow step "On The Way") that
 * the older `final_records/constants.py` list never named. */
export const BOOKING_STATUS_FILTERS: readonly BookingStatusFilterOption[] = [
  { value: null, label: "Any status" },
  { value: "pending_assignment", label: "Finding a professional" },
  { value: "assigned", label: "Professional assigned" },
  { value: "accepted", label: "Accepted by professional" },
  { value: "scheduled", label: "Visit scheduled" },
  { value: "on_the_way", label: "On the way" },
  { value: "in_progress", label: "Work in progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export function bookingStatusFilterLabel(value: string | null): string {
  return BOOKING_STATUS_FILTERS.find(o => o.value === value)?.label
    ?? BOOKING_STATUS_FILTERS[0].label;
}
