# Runtime and Documentation Drift Check

## Extension made this slice
`scripts/workflow_rearchitecture/inventory_mutation_routes.py`'s `--verify-module app.engines.booking.router` output now includes:
- `persona_breakdown` — count per persona category, computed live from `BOOKING_ROUTE_PERSONA`.
- `tenant_denominator_count` — count of routes classified `TENANT_PROVIDER_MUTATION` specifically (the only persona category that enters the canonical X/Y).
- `also_tenant_reachable_customer_routes` — the 3 customer routes also reachable by tenant_owner, for transparency (never used to inflate the tenant denominator).
- `persona_drift_detected` (only present when true) — set when any of:
  - A mounted route has no entry in `BOOKING_ROUTE_PERSONA` (`unclassified_routes` non-empty).
  - The `FALSE_POSITIVE_NON_MUTATION`-classified routes in `BOOKING_ROUTE_PERSONA` disagree with `CONFIRMED_FALSE_POSITIVE_ROUTES` for this module.
  - **New this slice**: any route in `BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES` is ALSO classified `TENANT_PROVIDER_MUTATION` in `BOOKING_ROUTE_PERSONA` (`leaked_customer` check) — this is exactly the class of bug 2F-15B introduced (a customer route counted as tenant/provider) and this slice's drift check now catches it automatically if it ever recurs.

When drift is detected, the tool appends a synthetic `{"drift": "..."}` entry to `unverified_routes`, increments `unverified_count`, and exits non-zero — the same fail-closed signal used throughout this whole initiative.

## Current result (no drift)
```
PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.booking.router
```
```json
{
  "module": "app.engines.booking.router",
  "total_routes": 11,
  "unverified_count": 0,
  "unverified_routes": [],
  "persona_breakdown": {
    "CUSTOMER_SELF_SERVICE_MUTATION": 3,
    "FALSE_POSITIVE_NON_MUTATION": 1,
    "TENANT_PROVIDER_MUTATION": 6,
    "PLATFORM_INTERNAL_MUTATION": 1
  },
  "tenant_denominator_count": 6,
  "also_tenant_reachable_customer_routes": ["cancel_booking", "create_booking", "request_reschedule"],
  "unclassified_routes": []
}
```
Exit code **0**. No `persona_drift_detected` key present (absence means false).

## Coverage-vs-runtime agreement
`tenant_denominator_count: 6` matches `canonical-tenant-coverage-recount.md`'s row-by-row reconciliation exactly. If a future code change added a 12th booking mutation route without updating `BOOKING_ROUTE_PERSONA`, this check would immediately fail (`unclassified_routes` non-empty, exit 1) rather than silently under- or over-counting the canonical figure.

## What this drift check does NOT verify
Per the mission's Workstream 12 list, two items remain proven by executed unit tests rather than the static/runtime route tool, because they require executing query-construction logic, not inspecting route metadata:
- "A creation-provenance query omits actor/customer equality" — proven by `TestActorBindingSourcePresence` (source-level assertion that `changed_by == Booking.customer_id`/`b.customer_id`/`booking.customer_id` appears at all 4 query sites) and the executed behavioral tests in `TestWrongCustomerActorCannotEstablishOrigin`.
- "Conflicting creation rows qualify" — proven by the fail-closed behavioral tests in `conflicting-creation-history-matrix.csv`'s corresponding test coverage (2F-15B's `TestMissingAmbiguousHistoryFailsClosed`, re-verified, plus this slice's new tests).
