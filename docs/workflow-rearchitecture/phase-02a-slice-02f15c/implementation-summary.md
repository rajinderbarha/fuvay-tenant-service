# Slice 2F-15C — Implementation Summary

## Scope
Close the final Booking provenance ambiguity (actor-to-customer binding) and produce a canonical, contradiction-free tenant-facing mutation inventory.

## Code changes

### 1. Actor-to-Booking-customer binding (4 query sites)
Every provenance/relationship query previously required `changed_by_role == "customer"` alone. This proved the acting user held the customer role, but never proved that user WAS the specific Booking's own customer. Added `BookingStatusHistory.changed_by == Booking.customer_id` (or the single-booking equivalent, `b.customer_id`/`booking.customer_id`) at all 4 sites:
- `FieldOpsService._assert_tenant_customer_relationship`
- `BookingService.create_booking`'s relationship-requirement check
- `BookingService.convert_to_job`'s creator-check
- `FieldOpsService.create_job`'s direct `booking_id` reference check

The two single-booking creator checks were also refactored from `select(BookingStatusHistory.changed_by_role)` (returning a raw role string) to a filtered `select(...id).where(role == "customer", changed_by == customer_id)` (returning a match-or-None) — keeping the query interface consistent with every other provenance check in the codebase (`scalar_one_or_none()` match-or-None), rather than reading a role string into Python and comparing there.

This change has **zero effect on any legitimate case** — the customer self-booking path already guarantees `changed_by == customer_id` structurally (server-derived at the router). It closes a theoretical gap only.

### 2. Persona reclassification (corrects a 2F-15B contradiction)
2F-15B classified `create_booking`, `cancel_booking`, `request_reschedule` as `TENANT_PROVIDER_MUTATION` (counted in the tenant denominator) while ALSO reporting them as a "customer self-service subset" — a contradiction flagged explicitly in this slice's mission (unapproved item #6). Corrected: these 3 routes are now `CUSTOMER_SELF_SERVICE_MUTATION` — a single, exclusive persona, excluded from the tenant-facing denominator entirely. Their tenant-side reachability is tracked separately (`BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES`) for transparency, never re-merged.

### 3. Canonical coverage recount from the 169/210 baseline
Only the 6 genuinely tenant/provider-only routes (`confirm_booking`, `reject_booking`, `convert_to_job`, `accept_reschedule`, `reject_reschedule`, `add_note`) enter the tenant-facing denominator. Math: `169 + 6 = 175` protected, `210 + 6 = 216` total. **Final: 175/216.** The 4 non-tenant Booking rows (3 customer + 1 platform) were physically removed from `tenant-mutation-endpoint-inventory.csv` (Design A, `canonical-csv-structure.md`).

### 4. Runtime tool extension
`scripts/workflow_rearchitecture/inventory_mutation_routes.py`: `BOOKING_ROUTE_PERSONA` updated to the corrected single-persona classification; added `tenant_denominator_count` and a drift check (`leaked_customer`) that fails closed if any customer-reachable route is ever classified `TENANT_PROVIDER_MUTATION` again.

## Test results
- New file `tests/test_phase2f15c_booking_actor_customer_binding.py`: 8/8 passing.
- 4 pre-existing tests updated (2 mock-shape fixes for the query-return-type change, 1 mock-shape fix, 1 corrected assertion for the persona-labeling fix) — no behavioral regressions.
- Canonical coverage test updated to 216/175.
- Full regression sweep: **1734 passed, 9 skipped, 0 failed** (up from 1726 at the 2F-15B gate).
- Runtime verification: `booking.router` 0 unverified, exit 0, persona breakdown `{CUSTOMER_SELF_SERVICE_MUTATION: 3, TENANT_PROVIDER_MUTATION: 6, PLATFORM_INTERNAL_MUTATION: 1, FALSE_POSITIVE_NON_MUTATION: 1}`; `field_ops.router` 28/28; `field_ops.staff_router` 6/6.

## Final status
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see `approval-gate.md`.
