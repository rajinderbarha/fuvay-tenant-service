# Slice 2F-14D Implementation Summary

## Purpose

Close the one remaining domain-integrity question from Slice 2F-14C: prove that
`customer_id`/`booking_id`/`parent_job_id`/`service_type_id` are mutually consistent as a single
coherent `create_job` request, not merely individually valid.

## Key finding

`Booking.convert_to_job` (in `app/engines/booking/service.py`) is the pre-existing, canonical,
atomic booking-conversion pipeline — entirely separate from `field_ops.router`'s own generic
`create_job` endpoint. `create_job`'s `booking_id` field is a secondary, manual reference field,
not the same code path. This reframed the mission's scope: the relational-consistency gap lives
in `create_job`'s own logic, not in the (unmodified, out-of-scope) `Booking` engine.

## Defects found and fixed

1. **`booking_id` cross-field mismatch**: `create_job` never verified an explicitly-supplied
   `customer_id`/`service_type_id` matched the referenced booking's own values. Fixed:
   `CUSTOMER_BOOKING_MISMATCH`/`SERVICE_BOOKING_MISMATCH` (422) on disagreement.
2. **`booking_id` duplicate-conversion bypass**: `create_job` had no equivalent to
   `Booking.convert_to_job`'s own `converted_job_id`/existing-Job guards — a second Job could be
   created against an already-converted booking via this separate endpoint. Fixed:
   `JOB_ALREADY_EXISTS_FOR_BOOKING` (409), mirroring the existing pattern.
3. **`parent_job_id` cross-field mismatch**: no check that an explicitly-supplied `customer_id`
   matched the parent's own customer. Fixed: `CUSTOMER_PARENT_JOB_MISMATCH` (422). Service type
   is intentionally NOT cross-checked (matches `convert_to_repair`'s own established policy that
   a repair's service may legitimately differ from its consultation parent's).
4. **`parent_job_id` duplicate-repair bypass**: `convert_to_repair`/`spawn_repair` both already
   block a second `REPAIR` job from the same `CONSULTATION` parent — `create_job`'s own separate
   endpoint had no equivalent guard, letting a caller with `create_job`'s own permission bypass
   that established uniqueness rule directly. Fixed: mirrors the identical
   `CONSULTATION_ALREADY_CONVERTED` (409) guard.

## Coverage

**Unchanged at 169/210** (field_ops subtotal 40/40) — this slice made no router/dependency
changes, only service-layer relational-consistency fixes. Confirmed via fresh
`--verify-module` runs (both exit 0) and the unmodified `TestCanonicalCoverageRecount` suite.

## Testing

10 new deterministic tests
(`tests/test_phase2f14d_field_ops_create_job_relational_consistency.py`). Full
slice/dependency suite: 253 passed. Broad regression sweep: 1625 passed, 21 pre-existing
live-environment exclusions honestly disclosed. One pre-existing test file required a fixture
update (documented, not silent).

## Documentation correction

Slice 2F-14C's `CREATE_JOB_INTEGRITY_CLOSED`-equivalent claim is qualified — see
documentation-corrections.md.

## Final status

See approval-gate.md.
