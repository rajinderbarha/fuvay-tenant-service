# Slice 2F-36 Scope Summary — Enterprise, Tenant-Administration and Operational Authorization

## Modules (18 canonical routes, 7 modules)

- `enterprise_grid_saved_views` (4)
- `enterprise_grid_preferences_exports` (2)
- `admin_catalog_provider_setup` (4)
- `profile_technician_self_service` (3)
- `profile_universal_self_service` (1)
- `marketing_automation_provider` (3)
- `analytics_provider_reports` (1)

Every route in this batch was confirmed this slice to already derive
tenant authority server-side (or is inherently self-service) — the
common closure pattern across all 7 modules is adding the missing
mutation-capable access-scope guard, plus a targeted ownership fix for
`enterprise_grid_saved_views`'s `set_default` route. See
[complete-service-inspection.csv](complete-service-inspection.csv).

## Held candidates (28)

`appointments`(7), `ds`(6), `inventory`(5), `catalog`(2), `dispatch`(2),
`settings`(2), `serviceability`(1), `chat`(1), `bookings`(1),
`notifications`(1). Full list:
[slice-2f36-held-scope.csv](slice-2f36-held-scope.csv).

## Batch safety note

7 separate module boundaries inside one batch — each retains its own
Set A/B/C, hashes, allow-list, contract, tests, and coverage arithmetic
per [remaining-module-boundaries.csv](remaining-module-boundaries.csv).
A batch may report mixed statuses per module (e.g. some fully closed,
some product-policy blocked) — this contract does not require one
uniform status.

## Full A/B/C sets and hashes

See [slice-2f36-scope-hashes.md](slice-2f36-scope-hashes.md).

## Full implementation contract

See [slice-2f36-implementation-contract.md](slice-2f36-implementation-contract.md).
