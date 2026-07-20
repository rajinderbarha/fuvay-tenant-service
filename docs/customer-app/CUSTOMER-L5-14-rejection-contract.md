# CUSTOMER-L5-14 — Rejection Contract

## Endpoint

`POST /customer/quotes/{quote_id}/reject`, body `{ "reason": string }`
(`customer_router.py` lines 52–62). No `Idempotency-Key` support — the
router reads `body.get("reason", "")` directly with no header
requirement.

## Service logic (`quote_service.py` `customer_reject`, lines 363–394)

1. `reason` must be non-empty after `.strip()` →
   `ERR_QUOTE_REJECTION_REASON_REQUIRED` otherwise.
2. Ownership check (`ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED` on
   mismatch).
3. `_assert_transition(q, customer_rejected)` — only valid from
   `sent_to_customer`.
4. Sets `status=customer_rejected`, `rejection_reason=reason`,
   `rejected_at=now`. **No `locked_at`** is set on rejection (unlike
   approval) — not exploitable by this client (there is no item-edit UI
   here regardless), but noted as a real asymmetry in the backend.
5. `_sync_job_status(job_id, "quote_rejected")`.
6. Logs `quote_customer_rejected` with the reason.

## This client's enforcement

- The reason field (`AppTextArea` inside the reject modal,
  `QuoteDecisionScreen.tsx`) requires non-empty text before the "Submit"
  button enables (`disabled={reasonText.trim().length === 0}`) —
  proactively avoiding `ERR_QUOTE_REJECTION_REASON_REQUIRED`'s opaque-500
  surface (baseline-verification.md #5.2).
- No idempotency key is passed (matches the real endpoint's lack of
  support) — this mutation is **not** auto-retried by `apiClient` on a
  transient 5xx. A genuine network failure mid-submission surfaces as
  `quoteDecision.actionFailed` and the user must explicitly retry, at
  which point the quote is either still `sent_to_customer` (retry
  succeeds cleanly) or already `customer_rejected` from the first attempt
  having actually landed (retry fails with the same opaque 500, but the
  real state is correct either way — a fresh screen load after
  dismissing the error will show `customer_rejected`, not a duplicate
  rejection, since the mutation is not called again automatically).

## What rejection does NOT do

Does not cancel the booking/job, does not require staff/provider
acknowledgement to take effect, and has no path back to
`sent_to_customer` (transitions table: `customer_rejected` is final —
only a brand-new quote, not a status change on this one, could offer the
customer another decision).
