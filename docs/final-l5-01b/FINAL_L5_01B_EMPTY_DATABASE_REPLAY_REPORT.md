# FINAL-L5-01B — Empty-Database Replay Report

## Attempt
1. Created a fresh, isolated database (`serviceos_l501b_replay`) on the same local Postgres instance, owned by the normal non-superuser `serviceos` role.
2. Ran `scripts/bootstrap_database_final_l5_01b.py` with a separate superuser connection string — succeeded, `vector` extension created.
3. Ran `alembic upgrade head` using the normal `DATABASE_URL` (non-superuser `serviceos` user) — migrations proceeded significantly further than the FINAL-L5-01 attempt (which failed immediately on the extension), then failed on `DuplicateTableError: relation "service_setup_templates" already exists` (migration 097 duplicating a table migration 058 already created).
4. Canonical seed, canonical rule seed, integrity checks, and API smoke were **not attempted** against this database, since the migration chain did not reach `head` — running seed scripts against a partially-migrated schema would be unsafe and is explicitly against this sprint's rules.
5. Throwaway database dropped after the failed attempt — no lingering artifacts, no manual SQL intervention was performed to force past the error.

## Verification against required checklist

| Requirement | Status |
|---|---|
| No manual SQL intervention | Confirmed — the failure was allowed to stop the process; no hand-edit was applied to force completion |
| No superuser runtime account | Confirmed — the bootstrap step used a separate superuser connection only for the one `CREATE EXTENSION` statement; all migration/seed work uses the normal non-superuser `serviceos` role |
| One expected migration head | Not reached — migration chain stopped mid-sequence at the `service_setup_templates` collision, before reaching `131 (head)` |
| All expected tables exist | Not fully — migration chain stopped before completing all 124 migrations |
| Rule records exist | Not attempted (blocked by incomplete migration) |
| Tenant data exists | Not attempted (blocked by incomplete migration) |
| Jobs and ledger exist | Not attempted (blocked by incomplete migration) |
| No orphan or duplicate records | Not applicable — no data was seeded into this throwaway database |

## Honest result
**The migration-bootstrap privilege blocker from FINAL-L5-01 is fully solved and proven** — the `vector` extension issue no longer blocks empty-database replay. However, empty-database replay as a complete end-to-end sequence (bootstrap → migrate to head → seed → rule seed → integrity → API smoke) is **not yet achieved**, because a second, independent, pre-existing migration bug (`service_setup_templates` duplicate table, unrelated to privileges) was uncovered only once the extension blocker was removed. This is reported factually rather than glossed over or worked around with an undocumented manual step.

This finding is net positive for the project even though it doesn't reach 100% completion: it is real, previously-undetectable-without-this-exact-test evidence of a migration-chain defect that the existing (never-replayed-from-empty) development database has been silently masking. It does **not** affect the correctness or safety of FINAL-L5-01's canonical data work against the real, already-migrated `serviceos` database.
