# FINAL-L5-01 — Database Runbook

All commands assume `cd g:\serviceos` and a POSIX-ish shell (Git Bash). Every command below requires the environment guard variables to be set first:

```bash
export APP_ENV=development          # or local/dev/test/e2e/certification — never production
export ALLOW_DATABASE_RESET=true    # required by both reset and seed scripts
export DATABASE_URL="postgresql+asyncpg://<user>:<pass>@127.0.0.1:5432/serviceos"
```

(These are already present in the local `.env`, gitignored — the `export $(grep -E "^(APP_ENV|ALLOW_DATABASE_RESET|DATABASE_URL)" .env | xargs -d '\n')` shell idiom was used throughout this sprint to load them into the shell for scripts that read `os.getenv` directly.)

## Create a safe local database
Already exists at `127.0.0.1:5432/serviceos` (bundled local PostgreSQL 16 install under `db/pgsql`, discovered in FINAL-L5-00). To create a fresh throwaway database on the same instance for experimentation:
```bash
"db/pgsql/bin/createdb.exe" -h 127.0.0.1 -p 5432 -U <user> <new_db_name>
```
Note: a fresh database on this instance currently **cannot** run `alembic upgrade head` to completion due to a `CREATE EXTENSION vector` superuser-privilege requirement — see `FINAL_L5_01_MIGRATION_CHAIN_REPORT.md`. Have a superuser run `CREATE EXTENSION vector;` on the new database first.

## Reset local database (destructive — dry run first)
```bash
python scripts/reset_final_l5_01.py                 # dry run — prints plan, no changes
python scripts/reset_final_l5_01.py --confirm        # actually truncates 201 tenant-scoped tables
```

## Migrate to head
```bash
alembic upgrade head
alembic current   # verify -> 131 (head)
```

## Run canonical seed
```bash
python scripts/canonical_seed_final_l5_01.py
```
Safe to run multiple times — every insert is existence-checked. Login credentials for all seeded users: see `.backups/final-l5-01/e2e_credentials.local.txt` (gitignored, local only).

## Run seed idempotency test
```bash
python scripts/canonical_seed_final_l5_01.py   # run 1
python scripts/canonical_seed_final_l5_01.py   # run 2 — every line should print [SKIP]
```

## Run data integrity checks
No standalone script was built this sprint — the integrity queries used to produce `FINAL_L5_01_FOREIGN_KEY_ORPHAN_REPORT.md` and `FINAL_L5_01_DUPLICATE_UNIQUE_INTEGRITY_REPORT.md` were run ad hoc via inline Python against `app.database.create_engine()`. Recommend promoting these to a `scripts/verify_final_l5_01_integrity.py` in a future sprint rather than re-deriving them by hand each time — flagged in remaining blockers.

## Run API smoke
```bash
curl -s -X POST http://localhost:8000/v1/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@serviceos.local","password":"Password123!"}'
# extract access_token from response, then:
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/v1/admin/tenants
```
Note: `admin@serviceos.local` uses the legacy fixture password `Password123!`, not the canonical test password — see `FINAL_L5_01_CANONICAL_SEED_SPECIFICATION.md`. All other canonical users use `CanonicalL5!2026`.

## Restore backup
```bash
"db/pgsql/bin/pg_restore.exe" -h 127.0.0.1 -p 5432 -U <user> -d serviceos --clean --if-exists \
  ".backups/final-l5-01/serviceos_pre_reset_20260711-001711.dump"
```

## Troubleshoot partial seed
The canonical seed commits in logical phases (platform users → tenant → tenant users/staff/customers → [commit] → catalog/pricing/offering/coverage/availability → [commit] → billing → [commit] → jobs → [commit] → deduction → [commit] → notifications → [commit]). If a run fails partway, re-running `reset_final_l5_01.py --confirm` then `canonical_seed_final_l5_01.py` from scratch is the supported recovery path — do not attempt to manually patch a partial state, since the existence-check idempotency logic assumes either "nothing exists" or "everything from a completed phase exists," not partial phase completion.

## Safety warnings
- Never point `DATABASE_URL` at anything other than `127.0.0.1`/`serviceos` when running these scripts — the guard will refuse cloud-host markers and non-allowlisted database names, but always double-check the printed `[TARGET]` line before confirming.
- `reset_final_l5_01.py --confirm` is irreversible without the backup — always take a fresh `pg_dump` before running it if the current data has any value.
