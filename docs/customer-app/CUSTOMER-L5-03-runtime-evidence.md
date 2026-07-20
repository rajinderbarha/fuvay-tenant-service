# CUSTOMER-L5-03 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to `CUSTOMER-L5-02-runtime-evidence.md`: this
environment has no running backend server and no reachable database. None
of CUSTOMER-L5-03 §58 ("Live Runtime Certification") or §59 ("Database
Evidence")'s 15 required proof points were executed against a real system.

**Stated plainly, none of the following were done:**

- No real customer ever authenticated against a live backend in this
  session for this pass.
- No real `GET /v1/customer/categories` request ever left this machine.
- No real categories were ever rendered from a live response.
- No real navigation from a category card was exercised (there is also no
  destination to navigate to yet — see contract matrix).
- No real pull-to-refresh against live data.
- No real account-switch isolation was proven against a live backend
  (only unit-level session-clearing was proven — see CUSTOMER-L5-02 test
  evidence).
- No screenshots, request IDs, or status codes from a live run exist to
  attach to this report.

## What Was Verified Instead

- The exact real backend contract (`GET /v1/customer/categories`'s
  request/response shape) via direct source-code reading of
  `app/engines/customer_flow/router.py`/`service.py` — this is source-
  level contract verification, not runtime verification.
- Every client-side code path (schema validation, deduplication, ordering,
  cap, visibility evaluation, module-registry resolution, query-key
  scoping) is exercised by real unit tests using fixtures shaped exactly
  like the real backend's actual response bodies.
- `HomeScreen`'s render logic was verified by TypeScript compilation and
  manual code review, not by mounting the component (no component test
  exists — see test evidence).

## Honest Gate Impact

Per CUSTOMER-L5-03 §66 ("Runtime" acceptance criteria: "Real Home API
executed... Real categories rendered... Real navigation executed... Real
account-switch isolation proven... No mock-only certification") and §67's
report format, this sprint cannot claim a hard PASS. The gate decision
reflects PARTIAL, consistent with CUSTOMER-L5-02's own honest PARTIAL
status for the identical reason.

## What Would Close This Gap

Identical remediation to CUSTOMER-L5-02: run the actual backend
(`uvicorn app.main:app` or the repository's real startup command) against
a seeded database, point `EXPO_PUBLIC_API_URL` at it, authenticate a real
test customer, and manually exercise `HomeScreen` while inspecting the
`service_categories`/`master_offerings` tables directly for the isolation
and correctness claims this document could not make.
