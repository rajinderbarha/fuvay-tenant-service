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
 * PREFIX FIX (2026-08-05): these paths previously omitted the /v1 prefix, on
 * the assumption that field_ops permanently occupied /v1/customer/quotes --
 * so every call here 404'd and quote approval never worked from the web app.
 * The real router IS at /v1/customer/quotes; the field_ops router that
 * collided with it was backed by a dead, empty table and is no longer
 * mounted (see app/main.py). The mobile customer app already used the
 * correct /v1 paths and was being silently swallowed by that collision.
 *
 * Real router: app/engines/quote_checklist/customer_router.py
 *   GET  /v1/customer/quotes/jobs/{job_id}
 *   GET  /v1/customer/quotes/{quote_id}
 *   POST /v1/customer/quotes/{quote_id}/approve           (Idempotency-Key header)
 *   POST /v1/customer/quotes/{quote_id}/reject            { reason }
 *   POST /v1/customer/quotes/{quote_id}/request-revision  { reason }
 *   GET  /v1/customer/quotes/{quote_id}/events
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
  const d = await apiFetch<Quote[]>(`/v1/customer/quotes/jobs/${jobId}`);
  return Array.isArray(d) ? d : [];
}

export async function getQuote(quoteId: string): Promise<Quote> {
  return apiFetch<Quote>(`/v1/customer/quotes/${quoteId}`);
}

export async function approveQuote(quoteId: string): Promise<Quote> {
  // Approval is money-moving, so the backend requires an idempotency key.
  const key = `approve-${quoteId}-${Date.now()}`;
  return apiFetch<Quote>(`/v1/customer/quotes/${quoteId}/approve`, {
    method: "POST", headers: { "Idempotency-Key": key }, body: "{}",
  });
}

export async function rejectQuote(quoteId: string, reason: string): Promise<Quote> {
  return apiFetch<Quote>(`/v1/customer/quotes/${quoteId}/reject`, {
    method: "POST", body: JSON.stringify({ reason }),
  });
}

export async function requestQuoteRevision(quoteId: string, reason: string): Promise<Quote> {
  return apiFetch<Quote>(`/v1/customer/quotes/${quoteId}/request-revision`, {
    method: "POST", body: JSON.stringify({ reason }),
  });
}
