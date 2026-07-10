# FINAL-L5-01 — Environment Safety Report

## Facts gathered (read-only, no writes performed)

| Field | Value |
|---|---|
| Application environment (`APP_ENV` in `.env`) | `development` |
| `ALLOW_DATABASE_RESET` | **not set** |
| Database host | `127.0.0.1` (loopback — confirmed via `inet_server_addr()` returning `127.0.0.1/32`) |
| Database port | `5432` |
| Database name | `serviceos` |
| Database user | masked (present in `.env`, not printed here) |
| Local vs remote | **Local** — loopback address, and matches the bundled local PostgreSQL install found under `db/pgsql`/`db/pgdata` during FINAL-L5-00 |
| Contains real customer/tenant data? | **No evidence of production data.** 1 tenant, 11 users, 11 service_jobs, 3 ledger entries, 0 bookings — consistent with a small hand-seeded/dev-accumulated dataset, not a production scale dataset |
| Current migration head | `131 (head)` via `alembic current` |
| Current schema count | 1 (`public`) |
| Current table count | 357 |
| Current tenant count | 1 |
| Current user count | 11 |
| Current service_jobs count | 11 |
| Current ledger count | 3 |
| Backup capability | `pg_dump` availability not yet verified in this shell (no `psql`/`pg_dump` on PATH in the Bash tool's environment — Postgres binaries exist under the bundled `db/pgsql` tree from FINAL-L5-00, need to invoke by full path) |

## Live-system caveat (important)
Four dev servers were found actively running against this exact database during the FINAL-L5-00 sprint (backend on :8000, three frontends on :3000/:3001/:3002, confirmed via actively-updating log files and a live HTTP liveness check). This is very likely the developer's **actual working dev database**, not a disposable throwaway — resetting it will destroy whatever the user has been manually testing with, even though it is unambiguously "local."

## Production guard evaluation

Per this mission's own required guard:
> "The reset process must abort unless an explicit safe environment value is present, for example: `APP_ENV=local`, `APP_ENV=test`, `APP_ENV=e2e`, `ALLOW_DATABASE_RESET=true`"

**Current state does not satisfy this gate as literally specified**: `APP_ENV=development` is not `local`/`test`/`e2e`, and `ALLOW_DATABASE_RESET` is not set at all. The evidence strongly suggests this is a genuinely local, non-production database (loopback host, small row counts, bundled local Postgres install), but the mission's explicit, mechanical guard is not satisfied by the current `.env` as-is.

## Guard checklist

| Protection | Status |
|---|---|
| Reject production | N/A — no evidence this is production; host is loopback |
| Reject staging unless dedicated E2E | N/A — no staging indicator found |
| Reject unknown environment | **Borderline** — `development` is a known, named environment, not "unknown," but is not on the mission's explicit allowlist |
| Reject non-allowlisted database name | `serviceos` — not yet explicitly allowlisted anywhere in code; will be added to the reset script's allowlist |
| Reject missing reset confirmation | **FAILS today** — `ALLOW_DATABASE_RESET` is unset |
| Print target host/database before acting | Will be implemented in the reset script (Part 5) |
| Require second explicit confirmation variable | Will be implemented in the reset script (Part 5) |

## Decision

Given (a) strong evidence this is a local, non-production database, but (b) the mission's own mechanical safe-env gate is not currently satisfied, and (c) the database is actively in use by running dev servers right now — **this sprint pauses here and requests explicit user confirmation before any destructive action**, rather than loosening the gate unilaterally. See the question posed to the user alongside this report.

This is not a failure of the environment-safety check in the sense of "this looks like production" — it is a deliberate stop because the destructive parts of this mission (reset/seed) should not proceed on implicit assumptions when a live, actively-used database is on the other end of the connection.
