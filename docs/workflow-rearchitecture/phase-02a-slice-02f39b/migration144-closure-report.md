# Migration 144 / Demo-Role Closure Report — Slice 2F-39B

## Finding: Migration 144 is already applied to this database

Direct investigation against the actual database this session connects to
(`localhost:5432/serviceos` — the same database every test in this
program runs against):

1. **`alembic_version` table**: current `version_num = '144'`.
2. **`pg_constraint`**: `ck_users_role_canonical` exists on `users.role`,
   enforcing exactly:
   ```
   role IN ('super_admin', 'tenant_owner', 'staff', 'technician',
            'customer', 'guest', 'admin_operations', 'admin_finance',
            'admin_security', 'admin_readonly')
   ```
   — the 10 canonical roles, nothing else.
3. **Detection query** (`SELECT ... WHERE role NOT IN (...)`) returns
   **zero rows**.
4. **The 2 historically-flagged demo accounts**
   (`manager@demo-ac-services.local` = `tenant_manager`,
   `readonly@demo-ac-services.local` = `tenant_readonly`, per
   `docs/workflow-rearchitecture/phase-02a-slice-02b/invalid-role-remediation-recommendation.md`)
   **do not exist in this database** — a search for any email containing
   "demo" or matching either address returns zero rows.
5. Full current role distribution: 12 users, all already canonical
   (`tenant_owner`×4, `super_admin`×3, `technician`×2, `customer`×2,
   `staff`×1).

## What this means

`migrations/144_users_role_canonical_check.py`'s own `upgrade()` function
is deliberately fail-closed: it queries for invalid roles first and
**raises, refusing to apply the constraint**, if any exist — precisely to
force the demo-role decision the Slice 2B/2C documentation flagged as
requiring separate approval. The fact that this database is at revision
144 with the constraint live proves that `upgrade()`'s guard passed
cleanly, meaning **this specific database never had those 2 invalid rows
at the time the migration ran here** — the 2 accounts referenced in the
historical recommendation document are absent from this database
entirely (likely never (re)created by whatever seed process populated
it, or removed prior to migration).

## Why no remediation action was taken this slice

There is nothing to remediate: no invalid-role row exists to map to a
canonical role, and neither demo account exists to make a disposition
decision about. Per the user's own explicit choice this slice
(`"Close as no-op, document the finding"` over
`"Re-seed the demo accounts first, then remediate them"`), this is
recorded as a closed, evidence-backed finding rather than fabricated
work against accounts that don't exist in the real database.

## Historical documentation — left untouched

`docs/workflow-rearchitecture/phase-02a-slice-02b/invalid-role-remediation-recommendation.md`
remains exactly as originally written. It is a frozen historical record
of a real decision point that existed at the time it was written, in
whatever database state existed then. It is not edited or retracted here
— this report is a new, additional finding for the current database
state, not a correction of that document.

## One test fixed (`PROTECTED_BY_LATER_SLICE`)

`tests/test_phase2c_role_integrity.py::TestMigration144DetectionLogic::test_detection_query_finds_a_freshly_inserted_invalid_role`
failed when run against this database — not because of a regression, but
because the DB-level CHECK constraint now rejects the invalid-role
`INSERT` outright (`asyncpg.exceptions.CheckViolationError`) before the
test's own SELECT-based detection logic can even run. This is a
**strictly stronger** guarantee than the original test assumed. Renamed
and rewritten as
`test_invalid_role_insert_is_rejected_by_db_level_constraint`, asserting
the `IntegrityError`/`ck_users_role_canonical` rejection directly. All 7
tests in the file now pass.

## Outcome

**`MIGRATION_144_ALREADY_APPLIED_NO_ACTION_REQUIRED`** — the migration is
live, the constraint is enforced, no invalid-role accounts exist in this
database, and no demo-account role decision is pending against it. This
does not retroactively resolve the historical recommendation document's
own scenario (a different database state, a different point in time) —
it reports the current, actual state of the database this program's
tests run against.
