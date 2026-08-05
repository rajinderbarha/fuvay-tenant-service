import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { serviceBookingDtoSchema, bookingListResponseSchema } from "../contracts/customerBookings";
import { BookingListFilter } from "../../domain/bookingFilters";

export async function listMyBookings(bucket: BookingListFilter, limit: number, offset: number) {
  const res = await authenticatedRequest({
    method: "GET", path: `/v1/customer/my-activity/bookings?bucket=${bucket}&limit=${limit}&offset=${offset}`,
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
