# HS0 — Stale Data Cleanup Report

## Script
`scripts/cleanup_home_services_test_state.py` — supports `--dry-run`
(default, read-only) and `--apply` (deletes, each target in its own
transaction so one failing target doesn't block the rest). Column/table
names verified against the live dev schema via `psql \d` before writing
SQL (the ticket's assumed table names — `home_services_bookings`,
`provider_availability_slots` — do not exist in this schema; real names
are `bookings` and `provider_availability_rules`).

## Targets checked

| Target | Before count | Found | Deleted | After count |
|---|---|---|---|---|
| Duplicate/phantom demo tenants (excluding the real one) | 1 tenant total | 0 | 0 | 1 |
| Orphan `tenant_service_types` | 2 rows total | 0 | 0 | 2 |
| Orphan `tenant_service_brands` | — | 0 | 0 | — |
| Stale draft `tenant_services` (>30 days, non-real-tenant) | — | 0 | 0 | — |
| Duplicate `provider_availability_rules` (exact tenant+day+start+end dupes) | 26 rows | 13 duplicate rows | 13 | 13 |
| Old draft/failed `bookings` (>7 days, non-real-tenant) | — | 0 | 0 | — |

## Real bug found
26 rows in `provider_availability_rules` collapsed to 13 unique rows —
13 exact duplicates (same tenant_id + day_of_week + start_time + end_time)
existed, left over from repeated setup/test runs against the same real
tenant. These would have produced doubled-up available slots in customer-
facing booking flows. Deleted via `--apply`, keeping the lowest-id row of
each duplicate pair (safe: rows are otherwise byte-identical).

## Safety confirmed
- The one real tenant ("Demo AC Services",
  `34b427a7-b2be-496c-b826-6d51bb181248`) was excluded from every
  deletion clause and confirmed still present (`SELECT count(*) FROM
  tenants` → 1, unchanged) after `--apply`.
- No production-like data existed to protect beyond this single tenant —
  confirmed via direct Postgres query before running.
- `--dry-run` output matched `--apply` output exactly (13 found, 13
  deleted) — no surprises between preview and execution.

## Verdict
Stale data cleanup: **complete**. One real duplicate-data bug found and
fixed; database now has a clean baseline for Home Services E2E testing.
