# Slice 2F-14F Implementation Summary

## Purpose

Implement and verify the ratified secure interim customer-authority policy for
`FieldOpsService.create_job`, closing the last open question from Slice 2F-14E: manual customer
authority.

## Implementation

1. **`_assert_tenant_customer_relationship(tenant_id, customer_id)`** — a new, minimal, read-only
   service helper querying only the existing `Booking` and `field_ops.Job` tables (no new model,
   no migration) for at least one same-tenant row referencing the requested customer.
2. Called from `create_job` **only** in standalone-manual mode (neither `booking_id` nor
   `parent_job_id` supplied) — booking-referenced and parent-derived creation already prove the
   relationship intrinsically through their own existing cross-checks, confirmed by 2 tests
   proving no redundant query is issued for those modes.
3. **Disabled/deleted customer check** added to the existing customer-account validation:
   `customer_user.is_active`/`customer_user.deleted_at` now checked, mirroring
   `Booking.convert_to_job`'s existing `staff.is_active` pattern. All four "not a valid customer"
   cases (missing, wrong-role, disabled, deleted) reuse the identical `FOREIGN_CUSTOMER` error
   code to prevent account-state enumeration via the error response.

## Relationship predicate

`ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` — any Booking or Job row (any status) with matching
`tenant_id`+`customer_id` counts, since neither model carries a soft-delete/scaffold marker to
filter on. See tenant-customer-relationship-contract.md.

## Coverage

**Unchanged at 169/210** (field_ops subtotal 40/40) — no router/dependency changes were made.
Confirmed via fresh `--verify-module` runs (both exit 0).

## Testing

10 new deterministic tests
(`tests/test_phase2f14f_field_ops_manual_customer_authority.py`). Full slice/dependency suites:
185 passed. Broad regression sweep: 1681 passed, 0 failed this run. Two pre-existing test files
required fixture updates (documented, not silent) to explicitly set customer-account state
fields.

## Documentation correction

Slice 2F-14E's `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PRODUCT_POLICY_BLOCKED` status is superseded
— see documentation-corrections.md.

## Final status

See approval-gate.md.
