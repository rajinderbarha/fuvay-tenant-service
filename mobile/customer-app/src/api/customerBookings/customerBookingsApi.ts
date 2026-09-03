import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { serviceBookingDtoSchema, bookingListResponseSchema } from "../contracts/customerBookings";
import { BookingListFilter } from "../../domain/bookingFilters";
import { z } from "zod";

const bookingActionEligibilitySchema = z.object({
  booking_id: z.string(),
  job_id: z.string(),
  status: z.string(),
  version: z.string(),
  can_cancel: z.boolean(),
  cancel_block_reason: z.string().nullable(),
  allowed_cancellation_reasons: z.array(z.string()),
  cancellation_reasons_requiring_detail: z.array(z.string()).default([]),
  can_reschedule: z.boolean(),
  reschedule_block_reason: z.string().nullable(),
  remaining_reschedule_allowance: z.number(),
}).passthrough();

const cancelledBookingSchema = z.object({
  booking_id: z.string(),
  job_id: z.string(),
  status: z.string(),
  reason: z.string(),
  version: z.string(),
}).passthrough();

const rescheduleAvailabilitySchema = z.object({
  booking_id: z.string(),
  job_id: z.string(),
  dates: z.array(z.object({ date: z.string(), available: z.boolean() })),
}).passthrough();

const rescheduledBookingSchema = z.object({
  booking_id: z.string(),
  job_id: z.string(),
  scheduled_date: z.string(),
  scheduled_time_window: z.string().nullable(),
  version: z.string(),
}).passthrough();

export type BookingActionEligibility = z.infer<typeof bookingActionEligibilitySchema>;

const maskedCallSchema = z.object({
  id: z.string(),
  booking_id: z.string().nullable(),
  direction: z.literal("customer_to_staff"),
  status: z.string(),
}).passthrough();

export async function listMyBookings(
  bucket: BookingListFilter,
  limit: number,
  offset: number,
  q?: string,
  status?: string | null,
) {
  // Both `q` and `status` are applied server-side
  // (final_records/customer_router.py) -- never filtered client-side,
  // which with pagination would only ever narrow the pages already
  // loaded. `status` narrows WITHIN the bucket rather than replacing it.
  const search = q && q.trim() ? `&q=${encodeURIComponent(q.trim())}` : "";
  const statusParam = status ? `&status=${encodeURIComponent(status)}` : "";
  const res = await authenticatedRequest({
    method: "GET",
    path: `/v1/customer/my-activity/bookings?bucket=${bucket}&limit=${limit}&offset=${offset}${search}${statusParam}`,
  });
  return parseApiSuccess(res.json, bookingListResponseSchema);
}

/** Throws a `DomainError` with `httpStatus: 404` for both a nonexistent
 * booking and one belonging to a different customer -- the backend
 * deliberately returns the identical response for both (see
 * contracts/customerBookings.ts). Callers must not attempt to
 * distinguish the two cases from this response. */
export async function getMyBooking(bookingId: string) {
  const res = await authenticatedRequest({
    method: "GET", path: `/v1/customer/my-activity/bookings/${bookingId}`,
  });
  return parseApiSuccess(res.json, serviceBookingDtoSchema);
}

export async function getBookingActionEligibility(bookingId: string) {
  const res = await authenticatedRequest({
    method: "GET",
    path: `/v1/customer/bookings/${encodeURIComponent(bookingId)}/cancel-reschedule-eligibility`,
  });
  return parseApiSuccess(res.json, bookingActionEligibilitySchema);
}

export async function cancelCustomerBooking(
  bookingId: string,
  input: { reason: string; detail?: string; expectedVersion: string },
) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/bookings/${encodeURIComponent(bookingId)}/cancel`,
    body: { reason: input.reason, detail: input.detail, expected_version: input.expectedVersion },
  });
  return parseApiSuccess(res.json, cancelledBookingSchema);
}

export async function getRescheduleAvailability(bookingId: string) {
  const res = await authenticatedRequest({
    method: "GET",
    path: `/v1/customer/bookings/${encodeURIComponent(bookingId)}/reschedule-availability`,
  });
  return parseApiSuccess(res.json, rescheduleAvailabilitySchema);
}

export async function rescheduleCustomerBooking(
  bookingId: string,
  input: { scheduledDate: string; scheduledTimeWindow?: string; reason: string; expectedVersion: string },
) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/bookings/${encodeURIComponent(bookingId)}/reschedule`,
    body: {
      scheduled_date: input.scheduledDate,
      scheduled_time_window: input.scheduledTimeWindow || null,
      reason: input.reason,
      expected_version: input.expectedVersion,
    },
  });
  return parseApiSuccess(res.json, rescheduledBookingSchema);
}

export async function callAssignedTechnician(bookingId: string) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/bookings/${encodeURIComponent(bookingId)}/call`,
  });
  return parseApiSuccess(res.json, maskedCallSchema);
}
