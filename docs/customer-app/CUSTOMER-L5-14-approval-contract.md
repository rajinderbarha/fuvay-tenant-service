# CUSTOMER-L5-14 — Approval Contract

## Endpoint

`POST /customer/quotes/{quote_id}/approve` — `customer_router.py` lines
38–49. **Requires** an `Idempotency-Key` header (`Header(..., alias=
"Idempotency-Key")`, line 41) — the request is rejected by FastAPI's own
validation if the header is missing, before the service layer even runs.

## Service logic (`quote_service.py` `customer_approve`, lines 323–359)

1. `str(q.customer_id) != customer_id` → `ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED`
   (ownership check).
2. **Idempotency short-circuit**: if `status == customer_approved` and the
   stored `idempotency_key` matches the one just sent, returns the quote
   as-is (safe replay of an already-successful approval).
3. If already `customer_approved` with a **different** key →
   `ERR_QUOTE_IDEMPOTENCY_CONFLICT`.
4. Otherwise `_assert_transition(q, customer_approved)` — only valid from
   `sent_to_customer`.
5. Sets `status=customer_approved`, `approved_at=now`, `locked_at=now`
   (locking blocks any further item edits — moot for a customer, who
   never edits items, but documented for completeness),
   `idempotency_key=<the one just sent>`.
6. `_sync_job_status(job_id, "quote_approved")`.
7. Logs a `quote_customer_approved` event.

## This client's idempotency key handling

Generated once per screen-instance via `newIdempotencyKey()`
(`QuoteDecisionScreen.tsx`, same `useRef`-held-for-lifetime pattern as
CUSTOMER-L5-11's `useConfirmBookingFlow`) — a retry after an uncertain
outcome (e.g. a timeout) reuses the exact same key, never mints a fresh
one, so the real backend's idempotency short-circuit (step 2 above) is
actually exercised rather than risking a spurious
`ERR_QUOTE_IDEMPOTENCY_CONFLICT`. The key is never logged (matches the
security posture of every previous sprint's idempotency keys).

## Why approval is safe to auto-retry, unlike reject/revision

`apiClient`'s retry policy only retries a non-GET request when an
`idempotencyKey` is supplied (`api-types.ts`). Approval is the only one
of the three decision actions that supports and uses this — so it is the
only one eligible for the client's built-in one-retry-on-5xx behavior.
Reject and request-revision deliberately never pass an `idempotencyKey`
(no server-side dedup logic exists for them — see `rejection-contract.md`/
`revision-contract.md`), so they are never auto-retried, avoiding a
double-submission of a `reason` string that the server would otherwise
reject with a second, indistinguishable opaque 500
(`ERR_QUOTE_ALREADY_DECIDED`-equivalent: `ERR_QUOTE_INVALID_TRANSITION`,
since the quote is no longer `sent_to_customer` after the first
successful call).
