import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { getMyBooking } from "./customerBookingsApi";
import { adaptBookingReceipt } from "../adapters/bookingReceipt";
import { BookingReceipt } from "../../domain/bookingReceipt";
import { bookingQueryKeys } from "./bookingQueryKeys";
import { DomainError } from "../../domain/errors";

export type BookingReceiptResult =
  | { kind: "found"; receipt: BookingReceipt }
  | { kind: "not_found" };

/**
 * `GET .../my-activity/bookings/{id}` now returns a real, identical HTTP
 * 404 for both a nonexistent booking and one belonging to a different
 * customer (SECURITY fix, 2026-08-01) -- this hook must not (and no
 * longer can) distinguish the two; both collapse to `kind: "not_found"`.
 */
export function useCustomerBookingQuery(bookingId: string) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: bookingQueryKeys.detail(bookingId),
    queryFn: async (): Promise<BookingReceiptResult> => {
      try {
        const res = await getMyBooking(bookingId);
        return { kind: "found", receipt: adaptBookingReceipt(res.data) };
      } catch (err) {
        if (err instanceof DomainError && err.httpStatus === 404) {
          return { kind: "not_found" };
        }
        throw err;
      }
    },
  });

  // Spec section 3: invalidate/refetch Home active-booking and My Bookings
  // caches once a real receipt has loaded -- runs once per successful
  // fetch (react-query dedupes identical invalidations), never on a
  // failed/pending read.
  useEffect(() => {
    if (query.data?.kind === "found") {
      // Partial key match (no zipcode) so every zipcode variant of the
      // Home aggregation cache is invalidated, not just the null-zipcode one.
      queryClient.invalidateQueries({ queryKey: ["home", "aggregate"] });
      queryClient.invalidateQueries({ queryKey: bookingQueryKeys.lists() });
    }
  }, [query.data, queryClient]);

  return query;
}
