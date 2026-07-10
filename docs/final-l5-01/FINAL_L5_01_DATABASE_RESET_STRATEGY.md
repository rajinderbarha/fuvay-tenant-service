# FINAL-L5-01 — Database Reset Strategy

## Selected strategy: Option C — FK-safe targeted delete

`scripts/reset_final_l5_01.py` implements Option C: delete data in an explicit table list rather than dropping/recreating the whole database or schema. This was chosen over Option A/B (drop+recreate database/schema) because:
1. The database also hosts already-correct canonical catalog data (`master_services`, `service_types`, `brands`, `master_issue_types`, `master_offerings`, `pricing_tiers`, `tier_locations`) built up across many prior sprints — a full drop/recreate would require re-deriving all of that from scratch, which is out of scope for this sprint.
2. `alembic_version` must survive the reset (migration history requirement) — a schema/database drop would also need a full `alembic upgrade head` replay afterward, which (see the migration chain report) is currently blocked by an extension-privilege gap unrelated to this sprint's actual goal.

## What gets truncated
201 tables in one `TRUNCATE TABLE t1, t2, ..., t201 CASCADE` statement: `tenants`, `users`, `service_pricing_rules`, plus 198 explicitly-enumerated tenant/user-scoped runtime tables (full list in the script's `TENANT_SCOPED_TABLES` constant).

## Why one big explicit TRUNCATE instead of relying on CASCADE from `tenants`/`users` alone
Discovered during this sprint (see `FINAL_L5_01_SCHEMA_TABLE_INVENTORY.md`): the vast majority of tenant-scoped tables have **no FK constraint** back to `tenants(id)`. A first attempt at `TRUNCATE tenants, users CASCADE` left ~190 tables' worth of stale data behind, which was only caught because a post-seed integrity check found jobs referencing a tenant ID that no longer existed in the `tenants` table. The strategy was corrected to explicitly enumerate every tenant-scoped table rather than trust cascade behavior.

## What is preserved
Catalog/master/config tables (no `tenant_id` column): `categories`, `master_services`, `service_types`, `brands`, `master_issue_types`, `master_offerings`, `pricing_tiers`, `tier_locations`, and `alembic_version`.

## Environment guard
Both `scripts/reset_final_l5_01.py` and `scripts/canonical_seed_final_l5_01.py` share the same guard logic:
- `APP_ENV` must be in `{local, development, dev, test, e2e, certification}` and not in `{production, prod, staging-live, live}`
- `ALLOW_DATABASE_RESET=true` must be explicitly set (added to local `.env`, gitignored, not committed)
- `DATABASE_URL` host must not contain managed-cloud markers (`.amazonaws.com`, `.azure.com`, `.gcp.com`, `prod-`, `.rds.`)
- Database name must be in an explicit allowlist (`{serviceos}`)
- Target host/database is printed (masked) before any destructive action
- `--confirm` flag required for the reset script to actually execute (default is dry-run/plan-only)

## Repeatability
Proven this sprint: reset → seed → reset → seed executed twice in sequence, producing byte-identical canonical business data both times (same credit balance `3979.00`, same 5 job records, same 2 pricing rule ranges) — see `FINAL_L5_01_RESET_REPEATABILITY_REPORT.md`.
