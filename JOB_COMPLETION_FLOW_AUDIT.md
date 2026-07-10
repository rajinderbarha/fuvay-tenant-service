# Job Completion + Provider Collection + Usage Credit Deduction — Flow Audit

## APIs found (all real, pre-existing)

| Purpose | Endpoint | File |
|---|---|---|
| Tenant confirms booking | `POST /v1/bookings/{id}/confirm` | `app/engines/booking/router.py` |
| Convert booking → job (+ optional technician assignment) | `POST /v1/bookings/{id}/convert-to-job` | `app/engines/booking/router.py` → `BookingService.convert_to_job` |
| Explicit technician assignment | `POST /v1/jobs/{id}/assign` | `app/engines/field_ops/router.py` → `FieldOpsService.assign_staff` |
| Technician job detail | `GET /v1/staff/me/jobs/{id}` | `app/engines/field_ops/staff_router.py` |
| Technician accept/reject assignment | `POST /v1/staff/me/jobs/{id}/accept` / `reject-assignment` | `staff_router.py` |
| Job status lifecycle | `PUT /v1/staff/me/jobs/{id}/status` | `staff_router.py` → `FieldOpsService.update_status` |
| Invoice generation | `POST /v1/jobs/{id}/generate-invoice` | `router.py` → `BillingService.generate_invoice` |
| Payment recording | `POST /v1/jobs/{id}/record-payment` | `router.py` → `BillingService.record_payment` |
| Commission (usage credit) deduction | `POST /v1/jobs/{id}/deduct-commission` (also auto-fires on payment) | `BillingService.deduct_commission` → `CommerceService.deduct_commission` |
| Job financial close | `POST /v1/jobs/{id}/close` or `/financial-close` (atomic) | `BillingService.close_job_financial` / `financial_close` |
| Tenant/admin ledger view | `GET /v1/tenant/finance/commissions`, `/v1/admin/finance/commissions` | `tenant_finance_router.py`, `admin_finance_router.py` |

No new endpoints were required — every capability the ticket asks for already existed. The problems were entirely in
**data propagation**, **role-naming**, and **schema drift**, not missing APIs.

## Missing APIs

None. The ticket's suggested paths (`/v1/provider/bookings/{id}/accept`, `/v1/staff/jobs/{id}/complete`, etc.) are covered
by the existing `confirm`/`convert-to-job`/`assign`/`status`/`close` pipeline under different but equivalent paths.

## Broken persistence / bugs found (all fixed this sprint — see BUG_FIX_REPORT)

1. `Job` never carried `credit_applied`/`payable_amount` from its originating `Booking` — technician had no way to know
   the correct collect amount.
2. `record_payment` never validated against `job.payable_amount` — a technician could be told to (or accidentally)
   collect the full quoted price even after a credit was applied.
3. `Booking.status` had no valid transition out of `converted_to_job` — bookings never reached `completed` even after
   the linked job fully closed, breaking admin/tenant/customer view consistency.
4. Real seeded technician accounts have `role="technician"`, but `field_ops/router.py`, `staff_router.py`, and multiple
   `actor_role`/`staff.role` comparisons inside `field_ops/service.py` and `billing_service.py` only ever checked for the
   literal string `"staff"` — **every real technician account was rejected everywhere in this flow.**
5. `ROLE_PERMISSIONS` had no `"technician"` key at all — real technician logins got **zero** permissions from role
   defaults, silently blocking `generate-invoice`/`record-payment`/`deduct-commission`/`close` (all gated on
   `P.FIELD_OPS_JOBS_CLOSE`).
6. `payment_records` table was missing 8 columns the `PaymentRecord` model declares (`job_id`, `payment_number`,
   `payment_method`, `payment_status`, `collected_by_user_id`, `collected_by_staff_id`, `paid_at`, `notes`) — every real
   `record_payment()` call 500'd with `UndefinedColumnError`.

## Mock-only flows

None found in this specific pipeline — every step is backed by real DB writes. The bugs were connectivity/schema gaps,
not mock stand-ins.

## Frontend/API mismatches

Not assessed in depth this sprint (backend-focused per scope) — `frontend/tenant-portal` booking/job pages were not
re-verified against the corrected API responses. This is a real gap noted in `REMAINING_BLOCKERS.md`.

## Ledger bugs / duplicate deduction risk

None found — `commission_deducted` boolean + `CommissionRecord.job_id` lookup already provides correct idempotency,
verified live (a second `/close` call correctly returns `JOB_ALREADY_CLOSED`, and `deduct_commission` itself is
idempotent and returns `"idempotent": True` on a repeat call rather than double-deducting).
