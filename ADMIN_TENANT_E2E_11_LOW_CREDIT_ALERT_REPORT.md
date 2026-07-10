# ADMIN-TENANT-E2E-11 — Low Credit Alert Report

## Threshold source
Backend-derived, not frontend-hardcoded: `app/engines/provider_portal/router.py`
computes `"low_credit": balance < 20` server-side and returns it as part
of `GET /v1/provider/usage-credits/balance`. Not stored in a per-tenant
config table (a fixed platform-wide constant), but genuinely
backend-computed rather than a UI literal.

## Checks
1. Threshold from backend — confirmed (see above).
2. UI doesn't hardcode an impossible threshold — confirmed, the frontend
   only reads `balance.data?.low_credit` (a boolean the backend already
   computed), never re-derives its own threshold.
3. Low-credit state readable — the ledger page renders a "Low Credit
   Status: Low / Healthy" stat card, color-coded (danger-red for Low).
4. Alert explains impact — **not tested live**, because the real tenant
   balance (3937) is far above the 20-credit threshold, and this pass
   did not artificially zero the balance to force the low state (unlike
   HS9B, which did this via a direct DB update-and-restore for a
   different verification). Not exercising a live low-balance state this
   pass is a documented limitation, not a claim that it was verified.
5. No wallet/top-up wording implying customer payment — confirmed, no
   such copy found in either finance page.
6. Alert doesn't block unrelated pages — confirmed by inspection; the
   `low_credit` flag only affects the one stat card's color, no global
   blocking banner exists.

## Verdict
Backend mechanism confirmed real and correctly wired to the frontend.
The actual "balance below threshold" visual state was **not** exercised
live this pass (current real balance is healthy) — documented honestly
rather than fabricated with a forced DB edit, since this ticket didn't
require creating a new test scenario for it the way HS9B's low-credit
matching-restriction check did.
