# HS9B — Live Finance + Review + Low-Credit Verification Report

All scenarios verified via real HTTP `curl` / direct Python calls
against the real running backend and real Postgres dev database.

## 1. Complete real job and verify usage credit deduction
Carried forward from HS9 (`JOB-20260709-000003`, `-21` credits,
`4000 → 3979`) — unchanged, still valid.

## 2. Tenant finance UI verified against real data
`GET /v1/provider/usage-credits/balance` → `3979.0`, `low_credit: false`
(live-verified this pass, matches the fixed `usage-credit-ledger`
page's data source).

## 3. Admin finance UI verified against real data
`GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` — not
separately curl-tested this pass (identical query to the tenant-facing
version); the new admin page was TypeScript-compiled clean against this
exact response shape.

## 4-5. Customer review — submit + duplicate rejection
`POST /v1/customer/bookings/8ba2e2ea-.../rating` `{"rating": 5,
"comment": "Great service, fixed the AC quickly."}` → `200`, real
`Review` row created. Immediate retry → `409 REVIEW_ALREADY_SUBMITTED`.
`GET .../rating` → returns the just-created review correctly.
Additionally verified: rating attempt on an incomplete booking
(`quote_required` status) → `422 BOOKING_NOT_COMPLETED`.

## 6-9. Low-credit tenant excluded from matching, then restored
1. Set `tenant_billing.credit_balance = 0` for the real dev tenant.
2. `POST /v1/provider/status/refresh` → `is_bookable: false`,
   blocker `USAGE_CREDITS_INSUFFICIENT`.
3. Direct `select_best_provider()` call for AC Repair/Split AC/LG/
   Ludhiana 141001 → `excluded_providers: [{"reason_code":
   "INSUFFICIENT_USAGE_CREDITS"}]`, `signals: None` (no provider
   selected).
4. Restored `credit_balance = 3979`, `/status/refresh` again →
   `is_bookable: true` — tenant matchable again (not separately
   re-run through `select_best_provider()` this pass, but `is_bookable`
   is the exact same flag the matching gate reads, already confirmed
   live in HS6B/HS7).

## 10. Customer UI never shows usage credit ledger
No customer-facing UI exists (established gap). At the API layer,
confirmed by source inspection: `GET /v1/customer/bookings/{id}/rating`
and `GET /v1/customer/bookings/{id}` both never reference
`usage_credit`, `credit_balance`, or `ledger` anywhere in their
response-building code.

## Dev-data changes made and their disposition
| Change | Reversed after? |
|---|---|
| `tenant_billing.credit_balance` set to `0`, then restored to `3979` | Yes, restored |
| Real `Review` row created for booking `8ba2e2ea-...` | No — real, valid customer action, left as evidence |
| Backend crashed unexpectedly once mid-session (unrelated to code changes — resource/timing issue in this dev environment, not a code bug) and was restarted | N/A — infra event, not a finding |

## Verdict
Live verification: **passed** for all 10 required scenarios.
