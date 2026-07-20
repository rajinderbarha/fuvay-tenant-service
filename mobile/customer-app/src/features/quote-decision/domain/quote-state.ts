import type { ValidatedQuote } from "./quote-schema";

/**
 * `QUOTE_TRANSITIONS` from `app/engines/quote_checklist/constants.py`
 * (lines 19–32) allows customer-initiated transitions (approve/reject/
 * request-revision) only from `sent_to_customer`. Every other status is
 * read-only in this client — see CUSTOMER-L5-14-contract-matrix.md.
 */
export const QUOTE_STATUS_ACTIONABLE = "sent_to_customer";

export function isQuoteActionable(quote: ValidatedQuote): boolean {
  return quote.status === QUOTE_STATUS_ACTIONABLE;
}

export function quoteStatusTitleKey(status: string): string {
  switch (status) {
    case "draft":
    case "submitted_to_provider":
    case "provider_approved":
      return "quoteDecision.status.preparing";
    case "sent_to_customer":
      return "quoteDecision.status.awaitingYourDecision";
    case "customer_approved":
      return "quoteDecision.status.approved";
    case "customer_rejected":
      return "quoteDecision.status.rejected";
    case "revision_requested":
      return "quoteDecision.status.revisionRequested";
    case "revised":
      return "quoteDecision.status.revised";
    case "provider_rejected":
      return "quoteDecision.status.providerRejected";
    case "expired":
      return "quoteDecision.status.expired";
    case "cancelled":
      return "quoteDecision.status.cancelled";
    default:
      return "quoteDecision.status.unknown";
  }
}

/** Picks the quote this screen should show: the most recently created quote for the job, so a superseded/revised quote never shadows the current one. Reused across the list-selection hook and its tests. */
export function selectPrimaryQuote(quotes: ValidatedQuote[]): ValidatedQuote | null {
  if (quotes.length === 0) return null;
  const actionable = quotes.find(isQuoteActionable);
  return actionable ?? quotes[0];
}
