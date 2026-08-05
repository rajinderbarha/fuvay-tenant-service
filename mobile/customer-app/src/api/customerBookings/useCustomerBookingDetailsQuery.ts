import { useCallback } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useQuery } from "@tanstack/react-query";
import { getMyBooking } from "./customerBookingsApi";
import { adaptCustomerBookingDetails } from "../adapters/customerBookingDetails";
import { CustomerBookingDetails } from "../../domain/customerBookingDetails";
import { bookingQueryKeys } from "./bookingQueryKeys";
import { DomainError } from "../../domain/errors";

export type BookingDetailsResult =
  | { kind: "found"; details: CustomerBookingDetails }
  | { kind: "not_found" };

/**
 * Shares `bookingQueryKeys` with `useCustomerBookingQuery` (Confirmation
 * Receipt) and the future My Bookings list hook -- no ad hoc key guessing.
 * Same real-404 handling as the receipt hook: a nonexistent booking and a
 * cross-customer one are indistinguishable here by backend design.
 */
export function useCustomerBookingDetailsQuery(bookingId: string) {
  const query = useQuery({
    queryKey: bookingQueryKeys.detail(bookingId),
    queryFn: async (): Promise<BookingDetailsResult> => {
      try {
        const res = await getMyBooking(bookingId);
        return { kind: "found", details: adaptCustomerBookingDetails(res.data) };
      } catch (err) {
        if (err instanceof DomainError && err.httpStatus === 404) {
          return { kind: "not_found" };
        }
        throw err;
      }
    },
  });

  // Spec section 4: "Refetch on screen focus" -- re-runs the same query,
  // never a separate polling loop; react-query dedupes if a fetch is
  // already in flight, so rapid focus/blur cannot pile up requests.
  useFocusEffect(
    useCallback(() => {
      query.refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [bookingId]),
  );

  return query;
}
