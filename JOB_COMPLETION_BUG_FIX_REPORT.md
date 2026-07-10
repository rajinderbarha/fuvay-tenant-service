# Job Completion Sprint — Bug Fix Report

## Migrations

- **093** (`093_job_credit_applied_fields.py`): adds `jobs.credit_applied` / `jobs.payable_amount`, mirroring the
  `bookings` columns added in migration 092.
- **094** (`094_payment_records_job_fields.py`): adds the 8 missing `payment_records` columns the `PaymentRecord` model
  already declared but the live table never had (`job_id`, `payment_number`, `payment_method`, `payment_status`,
  `collected_by_user_id`, `collected_by_staff_id`, `paid_at`, `notes`).

## Code changes

1. **`app/engines/field_ops/models.py`** — added `credit_applied`/`payable_amount` to `Job`.
2. **`app/engines/booking/service.py::convert_to_job`** — now copies `credit_applied`/`payable_amount` from the
   `Booking` onto the new `Job` (falls back to `quoted_price` if no credit was applied).
3. **`app/engines/field_ops/service.py::_job_dict`** — exposes `customer_credit_applied`, `payable_to_provider`,
   `payment_collection_mode` (always `"customer_pays_provider_directly"`), `platform_payment_collected` (always
   `False`) — the exact schema the ticket's Part D requires, with zero payout/withdraw/escrow language.
4. **`app/engines/field_ops/billing_service.py::record_payment`** — added a second amount check:
   `amount != job.payable_amount` → `PAYMENT_AMOUNT_MISMATCH`, enforcing "collect only the payable amount."
5. **`app/engines/booking/constants.py`** — `BOOKING_TRANSITIONS[BS.CONVERTED_TO_JOB]` changed from `[]` (dead end) to
   `[BS.COMPLETED]`.
6. **`app/engines/field_ops/billing_service.py::close_job_financial`** — now looks up the linked `Booking` and, if not
   already completed, transitions it to `BS.COMPLETED` with a `BookingStatusHistory` entry — closing the loop so
   admin/tenant/customer booking views actually show "completed."
7. **Role-naming fix (5 call sites)** — real seeded accounts use `role="technician"`, not `"staff"`. Fixed:
   - `app/engines/field_ops/staff_router.py` — role gate now accepts `("staff", "technician")`.
   - `app/engines/field_ops/router.py` — 2 occurrences of `u.role != "staff"` (accept/reject-assignment) fixed the same way.
   - `app/engines/field_ops/service.py` — 4 occurrences of `self.actor_role == "staff"` (job-ownership asserts) plus the
     `assign_staff` target-role check (`staff.role != "staff"`) fixed to accept both role strings.
   - `app/engines/field_ops/billing_service.py` — 2 occurrences (`_get_job_for_billing` ownership assert,
     `collected_by_staff_id` attribution) fixed the same way.
8. **`app/core/permissions.py`** — added a `"technician"` entry to `ROLE_PERMISSIONS` (previously absent entirely,
   meaning every real technician login got zero permissions from role defaults). Mirrors `"staff"` exactly, including
   `P.FIELD_OPS_JOBS_CLOSE` (needed for invoice/payment/commission/close — all gated on this one permission).

## Regression tests

New `tests/test_p0_job_completion_credit_deduction.py` — 20 static-inspection tests covering every fix above (migration
chain/columns, Job model fields, Booking→Job propagation, `_job_dict` schema + no-payout-language, payment-amount
enforcement, booking-completion propagation, all 5 role-naming fixes, and the `ROLE_PERMISSIONS["technician"]` gap).

Also updated 3 pre-existing test files whose assumptions were intentionally superseded by this sprint's fixes:
- `tests/test_phase9.py::test_terminal_booking_statuses_have_no_transitions` — updated to expect
  `CONVERTED_TO_JOB → [COMPLETED]` instead of `[]`, with an explanatory comment.
- `tests/test_step9_billing.py` / `tests/test_step9_smoke.py` — their shared `make_job()` mock helper didn't set
  `payable_amount`/`credit_applied`, so a MagicMock default value broke the new payable-amount check; both now default
  `payable_amount=None`, `credit_applied=Decimal("0")`.
