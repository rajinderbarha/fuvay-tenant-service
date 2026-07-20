# CUSTOMER-L5-14 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server and no reachable database. None of the following
were done:

- No real `POST /customer/quotes/{quote_id}/approve` request was made
  against a live server with a real, staff-created,
  `sent_to_customer` quote.
- No real staff-triggered `send_to_customer`/`mark_revised`/`cancel`
  action was exercised to observe the resulting real `ServiceJobQuote`
  row and confirm this client's screen renders the transition correctly
  end to end.
- The opaque-500 behavior for a business-rule violation
  (financial-security-review.md) was verified by direct source reading
  of `app/exceptions.py`'s handler registration, not by triggering a real
  500 against a live server.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `quote_checklist/{models.py,constants.py,quote_service.py,
  customer_router.py,admin_router.py,provider_router.py}`,
  `execution/{models.py,constants.py,home_service_service.py,
  home_service_router.py}`, `app/main.py`'s router-mounting order,
  `app/config.py`'s `API_V1_PREFIX`, `app/exceptions.py`'s exception
  handler registration, and `invoice_payment/customer_router.py` (used
  as a comparison point to confirm the missing `/v1` prefix is a real
  outlier, not a misread) — cross-checked by an independent background
  research pass reaching the same conclusions on the orphaned
  `PartsRequest` customer-decision dead-end.
- Every client-side code path (quote-list/detail parsing including
  structural exclusion of internal-only fields and non-customer-visible
  items, per-quote/per-item resilience, actionability gating, the three
  decision mutations' cache-invalidation behavior, the extended status
  registry) is exercised by 17 new unit tests using fixtures shaped
  exactly like the real backend's actual response bodies (per the exact
  dict/field literals read from source).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 634/634 passing (617 carried forward + 17 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard, this cannot claim a hard PASS:
live runtime proof was not possible in this environment, and this
sprint's own central finding — the spec's literal "parts approval"
target is real schema with zero reachable customer action, requiring a
pivot to a separate, correctly-functioning engine — was reached entirely
through static source verification, not live observation. The gate
decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded
database with a real job, create a quote via the staff endpoint
(`POST /v1/staff/... create-quote` equivalent in `provider_router.py`),
add at least one customer-visible and one non-customer-visible item,
call `send_to_customer`, then exercise this client's Approve/Reject/
Request-revision actions in turn against fresh quotes and confirm: (a)
the non-visible item never renders, (b) approval is idempotent under a
simulated network drop and retry, (c) a deliberately-triggered business
rule violation (e.g. approving an already-decided quote) actually
surfaces as a generic 500 exactly as predicted from source, and this
client shows `quoteDecision.actionFailed` rather than crashing or
mis-reporting success.
