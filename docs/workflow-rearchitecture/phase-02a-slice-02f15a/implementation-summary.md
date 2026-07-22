# Slice 2F-15A — Implementation Summary

## Scope
Close the 6 remaining unverified `booking.router` mutations left open by Slice 2F-15, and close the legacy/provider-created-Booking provenance risk 2F-15 explicitly disclosed but could not fully resolve.

## What changed

### 1. Router guard upgrades (5 routes)
| Route | Before | After |
|---|---|---|
| `cancel_booking` | `require_permission(BOOKING_CANCEL)` | `require_tenant_mutation_permission(BOOKING_CANCEL)` |
| `request_reschedule` | `require_permission(BOOKING_RESCHEDULE)` | `require_tenant_mutation_permission(BOOKING_RESCHEDULE)` |
| `accept_reschedule` | `require_permission(TENANT_UPDATE)` | `require_tenant_mutation_permission(TENANT_UPDATE)` |
| `reject_reschedule` | `require_permission(TENANT_UPDATE)` | `require_tenant_mutation_permission(TENANT_UPDATE)` |
| `add_note` | `get_current_user` (no persona check) | `require_staff_or_above_mutation` |

`BOOKING_CANCEL`/`BOOKING_RESCHEDULE` are granted to both `customer` and `tenant_owner`; `require_tenant_mutation_permission` admits both while denying only read-only tenant `access_scope`, so no legitimate customer or tenant caller is affected. `TENANT_UPDATE` is tenant_owner-only. `add_note` had no live customer caller (only tenant-portal `bookingsApi.addNote`), so it is gated provider-only, matching the field_ops `add_note` precedent from Slice 2F-14C.

### 2. `booking_preflight` reclassified
Confirmed via direct source read of `BookingService.run_booking_preflight` that it performs zero `db.add`/`db.commit` calls — it is a POST-verb query endpoint (accepts a request body), not a mutation. Added to `scripts/workflow_rearchitecture/inventory_mutation_routes.py`'s `CONFIRMED_FALSE_POSITIVE_ROUTES`. This brought `--verify-module app.engines.booking.router`'s `unverified_count` from 6 to 0, exit code 0.

### 3. Legacy/provider-created Booking provenance closure
Discovered that `BookingStatusHistory`'s creation-time row (`from_status IS NULL`) already and reliably records `changed_by_role` — whether a Booking was created by a `customer` or by a `tenant_owner` acting on the customer's behalf — with **no new column or migration** (respects the explicit out-of-scope constraint).

Using this, tightened:
- `FieldOpsService._assert_tenant_customer_relationship` — a qualifying-status Booking must now also be customer-originated to establish relationship authority.
- `BookingService.create_booking`'s own relationship-requirement check — identical tightening, for consistency between the two enforcement points.
- `Booking.convert_to_job` — a provider-created Booking now additionally requires INDEPENDENT prior relationship evidence (a different customer-originated Booking, or a source-derived Job, excluding the Booking being converted) before it may convert.
- `FieldOpsService.create_job`'s direct `booking_id` path — identical independent-evidence requirement, closing the bypass where a legacy/provider-created Booking could be fed directly into `create_job` instead of `convert_to_job`.

## Test results
- New file `tests/test_phase2f15a_booking_provenance_and_remaining_routes.py`: 8/8 passing.
- 4 pre-existing tests required mock-scaffolding updates (additional `db.execute()` call from the new provenance queries) — no behavioral logic changed. All fixed and passing.
- Full regression sweep (`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking"`): **1713 passed, 9 skipped, 0 failed**.

## Runtime verification
- `app.engines.booking.router`: 0/10 unverified, exit 0 (10 = 11 mounted routes minus 1 reclassified false positive).
- `app.engines.field_ops.router`: 0/28 unverified, exit 0 (unchanged, re-confirmed).
- `app.engines.field_ops.staff_router`: 0/6 unverified, exit 0 (unchanged, re-confirmed).

## Coverage reconciliation
Canonical coverage moves from the provisional **174/221** (2F-15 baseline) to **179/220** (see `canonical-coverage-reconciliation.md`): +5 newly protected routes, -1 denominator correction (preflight reclassified as non-mutation).

## Final status
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see `approval-gate.md`.
