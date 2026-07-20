# CUSTOMER-L5-14 — Failure Matrix

| Scenario | Real server behavior | This client's handling |
|---|---|---|
| No job exists yet for this booking | `job` field absent/null on booking detail | `useQuoteDecision`'s `jobId` stays `null`; `useJobQuotes` never fires (`enabled: Boolean(jobId)`) |
| Job exists, no quote ever created | `GET /customer/quotes/jobs/{job_id}` returns `[]` | `quoteDecision.noneYet` message, no error state |
| Quote list loads, detail fetch fails | transient network/5xx on `GET /customer/quotes/{quote_id}` | `ErrorState` with retry, scoped to the detail fetch only (list still shown to have succeeded) |
| Quote in `draft`/`submitted_to_provider`/`provider_approved` | real, valid states — customer not yet asked | Read-only status label (`quoteDecision.status.preparing`), no action buttons |
| Quote is `sent_to_customer` | actionable | Approve/Reject/Request-revision all enabled |
| Approve tapped, request succeeds | `customer_approved`, job status synced | Buttons hidden after refetch (no longer actionable); status label updates |
| Approve tapped, network drops mid-request | uncertain outcome | Retried once automatically (idempotency key + `apiClient`'s built-in retry for idempotent POSTs) — if the first attempt actually landed, the retry hits the idempotency short-circuit and returns success; if it didn't land, the retry performs the real approval |
| Reject/revision tapped, network drops mid-request | uncertain outcome, no retry (no idempotency support server-side) | `quoteDecision.actionFailed` shown; re-opening the screen shows the true current status either way — no duplicate/conflicting reason submitted automatically |
| Reason field submitted empty | would raise `ERR_QUOTE_REJECTION_REASON_REQUIRED`/`ERR_QUOTE_REVISION_REASON_REQUIRED` (opaque 500) | Never reaches the server — "Submit" stays disabled until non-empty |
| Race: staff cancels/re-sends the quote between load and tap | `ERR_QUOTE_INVALID_TRANSITION` (opaque 500, see financial-security-review.md) | `quoteDecision.actionFailed` generic message; refetch on next screen visit shows the true state |
| Quote has non-customer-visible items | server returns them anyway (real gap) | Filtered out before render (`parseQuoteDetail`) |
| Quote has `provider_internal_notes` | server returns it anyway (real gap) | Never parsed, never rendered (structural exclusion) |
| Booking doesn't belong to this customer | `403`/`ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED` on quote endpoints; `useBookingDetail`'s own ownership check already blocks earlier | Screen never reaches a state where this is reachable through normal navigation (booking detail's own access guard gates entry) |
