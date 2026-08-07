import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { serviceBookingDtoSchema, bookingListResponseSchema } from "../contracts/customerBookings";
import { BookingListFilter } from "../../domain/bookingFilters";

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
