# Cross-App Frontend Runtime Verification — Live Smoke Report

Run against the real local Postgres DB and a live backend process (port 8000), using real seeded accounts:
tenant `f002bb6b-...` (provider@serviceos.in), technician `f8a7e369-...` (staff@serviceos.in, role=`technician`),
customer `42ee6e8a-...` (customer@serviceos.in), admin (admin@serviceos.in). Fresh JWTs obtained for all 4 roles.

Reference numbers used throughout (matching the ticket's own example): quoted_price=800, credit_applied=500,
payable_amount=300, deduction=21, wallet 1000→979.

| # | Step | Result |
|---|---|---|
| 1 | Insert test booking (quoted_price=800, status=confirmed) | ✅ |
| 2 | Issue ₹500 service credit to test customer | ✅ |
| 3 | Customer `POST /v1/me/credits/apply` | ✅ `credit_applied=500, payable_to_provider=300` |
| 4 | Customer `GET /v1/bookings/{id}` | ✅ **before fix: `credit_applied`/`payable_amount` absent from response entirely (booking_dict never exposed them). After fix: `quoted_price=800, credit_applied=500, payable_amount=300, payment_collection_mode=customer_pays_provider_directly`** |
| 5 | Tenant `GET /v1/bookings/{id}` | ✅ same numbers as customer — cross-app consistent |
| 6 | Admin `GET /v1/admin/bookings/{id}` | ✅ **before fix: 500 `PostgresSyntaxError` on every call (`:bid::uuid` bind-cast bug, pre-existing). After fix: `estimated_amount=800, credit_applied=500, payable_amount=300`** |
| 7 | Admin `GET /v1/admin/bookings?limit=1` (list) | ✅ same bug, same fix, confirmed on the list endpoint too |
| 8 | Tenant `POST /v1/bookings/{id}/convert-to-job` with technician assigned | ✅ job created, `pending_assignment` |
| 9 | Tenant `POST /v1/jobs/{id}/assign` | ✅ `status=assigned` |
| 10 | Technician `GET /v1/jobs/{id}` | ✅ `quoted_price=800, customer_credit_applied=500, payable_to_provider=300, payment_recorded=false, amount_collected=null` (matches staff-app Payment Collection card exactly) |
| 11 | Technician accept + full status lifecycle (`en_route→...→signed_off`) | ✅ all 10 transitions valid |
| 12 | Technician `POST /jobs/{id}/generate-invoice` (visit_fee=300) | ✅ `total_amount=300` |
| 13 | Technician `POST /jobs/{id}/record-payment` amount=800 (wrong) | ✅ rejected: `PAYMENT_AMOUNT_MISMATCH`, expected=300 — exact error the staff-app Record Payment modal now surfaces |
| 14 | Technician `POST /jobs/{id}/record-payment` amount=300 (correct) | ✅ `job_status=paid` |
| 15 | Technician `GET /v1/jobs/{id}` after payment | ✅ **before fix: `payment_recorded`/`amount_collected` keys absent from `_job_dict` entirely (frontend I built would show blank forever). After fix: `payment_recorded=true, amount_collected=300`** |
| 16 | Technician `POST /jobs/{id}/deduct-commission` | ✅ (after topping up empty tenant wallet to 1000) `commission_amount=21, wallet_balance_before=1000, wallet_balance_after=979` |
| 17 | Technician `POST /jobs/{id}/close` | ✅ `status=closed` |
| 18 | Tenant `GET /v1/jobs/{id}` | ✅ same numbers as technician — cross-app consistent |
| 19 | Admin `GET /v1/jobs/{id}` | ✅ same numbers again |
| 20 | Booking status after close | ✅ `completed` on customer, tenant, and admin booking views alike |
| 21 | Admin `GET /v1/admin/bookings/{id}` (final) | ✅ **before fix: `job_status` always blank (JOIN used unpopulated legacy `job_id` column). After fix: `job_status=closed, job_id=<real id>, assignment_status=assigned`** |
| 22 | Tenant `GET /v1/tenant/finance/commissions` | ✅ shows the deduction record: `job_value=300, commission_amount=21, wallet_balance_before=1000, wallet_balance_after=979` |
| 23 | Confirm no `Payout`/`Withdraw`/`Cash Wallet`/`Escrow`/`Provider Earnings Wallet` language anywhere in the fixed pages | ✅ (automated test) |

All live test data (booking, job, invoice, payment, commission record, status histories, service credit, tenant
wallet) was deleted after the run.

## Summary of what a live run caught that static inspection could not

4 of the 6 backend fixes in this sprint (`_booking_dict` gap, admin bookings `:name::type` bind bug, `ms.name`
column bug, `job_id`/`converted_job_id` JOIN bug) were **only found by actually calling the endpoints** the newly
built frontend pages depend on. Every one of them would have silently broken the exact pages this ticket asked to
verify, while passing every pre-existing static-inspection test in the suite.
