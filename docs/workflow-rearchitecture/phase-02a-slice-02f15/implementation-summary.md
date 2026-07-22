# Slice 2F-15 Implementation Summary

## Purpose

Close the customer-identity and confirmation-provenance vulnerability disclosed in Slice 2F-14G:
a `tenant_owner` could create a Booking naming an unrelated real customer, self-confirm it, and
use it as `field_ops` relationship evidence.

## Exact model confirmed

`app.engines.booking.models.Booking` — the same model used by `create_booking`,
`confirm_booking`, `Booking.convert_to_job`, and `FieldOpsService._assert_tenant_customer_relationship`.
Confirmed entirely distinct from `ServiceBooking` (unmodified).

## Fixes

1. **`BookingService.create_booking` customer validation**: when the acting persona is not
   `customer` (the tenant-assisted override path), `customer_id` must now resolve to a real,
   active, non-deleted `customer`-role account — mirrors `FieldOpsService.create_job`'s own
   pattern (Slice 2F-14C).
2. **`BookingService.create_booking` relationship requirement**: the same non-customer path now
   additionally requires an existing same-tenant relationship (a `CONFIRMED`-or-later Booking, or
   a source-derived `field_ops.Job`) for that customer — reusing
   `FieldOpsService._assert_tenant_customer_relationship`'s exact qualifying rule (Slice 2F-14G),
   duplicated minimally into the booking engine rather than shared via a cross-engine call.
   Customer self-booking is entirely unaffected — it remains the legitimate first-contact path.
3. **Router guard upgrades**: `create_booking`, `confirm_booking`, `reject_booking`,
   `convert_to_job` upgraded from `require_permission` to `require_tenant_mutation_permission` —
   the same access-scope-aware fix pattern established across the field_ops series.

## Confirmed NOT necessary

No change was made to `FieldOpsService._assert_tenant_customer_relationship` itself, to
`Booking.convert_to_job`, or to `confirm_booking`'s own transition/ownership logic — all were
already correct; the vulnerability lived entirely in `create_booking`'s missing validation.

## Coverage

169/210 → **174/221** (11 new `booking.router` rows tracked for the first time; 4 newly protected
this slice; 1 already-protected `void_booking` newly counted; 6 rows remain explicitly
out-of-scope, documented not silently ignored).

## Testing

9 new deterministic tests
(`tests/test_phase2f15_booking_customer_identity_and_confirmation.py`), including a direct
reproduction of the Slice 2F-14G bootstrap attack proving it now fails. Full slice/dependency
suites: 217 passed. Broad regression sweep: 1707 passed, 0 failed. `test_step4_booking.py`'s 44
tests required zero changes.

## Documentation correction

Slice 2F-14G's provenance-blocked status is superseded — see documentation-corrections.md.

## Final status

See approval-gate.md.
