/**
 * Customer Quotes API module — approve/reject provider work quotes.
 *
 * MODULE-L5-16: when a job needs extra work/parts the provider sends the customer
 * a quote (quote_checklist engine, the same one the provider uses via
 * /staff/quotes and the tenant-portal /service-jobs/[id]/quotes screen). The
 * customer_router (/customer/quotes/*) lets the customer approve, reject, or ask
 * for a revision — but the customer app had NO surface for it, so any job that
 * needed a quote simply stalled. This wires it.
 *
 * NOTE: this router is mounted at /customer/quotes (no /v1 prefix) because the
 * field_ops job-tracking engine occupies /v1/customer/quotes; the provider's real
 * quote engine is quote_checklist, which is what the tenant-portal uses.
 *
 * Real router: app/engines/quote_checklist/customer_router.py
 *   GET  /customer/quotes/jobs/{job_id}
 *   GET  /customer/quotes/{quote_id}
 *   POST /customer/quotes/{quote_id}/approve           (Idempotency-Key header)
 *   POST /customer/quotes/{quote_id}/reject            { reason }
 *   POST /customer/quotes/{quote_id}/request-revision  { reason }
 *   GET  /customer/quotes/{quote_id}/events
 */
import { apiFetch } from "./client";

export interface QuoteItem {
  id: string;
  description?: string | null;
  item_type?: string | null;
  quantity?: number | string | null;
  unit_price?: number | string | null;
  amount?: number | string | null;
}

export interface Quote {
  id: string;
  quote_number: string;
  job_id: string;
  status: string;
  quote_type?: string | null;
  currency?: string | null;
  labour_amount?: string | null;
  parts_amount?: string | null;
  service_amount?: string | null;
  total_amount?: string | null;
  notes?: string | null;
  items?: QuoteItem[];
  version_number?: number;
  is_current?: boolean;
}

export async function listJobQuotes(jobId: string): Promise<Quote[]> {
  const d = await apiFetch<Quote[]>(`/customer/quotes/jobs/${jobId}`);
  return Array.isArray(d) ? d : [];
}

export async function getQuote(quoteId: string): Promise<Quote> {
  return apiFetch<Quote>(`/customer/quotes/${quoteId}`);
}

export async function approveQuote(quoteId: string): Promise<Quote> {
  // Approval is money-moving, so the backend requires an idempotency key.
  const key = `approve-${quoteId}-${Date.now()}`;
  return apiFetch<Quote>(`/customer/quotes/${quoteId}/approve`, {
    method: "POST", headers: { "Idempotency-Key": key }, body: "{}",
  });
}

export async function rejectQuote(quoteId: string, reason: string): Promise<Quote> {
  return apiFetch<Quote>(`/customer/quotes/${quoteId}/reject`, {
    method: "POST", body: JSON.stringify({ reason }),
  });
}

export async function requestQuoteRevision(quoteId: string, reason: string): Promise<Quote> {
  return apiFetch<Quote>(`/customer/quotes/${quoteId}/request-revision`, {
    method: "POST", body: JSON.stringify({ reason }),
  });
}
