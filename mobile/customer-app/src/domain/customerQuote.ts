export interface CustomerQuoteLineItem {
  id: string;
  label: string;
  description: string | null;
  quantity: string;
  unitAmount: string;
  lineTotal: string;
}

/** No canonical "visit fee"/"fee adjustment" quote-level field exists on
 * the real backend model (confirmed via source read of
 * `quote_checklist/models.py` and `constants.py`'s `VALID_ITEM_TYPES`) --
 * those concepts, when present, are ordinary line items (`item_type`
 * "visit_charge"/"discount") named by whatever the provider actually
 * entered. This type renders exactly the items and totals the backend
 * sends, never a synthesized visit-fee/adjustment breakdown. */
export interface CustomerQuote {
  id: string;
  quoteNumber: string;
  jobId: string;
  rawStatus: string;
  currency: string;
  totalAmount: string;
  customerPayableAmount: string;
  findingSummary: string | null;
  rejectionReason: string | null;
  isCurrent: boolean;
  items: CustomerQuoteLineItem[];
}
