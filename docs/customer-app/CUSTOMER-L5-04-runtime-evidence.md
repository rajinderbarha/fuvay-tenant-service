# CUSTOMER-L5-04 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to `CUSTOMER-L5-02-runtime-evidence.md` and
`CUSTOMER-L5-03-runtime-evidence.md`: this environment has no running
backend server and no reachable database. None of CUSTOMER-L5-04 §66's 15
required proof points were executed against a real system.

**Stated plainly, none of the following were done:**

- No real category was ever opened from Home against a live backend.
- No real `GET /v1/customer/categories/{id}` request ever left this machine.
- No real service list, service detail, or search request ever left this
  machine.
- No real filter/sort change was exercised against a live backend (and, per
  the contract matrix, there is little to exercise — no client-selectable
  sort exists, and the one real filter — `search` — is not wired into any UI
  this pass).
- No real pagination was exercised against a live backend.
- No real category/service deep link was resolved against a live app
  instance (only the pure `parseDeepLink`/`validateDeepLink` functions were
  exercised by unit tests with synthetic URLs).
- No real disabled/hidden category or service 404 was observed from a live
  backend.
- No real booking-boundary navigation was exercised beyond the dev-only
  placeholder screen, and even that was not run on a device/simulator this
  session — only compiled and unit-reasoned about.
- No real account switch was exercised against live search history.
- No request IDs, status codes, or screenshots from a live run exist to
  attach to this report.

## What Was Verified Instead

- The exact real backend contract for every endpoint used
  (`/v1/customer/categories/{id}`, `/v1/customer/categories/{id}/offerings`,
  `/v1/customer/categories/{id}/offerings/{id}`, `/v1/customer/search`) via
  direct source-code reading of `customer_flow/router.py` and `service.py`
  — cross-checked by an independent research pass that reached the same
  conclusions (see contract-matrix.md).
- Every client-side code path (schema validation, pagination boundary
  behavior, query-key scoping, debounce/normalization, recent-search
  isolation, booking-boundary gating) is exercised by 58 new unit tests
  using fixtures shaped exactly like the real backend's actual response
  bodies (field-for-field, taken from `service.py`'s literal dict
  construction).
- `npx tsc --noEmit`: 0 new errors (31 pre-existing, unchanged, all in
  untouched legacy `src/screens/*.tsx` files).
- `npx jest`: 370/370 passing (312 carried forward unmodified + 58 new).
- `npx eslint`: 0 errors, 36 pre-existing warnings (baseline unchanged).
- `npx prettier --check`: clean.

## Honest Gate Impact

Per CUSTOMER-L5-04 §66's acceptance criteria ("Real category opens from
Home... Real service list loads... Real search executed... No mock-only
certification"), this sprint cannot claim a hard PASS. The gate decision
reflects PARTIAL, consistent with CUSTOMER-L5-02 and CUSTOMER-L5-03's own
honest PARTIAL status for the identical, environment-level reason.

## What Would Close This Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with real `service_categories`/`master_offerings` rows, point
`EXPO_PUBLIC_API_URL` at it, authenticate a real test customer, and manually
exercise: Home → category → service list → service detail → booking
boundary, plus a real search query, plus a category/service deep link
opened cold, plus an account switch verifying the previous customer's recent
searches are gone.
