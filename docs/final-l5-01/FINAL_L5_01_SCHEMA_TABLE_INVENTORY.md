# FINAL-L5-01 — Active Schema and Table Inventory

## Headline scale
- 357 tables in `public` schema at migration head `131`
- 1 schema (`public`)
- ~190 tables carry a `tenant_id` column; of those, the overwhelming majority (see below) have **no FK constraint** back to `tenants(id)` — a systemic schema gap discovered while building the reset script for this sprint.

## Major finding: missing tenant FK constraints
`TRUNCATE tenants CASCADE` was attempted as the first reset strategy and only removed 2 tables' worth of dependent data — everything else (`service_jobs`, `bookings`, `usage_credit_ledger`, `in_app_notifications`, etc.) silently survived because Postgres `TRUNCATE ... CASCADE` only follows *declared* foreign keys, and a direct query against `pg_constraint` confirmed **zero FK constraints exist on `service_jobs` at all**, and ~190 tenant-scoped tables lack an FK to `tenants`. Full list captured in `scripts/reset_final_l5_01.py::TENANT_SCOPED_TABLES`. This is a real, load-bearing finding for future schema hardening (referential integrity is enforced entirely at the application layer, not the database layer, for the majority of tenant-scoped tables) — carried to `FINAL_L5_01_REMAINING_BLOCKERS.md`, not fixed in this sprint (fixing it would require ~190 new migrations and is out of scope for a data-seeding certification sprint).

## Key tables (classification)

| Table | Classification | Notes |
|---|---|---|
| `users` | CANONICAL_ACTIVE | No FK enforcement on `tenant_id`; role stored as free-text column (`role`, `platform_role`) |
| `tenants` | CANONICAL_ACTIVE | Root tenant table; `slug` is the stable lookup key used by the canonical seed |
| `tenant_billing` | CANONICAL_ACTIVE | **Active credit balance source** per mission rule — `credit_balance` column |
| `tenant_wallets` | DORMANT_UNUSED | Exists, has `credit_balance` column too, but the canonical seed does NOT write to it — confirmed dormant per mission rule; legacy compatibility only |
| `usage_credit_ledger` | CANONICAL_ACTIVE | `event_type='completed_job_deduction'` rows drive the exactly-once deduction; `balance_before`/`credit_delta`/`balance_after` all present and verified arithmetically correct |
| `service_jobs` | CANONICAL_ACTIVE | **Canonical Home Services jobs source** per mission rule; NOT NULL `booking_id` (FK-less) and `offering_id` (FK-less) — both had to be populated via `bookings`/`master_offerings` rows during seed script development |
| `jobs` | LEGACY_READ_ONLY | Separate legacy operations table exists alongside `service_jobs`; not touched or seeded this sprint (out of scope; documented in prior FINAL-L5-00 audit as the Field-Ops/Home-Services split) |
| `bookings` | ACTIVE_SUPPORTING | Required parent of `service_jobs` (NOT NULL `booking_id` FK-in-name-only) |
| `service_pricing_rules` | CANONICAL_ACTIVE | Reseeded with 2 canonical rules this sprint (`final_l5_01_split_ac_lg_141001`, `final_l5_01_window_ac_lg_141001`); 9 pre-existing rules from prior sprints were truncated as part of reset |
| `master_services`, `service_types`, `brands`, `master_issue_types`, `master_offerings` | CANONICAL_ACTIVE (catalog) | Deliberately preserved across reset — not tenant-scoped, already correct from prior sprints; one new `master_offerings` row ("AC Repair") added since none existed for the AC Repair category |
| `provider_enabled_offerings` | CANONICAL_ACTIVE | Tenant provider setup — 1 row created enabling Split AC + Window AC + LG for Demo AC Services |
| `tenant_service_areas` | CANONICAL_ACTIVE | Coverage — 141001 active/primary for Demo AC Services |
| `provider_availability_rules` | CANONICAL_ACTIVE | 6 rows (Mon–Sat) per tenant, 09:00–18:00 with 13:00–14:00 break |
| `in_app_notifications` | CANONICAL_ACTIVE | 4 canonical notifications seeded (admin/tenant/customer/staff, mixed read/unread) |
| `tenant_package_assignments`, `customer_addresses` | ACTIVE_SUPPORTING | Populated by pre-existing `seed_phase0_baseline.py` logic in prior sprints; not re-touched this sprint beyond the reset (truncated, not reseeded — see remaining blockers) |
| `alembic_version` | MIGRATION_HISTORY | Untouched by reset (not in `TENANT_SCOPED_TABLES`); confirms migration head persists across reset |

## Full machine-readable inventory
See `schema-table-inventory.json` for the complete 357-table list with row counts captured post-seed.
