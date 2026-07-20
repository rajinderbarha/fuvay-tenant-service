# CUSTOMER-L5-14 — Known Gaps

## P0

1. **No live runtime certification** — see `runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **The spec's literal "parts approval" target is orphaned, unreachable
   backend state.** `execution` engine's `PartsRequest` model,
   `customer_approval_required` flag, and `PARTS_STATUS_CUSTOMER_*`
   statuses are real, but no code path anywhere sets
   `PARTS_STATUS_CUSTOMER_APPROVED`/`_CUSTOMER_REJECTED`, and there is no
   customer-facing endpoint of any kind for parts requests. This sprint
   pivoted to building against the separate, fully-functional
   `quote_checklist` engine instead — see
   `baseline-verification.md`'s Central Finding and
   `parts-request-contract.md`. A future sprint could still add the
   missing `PARTS_STATUS_CUSTOMER_APPROVED`/`_REJECTED`-setting service
   methods and customer endpoints to the `execution` engine if product
   wants parts specifically (as opposed to general additional-cost line
   items) tracked as their own decision flow.
3. **Every quote-service business-rule rejection is an opaque 500, not a
   4xx** — `ValueError` has no dedicated exception handler in
   `app/exceptions.py`; falls through to the generic 500 handler with the
   real reason only in the server log. Mitigated client-side by
   proactively enforcing every guard before calling the endpoint (see
   `financial-security-review.md`), but a genuine race condition still
   produces an indistinguishable-from-outage generic error message.
4. **`GET /customer/quotes/{quote_id}` does not filter by
   `is_customer_visible`**, and also returns `provider_internal_notes` —
   both real, disclosed backend gaps mitigated entirely client-side (see
   `line-item-contract.md`/`financial-security-review.md`). A backend fix
   would be to filter both in `get_quote` itself.
5. **No `/v1` prefix on `quote_checklist`'s customer router** — a real,
   confirmed inconsistency versus every other engine's customer router in
   this codebase (baseline-verification.md #5.1). This client hits the
   real path as mounted; a future backend cleanup adding the missing
   prefix would require a corresponding one-line client change to
   `quote-api.ts`.
6. **No expiry enforcement despite a real `expires_at` column and
   `QS_EXPIRED` status** — a quote can sit `sent_to_customer` forever with
   no deadline. This client does not fabricate one; if product wants a
   customer-facing countdown, the backend would need to actually set
   `expires_at` and enforce it (no scheduler currently exists for this).
7. **No component/render tests** for `QuoteDecisionScreen` — same,
   now-consistent-across-fourteen-sprints deprioritization pattern.
8. **Whether `EVT_QUOTE_SENT`/`_APPROVED`/`_REJECTED`/`_REVISION` are
   actually emitted (vs. only registered) was not re-traced to their
   emission call sites this sprint** — see `notification-deep-links.md`.
   If not emitted, a customer currently has no push-notification signal
   that a decision is needed; they must open the app and navigate to
   Booking Detail themselves.

## P2

9. **`GET /customer/quotes/{quote_id}/events` (the audit trail) is not
   queried or rendered by this client at all** — a real endpoint with no
   UI built against it this sprint (out of scope: the spec's core ask is
   the decision itself, not a full audit-log viewer). A future sprint
   could add a simple history list using the exact same resilient-parsing
   pattern established here.
10. **No analytics events actually wired to a vendor** — same
    now-fourteen-sprints-running gap: no analytics SDK is integrated in
    this app at all; `logger.*` calls are structured logs only.
11. **`quote-api.ts`/hook composition files have no dedicated unit
    tests** — consistent with the established, repo-wide pattern for thin
    API wrappers and hook-composition layers.
12. **This sprint's own client-authored quote-status labels
    (`quote-state.ts`'s `quoteStatusTitleKey`) have not been reviewed
    against any existing product-copy style guide** — none was found in
    the repo for this specific screen, same disclosed caveat as every
    previous sprint's original copy.
13. **`revision_reason` is a single, overwritable column** — a second
    revision request later in the same quote's lifecycle erases the
    first reason server-side (see `revision-contract.md`). Not a client
    bug, but worth flagging if product ever wants a full revision history
    surfaced to the customer.

## P3

14. **Punjabi/Hindi translations of the new `quoteDecision.*`/
    `bookings.status.*` keys were written by this sprint and have not
    been reviewed by a native-speaking product reviewer** — same
    disclosed caveat pattern as every previous sprint's localization
    additions.
15. **No genuine multi-quote-per-job scenario was exercised against a
    live backend** — `selectPrimaryQuote`'s "prefer actionable, else most
    recent" logic is covered by unit tests using synthetic fixtures only
    (see `test-evidence.md`), not a real sequence of `draft → revised →
    sent_to_customer` quotes for the same job.
