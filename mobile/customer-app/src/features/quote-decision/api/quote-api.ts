import { apiClient } from "../../../api/api-client";

/**
 * Real paths verified against `app/engines/quote_checklist/customer_router.py`
 * — see CUSTOMER-L5-14-contract-matrix.md. Deliberately has NO `/v1`
 * prefix: this engine's own `APIRouter(prefix="/customer/quotes")` never
 * declares one, unlike every other engine's customer router in this
 * codebase (baseline-verification.md #5.1) — this is the real, disclosed,
 * mounted path, not an oversight in this client.
 */
export const quoteApi = {
  getJobQuotes: (jobId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/customer/quotes/jobs/${encodeURIComponent(jobId)}`, { signal: options.signal }),

  getQuote: (quoteId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/customer/quotes/${encodeURIComponent(quoteId)}`, { signal: options.signal }),

  /** Requires `Idempotency-Key` — the real backend endpoint rejects the request without it (`customer_router.py` line 41: `Header(..., alias="Idempotency-Key")`). */
  approveQuote: (quoteId: string, idempotencyKey: string) =>
    apiClient.post<unknown>(`/customer/quotes/${encodeURIComponent(quoteId)}/approve`, undefined, { idempotencyKey }),

  /** No idempotency support on this real endpoint (contract-matrix.md) — never pass `idempotencyKey`, so the client's own auto-retry never fires for a non-idempotent business action. */
  rejectQuote: (quoteId: string, reason: string) => apiClient.post<unknown>(`/customer/quotes/${encodeURIComponent(quoteId)}/reject`, { reason }),

  requestRevision: (quoteId: string, reason: string) => apiClient.post<unknown>(`/customer/quotes/${encodeURIComponent(quoteId)}/request-revision`, { reason }),
};
