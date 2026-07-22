# Slice 2F-14G Implementation Summary

## Purpose

Audit the provenance of the Booking/Job "relationship evidence" `_assert_tenant_customer_relationship`
(Slice 2F-14F) relies on, and tighten it where the evidence proves it can be fabricated or is
untrustworthy.

## Key finding

`BookingService.create_booking` lets a `tenant_owner` supply an arbitrary, unvalidated
`customer_id` (no User-table check, unlike `create_job`'s own validation) — the resulting Booking
(initial status `BS.PENDING_CONFIRMATION`) previously satisfied Slice 2F-14F's
`ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` predicate immediately, letting a tenant bootstrap
relationship "evidence" for a real, unrelated customer with a single API call and zero customer
participation.

## Fixes

1. **Booking status gating**: only statuses structurally unreachable except by first passing
   through `BS.CONFIRMED` (`confirmed`, `scheduled`, `dispatching`, `in_progress`, `completed`,
   `converted_to_job`) now qualify. All 7 non-qualifying statuses
   (`draft`/`pending`/`pending_confirmation`/`rejected`/`expired`/`cancelled`/`voided`) closed —
   `cancelled`/`voided` excluded too since current status alone can't prove prior confirmation.
2. **Legacy Job-row exclusion**: a "generic" standalone Job (both `booking_id` and
   `parent_job_id` null) carries no field distinguishing a post-hardening validated row from a
   pre-hardening arbitrary one — excluded from evidence entirely. Only Job rows with a non-null
   `booking_id` or `parent_job_id` (structurally derived from an already-validated source) now
   qualify.

## Residual, disclosed risk

A `tenant_owner` can still self-confirm their own fabricated Booking (`confirm_booking` requires
no customer participation), reaching a now-qualifying status without genuine customer contact.
Closing this requires modifying `BookingService.create_booking`/`confirm_booking` in the booking
engine — outside this slice's scope (confined to the `create_job` relationship helper). Disclosed
honestly, not silently left unaddressed — see known-limitations.md, relationship-evidence-threat-model.md.

## Coverage

**Unchanged at 169/210** (field_ops subtotal 40/40) — no router/dependency changes were made.
Confirmed via fresh `--verify-module` runs (both exit 0).

## Testing

17 new deterministic tests
(`tests/test_phase2f14g_field_ops_relationship_provenance.py`), parametrized over all 7
non-qualifying and 6 qualifying real Booking statuses. Full slice/dependency suites: 202 passed.
Broad regression sweep: 1698 passed, 0 failed. No pre-existing test file required a fixture
update.

## Documentation correction

Slice 2F-14F's `CUSTOMER_AUTHORITY_CLOSED` claim is superseded — see documentation-corrections.md.

## Final status

See approval-gate.md.
