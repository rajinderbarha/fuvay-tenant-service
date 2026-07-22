# Slice 2F-14E Implementation Summary

## Purpose

Close the four remaining questions from Slice 2F-14D: Booking status eligibility, parent Job
status/type eligibility, manual customer authority, and `booking_id`+`parent_job_id`
coexistence — for `FieldOpsService.create_job`.

## Findings and fixes

1. **Booking status eligibility.** `booking_id`'s existing customer/service cross-check and
   duplicate-conversion guard make it an `AUTHORITATIVE_LINEAGE_REFERENCE`, not merely
   informational. Fixed: `booking.status == BS.CONFIRMED` is now required, mirroring
   `Booking.convert_to_job`'s own established prerequisite — all 12 other real Booking statuses
   are now rejected (`BOOKING_INVALID_STATUS_TRANSITION`).
2. **Parent Job status eligibility (CONSULTATION→REPAIR only).** Where `create_job` with a
   CONSULTATION parent + REPAIR job_type is semantically equivalent to `convert_to_repair`'s own
   capability, the identical `JS.QUOTE_APPROVED` prerequisite is now enforced
   (`CONSULTATION_CONVERSION_NOT_ALLOWED` otherwise). No status gate was added for other
   parent/child combinations — no established policy exists for those.
3. **`booking_id` + `parent_job_id` coexistence.** No safe combined semantics were ever
   established anywhere in this codebase. Fixed: simultaneous use is now rejected before
   persistence (`AMBIGUOUS_JOB_SOURCE`).
4. **Manual customer authority.** Investigated exhaustively (Workstream 5/6) — no tenant/customer
   relationship model exists anywhere in this codebase, and requiring one would make it
   impossible to ever create the first Job for a legitimately new customer (no other
   customer-onboarding path exists). Recorded as `PRODUCT_DECISION_REQUIRED`, not fixed with an
   invented relationship rule — this is not a security gap, since a Job's customer_id association
   grants no elevated access to that customer's other data.

## Coverage

**Unchanged at 169/210** (field_ops subtotal 40/40) — no router/dependency changes were made.
Confirmed via fresh `--verify-module` runs (both exit 0).

## Testing

31 new deterministic tests
(`tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py`), parametrized over every
real Booking status (12) and every real non-QUOTE_APPROVED Job status (12) as a CONSULTATION
parent. Full slice/dependency suites passing (138/253 across combined runs). Broad regression
sweep: 1656 passed, the same pre-existing live-environment exclusion class honestly disclosed.
One pre-existing test file required a fixture update (documented, not silent).

## Documentation correction

Slice 2F-14D's `CREATE_JOB_RELATIONAL_INTEGRITY_CLOSED` claim is qualified — see
documentation-corrections.md.

## Final status

See approval-gate.md.
