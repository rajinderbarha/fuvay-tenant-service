# Job Completion Sprint — Live Smoke Report

Run against the real local Postgres DB (not mocks), using real tenant `f002bb6b-...` (provider@serviceos.in), real
technician `f8a7e369-...` (staff@serviceos.in, role=`technician`), real customer `42ee6e8a-...` (customer@serviceos.in).

| # | Step | Result |
|---|---|---|
| 1 | Seed tenant wallet with 1000 usage credits | ✅ `credit_balance=1000.00` |
| 2 | Create booking, `quoted_price=800` | ✅ |
| 3 | Issue customer service credit ₹500 | ✅ |
| 4 | Apply credit via `POST /v1/me/credits/apply` | ✅ `credit_applied=500, payable_to_provider=300` |
| 5 | Confirm DB: `booking.credit_applied=500, payable_amount=300` | ✅ |
| 6 | Tenant `POST /v1/bookings/{id}/convert-to-job` with `assigned_staff_id` | ✅ job created, `pending_assignment` |
| 7 | Technician `GET /v1/staff/me/jobs/{id}` | ✅ **before fix: 403 STAFF_ACCESS_DENIED. After fix: 200**, shows `quoted_price=800, customer_credit_applied=500, payable_to_provider=300, payment_collection_mode=customer_pays_provider_directly, platform_payment_collected=false` |
| 8 | Tenant `POST /v1/jobs/{id}/assign` (real technician assignment endpoint) | ✅ **before fix: 404 STAFF_NOT_FOUND (role mismatch). After fix: 200**, `status=assigned` |
| 9 | Technician `POST .../accept` | ✅ `status=accepted`, response includes correct credit breakdown |
| 10 | Technician progresses status: `en_route → arrived → assessment_started → assessment_complete → work_started → work_complete → quality_check → quality_passed → pending_sign_off → signed_off` | ✅ all transitions valid for `repair` job type |
| 11 | Technician `POST /jobs/{id}/generate-invoice` (`visit_fee=300`) | ✅ **before fix: 403 (zero technician permissions). After fix: 200**, `total_amount=300` |
| 12 | Technician `POST /jobs/{id}/record-payment` with `amount=800` (deliberately wrong) | ✅ rejected: `PAYMENT_AMOUNT_MISMATCH`, `expected=300, received=800` |
| 13 | Technician `POST /jobs/{id}/record-payment` with `amount=300` (correct) | ✅ **before fix: 500 UndefinedColumnError on payment_records.job_id. After fix: 200**, `job_status=paid` |
| 14 | Confirm commission (usage credit) auto-deducted on payment | ✅ tenant wallet `1000 → 979` (7% of ₹300 = ₹21) |
| 15 | Technician `POST /jobs/{id}/close` | ✅ `status=closed` |
| 16 | Confirm `booking.status=completed` | ✅ **before fix: stuck at `converted_to_job` forever. After fix: `completed`** |
| 17 | Confirm `booking_status_history` shows `converted_to_job → completed, reason="Job financially closed"` | ✅ |
| 18 | Confirm `commission_records` row: `job_value=300, commission_amount=21, wallet_balance_before=1000, wallet_balance_after=979, idempotency_key` present | ✅ |
| 19 | Duplicate `POST /jobs/{id}/close` | ✅ correctly rejected: `JOB_ALREADY_CLOSED` (409) — no double deduction |
| 20 | Tenant `GET /v1/tenant/finance/commissions` | ✅ shows the same deduction record |
| 21 | Admin `GET /v1/admin/finance/commissions` | ✅ shows the same deduction record |
| 22 | Confirm no tenant payout/withdrawal record created anywhere | ✅ — only `CommissionRecord`/`WalletTransaction` (usage-credit ledger), no payout table touched |

All test data cleaned up after the run (booking, job, invoice, payment, commission record, status histories, service
credit, tenant wallet all deleted).
