# Cross-App Frontend Runtime Verification Sprint — Fix Report

## Frontend fixes

| Page | Fix |
|---|---|
| Tenant booking detail (`bookings/[id]/page.tsx`) | Added Payment Breakdown card: Service Price, ServiceOS Credit Applied, Payable To Provider, Payment Mode, Platform Collected Payment; link to job payment status |
| Tenant job detail (`jobs/[id]/page.tsx`) | Added Payment Collection + Usage Credit Deduction cards; removed "Commission" row (duplicated by new section); reworded close-job modal copy from "deduct commission from your wallet" to "Completed Job Deduction… Provider usage credits are not real money and are not withdrawable" |
| Tenant finance ledger (`finance/page.tsx`) | Renamed "Commission" tab → "Usage Credits"; "Commission History" → "Usage Credit Ledger"; each row now reads "Completed Job Deduction — {job}"; amounts labeled "credits" not "₹ commission" |
| Admin booking detail (`admin/bookings/[id]/page.tsx`) | Added Payment Breakdown card: Quoted Price, Customer Credit Applied, Payable To Provider, Payment Collection Mode, Payment Recorded, Amount Collected |
| Admin job detail (`admin/operations/[jobId]/page.tsx`) | Added "Payment / Credit / Deduction Record" card; renamed header commission badge to "usage credit deduction" |
| Staff app job detail (`mobile/staff-app/JobDetailScreen.tsx`) | **New** Payment Collection card + Record Payment modal (amount/mode/note) wired to `jobsApi.recordPayment`; job completion now blocked until payment recorded when a payable amount is owed; success alert reads "Provider usage credit deduction will be applied to tenant account" |
| Customer app booking detail (`mobile/customer-app/BookingDetailScreen.tsx`) | Added Payment Breakdown card: Service Price, ServiceOS Credit Used, Paid Directly To Provider, plus the required "you will pay the remaining amount directly to the provider" note |

## API client / type fixes (Part F)

- `frontend/tenant-portal/lib/api.ts`: added `BookingPaymentBreakdown`/`JobPaymentBreakdown` types; extended `Job`/`Booking` interfaces with `customer_credit_applied`, `payable_to_provider`, `payment_collection_mode`, `platform_payment_collected`, `amount_collected`, `payment_recorded`, `credit_applied`, `payable_amount`; added `jobsApi.recordPayment()`.
- `frontend/super-admin/lib/api.ts`: extended `Job`/`AdminBooking` interfaces with the same fields.
- `mobile/staff-app/src/lib/api.ts`: extended `Job` interface; added `jobsApi.recordPayment()`.
- `mobile/customer-app/src/lib/api.ts`: extended `Booking` interface with `quoted_price`, `credit_applied`, `payable_amount`.

## Backend runtime bugs found and fixed (discovered only by live testing, not static inspection)

Static-inspection tests cannot catch these — they were only found by actually calling the real APIs the fixed frontend pages depend on.

1. **`_booking_dict()` never exposed `credit_applied`/`payable_amount`** (`app/engines/booking/service.py`) — the columns existed in the DB (migration 092) and were used internally, but `GET /v1/bookings/{id}` never returned them to ANY app (customer, tenant, or admin). Every page I built to display this data would have shown blank/undefined values. Fixed by adding the 4 fields to `_booking_dict`.
2. **Admin bookings SQL never exposed `credit_applied`/`payable_amount`/`payment_recorded`** (`app/engines/booking/admin_router.py`) — same root issue, admin-specific raw-SQL query. Fixed by adding 3 SELECT columns + dict fields.
3. **`:name::type` bind-parameter casts broke asyncpg query compilation platform-wide in this file** — `WHERE b.id = :bid::uuid` (and 9 other occurrences: `:tenant_id::uuid`, `:customer_id::uuid`, `:service_id::uuid`, `:uid::uuid`) caused `PostgresSyntaxError: syntax error at or near ":"` on every admin booking list/detail/cancel/void call, live-reproduced independent of this sprint's edits (pre-existing). **This meant `/v1/admin/bookings` and `/v1/admin/bookings/{id}` were completely broken in production before this sprint** — the admin booking detail page could never have worked. Fixed by rewriting all 10 occurrences to `CAST(:name AS type)`.
4. **`COALESCE(ms.name, ...)` referenced a non-existent column** — `master_services` has `service_name`, not `name`. Caused `UndefinedColumnError` on every admin bookings query once bug #3 was fixed and the query could actually reach Postgres. Fixed to `ms.service_name`. (A pre-existing test, `test_admin_router_service_name_from_join`, literally asserted the broken `"ms.name"` string was present — updated to assert the correct `"ms.service_name"` with a comment explaining why.)
5. **Admin bookings JOIN used the legacy, always-NULL `bookings.job_id` column instead of `bookings.converted_job_id`** — `convert_to_job` only ever populates `converted_job_id` (confirmed via direct DB query), so `job_status`, `assignment_status`, `sla_breached`, and the job-detail deep-link were blank/wrong on every admin booking that had been converted to a job. Fixed the JOIN and the exposed `job_id` field to `COALESCE(b.job_id, b.converted_job_id)`.
6. **`field_ops/service.py::_job_dict` never derived `payment_recorded`/`amount_collected`** — needed by the new staff-app/tenant/admin payment-collection UI. Since `record_payment()` already enforces `amount == payable_amount` (`PAYMENT_AMOUNT_MISMATCH` otherwise), these are safely derived from `j.payment_id is not None` and `j.paid_at`, without an extra join.

All 6 backend fixes were verified live end-to-end (see `CROSS_APP_FRONTEND_LIVE_SMOKE_REPORT.md`) and covered by new regression tests in `tests/test_p0_cross_app_frontend_runtime.py`.

## Mock data removal

No production mock data was found on any of the 14 audited pages (see `CROSS_APP_FRONTEND_AUDIT.md`) — all pages already called real API endpoints. The gap was never "mock data," it was **backend fields silently missing from real API responses** and **two live-breaking SQL bugs in the admin bookings endpoint that had never been exercised end-to-end**.

## Terminology cleanup

- Removed "deduct commission from your wallet" (tenant job close modal) → "Completed Job Deduction… not real money… not withdrawable."
- Renamed tenant finance "Commission" tab/section → "Usage Credits" / "Usage Credit Ledger" / "Completed Job Deduction" row labels.
- Renamed admin job detail header badge "commission" → "usage credit deduction."
- No `Payout`/`Withdraw`/`Cash Wallet`/`Escrow`/`Provider Earnings Wallet` term exists on any of the 6 job-completion-facing pages fixed this sprint (verified by an automated forbidden-term scan test). The tenant Finance "Payouts" tab is a **separate, pre-existing feature** (tenant subscription/deposit refunds unrelated to job completion) — flagged, not removed; see `REMAINING_BLOCKERS.md`.
- "Platform Payment: Not collected by ServiceOS" is intentionally present per the ticket's own Part C spec (a negation disclosure, not a payout feature name).
