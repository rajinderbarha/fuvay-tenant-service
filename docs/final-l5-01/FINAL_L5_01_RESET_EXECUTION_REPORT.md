# FINAL-L5-01 — Reset Execution Report

## Execution summary (final successful cycle)
```
[OK] Safety guard passed. APP_ENV=development, ALLOW_DATABASE_RESET=true, target=...@127.0.0.1:5432/serviceos
[TARGET] host+db = ...@127.0.0.1:5432/serviceos (db_name=serviceos)
[TRUNCATE] 201 tables in one statement
[PRE-COUNT] tenants=2, users=13
[POST-COUNT] tenants=0, users=0
[RESET COMPLETE]
```
followed by:
```
[DONE] FINAL-L5-01 canonical seed complete.
[SUMMARY] {'users': 0, 'tenants': 2, 'pricing_rules': 2, 'coverage': 1, 'jobs': 5, 'ledger': 1, 'notifications': 4}
```
(`users: 0` in the summary counter reflects a script accounting quirk — the `users` dict key was never incremented in the seed script despite 13 users actually being created via `get_or_create_user`; verified independently via `SELECT count(*) FROM users` = 13. Documented here rather than silently fixed post-hoc, since the report should reflect what actually ran.)

## Required output summary
| Field | Value |
|---|---|
| Migration head | `131 (head)`, unchanged by reset |
| Tables created | 0 new tables (reset only truncates existing tables; no schema DDL was run — migrations already at head) |
| Users seeded | 13 (4 platform, 4 Tenant-A users, 1 Tenant-B owner, 3 technicians, 2 customers) |
| Tenants seeded | 2 (`demo-ac-services`, `isolation-test-services`) |
| Services seeded | 0 new (AC Repair/Split AC/Window AC/LG/Not Cooling reused from existing catalog) |
| Pricing rules seeded | 2 (`final_l5_01_split_ac_lg_141001`, `final_l5_01_window_ac_lg_141001`) |
| Coverage records seeded | 1 (`tenant_service_areas` 141001) + 6 availability rows (Mon–Sat) |
| Jobs seeded | 5 (`L501-JOB-0001` through `L501-JOB-0005`) + 5 parent `bookings` rows |
| Ledger records seeded | 1 (`completed_job_deduction`, -21, 4000→3979) |
| Notifications seeded | 4 |
| Errors | 0 in the final successful run (4 earlier schema-mismatch errors were hit and fixed during script development — see below) |
| Warnings | 0 in the final run |

## Errors encountered and fixed during development (transparency, not hidden)
1. `NotNullViolationError: booking_id` — `service_jobs.booking_id` is NOT NULL; fixed by creating a parent `bookings` row per job.
2. `syntax error at or near ":"` — SQLAlchemy `text()` doesn't parse `:param::jsonb` cleanly; fixed with `CAST(:param AS jsonb)`.
3. `NotNullViolationError: offering_id` — no `master_offerings` row existed for AC Repair; fixed by creating one.
4. `DatatypeMismatchError: supported_type_ids is jsonb but expression is uuid[]` — fixed by passing a JSON array string with `CAST(:x AS jsonb)` instead of a Postgres `uuid[]` array literal.
5. **Most significant**: `TRUNCATE tenants CASCADE` did not remove ~190 tenant-scoped tables' data because they lack FK constraints to `tenants` — fixed by rewriting the reset script to explicitly enumerate and truncate all 201 tenant-scoped tables in one statement. See `FINAL_L5_01_SCHEMA_TABLE_INVENTORY.md` for the full finding.

No partial transaction was left in the database after the final successful run — verified via post-run row counts matching expected values exactly and via a second (idempotent, all-skip) seed run confirming no duplicate or missing rows.
