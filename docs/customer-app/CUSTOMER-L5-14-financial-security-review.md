# CUSTOMER-L5-14 — Financial & Security Review

## Money handling

- `currency` is always `"INR"` — hardcoded server-side
  (`models.py` line 30), never customer- or provider-selectable.
  `formatCurrency(amount, locale, quote.currency)` is used everywhere
  (not a hardcoded `"INR"` literal in the client), so if the backend ever
  changes this, the client adapts without a code change — but no other
  currency has ever been observed.
- Every amount rendered (`line_total`, `customer_payable_amount`) is
  taken exactly as returned by the server — `_recalculate`
  (`quote_service.py` lines 104–122) is the sole place any arithmetic
  happens, and it runs server-side only. This client never adds,
  multiplies, or re-derives a total.
- No payment is collected by this screen. Approving a quote changes
  `ServiceJob.status` to `quote_approved` — the actual payment mechanism
  remains whatever the job's normal completion/invoice flow already is
  (Sprint 23 / CUSTOMER-L5-09's payment-mode rules), unmodified by this
  sprint.

## Ownership / access control

Every customer-facing endpoint checks `str(quote.customer_id) ==
str(user.user_id)` server-side (`quote_service.py`'s three customer
methods) — this client adds no additional client-side ownership check
beyond routing through the already-ownership-checked `useBookingDetail`
to resolve `job.id` in the first place (same posture as CUSTOMER-L5-11
through 13).

## The opaque-500 gap and how this client is designed around it

**This is the sprint's central security/reliability finding** (also in
baseline-verification.md #5.2): every one of `quote_service.py`'s
business-rule guards (`ERR_QUOTE_ACCESS_DENIED`,
`ERR_QUOTE_INVALID_TRANSITION`, `ERR_QUOTE_REJECTION_REASON_REQUIRED`,
`ERR_QUOTE_REVISION_REASON_REQUIRED`, `ERR_QUOTE_IDEMPOTENCY_CONFLICT`,
`ERR_QUOTE_NOT_FOUND`, `ERR_QUOTE_JOB_NOT_FOUND`) is raised as a plain
Python `ValueError`, which `app/exceptions.py` has no dedicated handler
for — it falls through to the generic `Exception` handler and returns a
500 `INTERNAL_ERROR`, with the real reason only in the server log. This
client's `normalizeApiError` (pre-existing, cross-cutting limitation
already documented since earlier sprints) additionally never reads a
response body at all — so even if the server did return the specific
code, this client could not distinguish it from any other 500 without a
change to `api-errors.ts` itself (out of scope for a single feature
sprint).

**Consequence**: a customer who, say, taps "Approve" on a quote that a
staff member simultaneously cancelled sees the exact same generic
"Something went wrong. Please try again." as a customer who hits a real
server outage. This is an honest, disclosed UX degradation, not a
security hole — no wrong action is silently taken; the request either
succeeds (and the invalidated refetch shows the true resulting state) or
it visibly fails with a safe, generic message.

**Mitigation strategy (proactive, not reactive)**: this client enforces
every one of the server's own guards *before* ever calling the endpoint,
so the opaque-500 path is reached only on a genuine race condition, never
in routine use:
- Approve/reject/revision buttons only render when
  `isQuoteActionable(quote)` (`status === "sent_to_customer"`).
- Reject/revision "Submit" is disabled until the reason field is
  non-empty.
- Approve's idempotency key is generated once and held for the
  component's lifetime, so a retry after an uncertain outcome cannot
  itself trigger `ERR_QUOTE_IDEMPOTENCY_CONFLICT` (mismatched key).

## Data exposure

`provider_internal_notes`, `created_by_user_id`,
`created_by_staff_member_id`, `idempotency_key`, `locked_at` are excluded
structurally from this client's parse schema (never listed in
`quoteSchema`) even though the real `GET /customer/quotes/{quote_id}`
response includes them unfiltered — the same `z.object()` key-stripping
technique used since CUSTOMER-L5-08, applied here to a newly-confirmed
real leak. Non-customer-visible items (`is_customer_visible: false`) are
likewise dropped post-validation, since the server does not filter them
either. See `line-item-contract.md`.

## What this client never logs

The idempotency key, the full quote payload, and the reject/revision
reason text are never passed to `logger.*` — only lifecycle markers
(`quote_approve_started`/`_succeeded`/`_failed`, etc. — no PII, no
amounts, no free-text reason), matching the redaction posture of every
previous sprint.
