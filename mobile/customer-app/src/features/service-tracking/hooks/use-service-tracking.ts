import { useBookingDetail } from "../../booking-confirmation/queries/booking-confirmation-queries";
import { useJobExecutionTracking } from "../queries/service-tracking-queries";

/**
 * Resolves the real `job.id` via the reused CUSTOMER-L5-11 booking-detail
 * query (`/v1/customer/my-activity/bookings/{bookingId}`, the only real
 * endpoint that returns a raw job ID — see
 * CUSTOMER-L5-13-contract-matrix.md), then fetches the real execution
 * timeline for that job. Two real, sequential fetches — not a fabricated
 * combined endpoint.
 */
export function useServiceTracking(bookingId: string) {
  const bookingQuery = useBookingDetail(bookingId);
  const jobId = bookingQuery.data?.job?.id ?? null;
  const trackingQuery = useJobExecutionTracking(jobId);

  return { bookingQuery, jobId, trackingQuery };
}
