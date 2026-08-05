import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerQuoteDtoSchema, customerQuoteListDtoSchema } from "../contracts/customerQuote";
import { IdempotencyKey } from "../../domain/ids";

/** `GET /v1/customer/quotes/jobs/{jobId}` -- returns only the job's
 * current quote (this phase's own backend fix; see
 * `quote_service.list_customer_quotes`), never superseded history. */
export async function listJobQuotes(jobId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/quotes/jobs/${jobId}` });
  return parseApiSuccess(res.json, customerQuoteListDtoSchema);
}

/** `GET /v1/customer/quotes/{quoteId}` -- full customer-safe detail
 * including allow-listed line items and customer-reconciled totals. */
export async function getQuote(quoteId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/quotes/${quoteId}` });
  return parseApiSuccess(res.json, customerQuoteDtoSchema);
}

/** `POST /v1/customer/quotes/{quoteId}/approve` -- requires the
 * `Idempotency-Key` header (confirmed via source read of
 * `quote_checklist/customer_router.py`); a retried request with the same
 * key returns the same result rather than double-approving. */
export async function approveQuote(quoteId: string, idempotencyKey: IdempotencyKey) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/quotes/${quoteId}/approve`, idempotencyKey,
  });
  return parseApiSuccess(res.json, customerQuoteDtoSchema);
}

/** `POST /v1/customer/quotes/{quoteId}/reject` -- `reason` is required by
 * the real backend (`ERR_QUOTE_REJECTION_REASON_REQUIRED`). */
export async function declineQuote(quoteId: string, reason: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/quotes/${quoteId}/reject`, body: { reason },
  });
  return parseApiSuccess(res.json, customerQuoteDtoSchema);
}
