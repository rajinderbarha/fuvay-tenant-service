import { useBookingDetail } from "../../booking-confirmation/queries/booking-confirmation-queries";
import { useJobQuotes, useQuoteDetail } from "../queries/quote-queries";
import { selectPrimaryQuote } from "../domain/quote-state";

/**
 * Resolves the real `job.id` via the reused CUSTOMER-L5-11/13
 * booking-detail query, lists this customer's quotes for that job, then
 * fetches the full detail (line items) of the one quote this screen
 * shows — the most recent `sent_to_customer` quote if one exists, else
 * the most recent quote overall (`selectPrimaryQuote`). Three real,
 * sequential fetches — no fabricated combined endpoint.
 */
export function useQuoteDecision(bookingId: string) {
  const bookingQuery = useBookingDetail(bookingId);
  const jobId = bookingQuery.data?.job?.id ?? null;
  const listQuery = useJobQuotes(jobId);
  const primaryQuote = listQuery.data ? selectPrimaryQuote(listQuery.data) : null;
  const detailQuery = useQuoteDetail(primaryQuote?.id ?? null);

  return { bookingQuery, jobId, listQuery, detailQuery };
}
