# FINAL-L5-01B — Safe Migration Bootstrap Solution

## Pattern selected: Option A — Explicit bootstrap script

`scripts/bootstrap_database_final_l5_01b.py`. A one-time, explicitly-invoked script connects with a **separate** superuser credential (never the app's normal `DATABASE_URL`) to run `CREATE EXTENSION IF NOT EXISTS vector`, then exits. All subsequent migration and runtime work uses the normal, non-superuser `serviceos` application user.

## Requirements checklist

| Requirement | Status |
|---|---|
| Normal app runtime user remains non-superuser | **Confirmed** — `serviceos` user is untouched, still `usesuper=false`; the bootstrap script never modifies its privileges |
| Migration role has only required privileges | Migrations continue to run as `serviceos`, same as before — no privilege escalation introduced |
| Exact bootstrap command documented | `BOOTSTRAP_SUPERUSER_DATABASE_URL="postgresql+asyncpg://postgres:<pw>@127.0.0.1:5432/<dbname>" python scripts/bootstrap_database_final_l5_01b.py` — see runbook |
| Bootstrap is idempotent | Yes — `CREATE EXTENSION IF NOT EXISTS` |
| Running bootstrap twice is safe | Yes, by construction |
| Empty database → bootstrap → migrate head succeeds | **Partially proven** — bootstrap resolved the extension privilege blocker completely (confirmed via real reproduction against a fresh database); the migration chain then proceeded significantly further before hitting the separate, pre-existing `service_setup_templates` duplicate-table bug (see root cause report) — that second bug is NOT part of the bootstrap problem and is not fixed by this solution, nor should it be papered over by it |
| Existing database migrations still succeed | Not affected — the real `serviceos` database already has the `vector` extension (created previously by a superuser during initial setup) and does not re-run `CREATE EXTENSION`, so this change has zero impact on it |
| CI/E2E can run it automatically | Yes — the script takes its superuser connection from an environment variable, making it drop-in for a CI step that provisions a fresh test database (e.g. `docker-compose` init script pattern, or a CI job step before `alembic upgrade head`) |
| Production deployment process documented | See runbook — production databases should have the extension bootstrapped once by infra/DBA tooling as part of initial provisioning, using this same script or an equivalent one-line `CREATE EXTENSION` run by whoever provisions the production database (typically outside the app's own deploy pipeline, consistent with least-privilege practice) |
| Secrets not embedded in scripts | Confirmed — `BOOTSTRAP_SUPERUSER_DATABASE_URL` is read from the environment only, never hardcoded or logged (the script masks credentials in its own `[TARGET]` print line) |

## Why not Option B or Option C
- **Option B (infrastructure-managed)**: `docker-compose.yml`'s Postgres service could be configured to auto-create the extension via a Postgres `docker-entrypoint-initdb.d` init script, which is arguably cleaner for a container-based deployment. Not implemented this sprint since the current dev environment uses a bundled local Postgres install (not the Docker Compose path) — the explicit script (Option A) works for both this environment and CI/Docker equally, whereas an init-script-only solution wouldn't help this sprint's actual local bootstrap need. Documented as a valid alternative for the Docker path in the runbook.
- **Option C (migration-safe redesign)**: Would mean removing the `vector` extension dependency or replacing it with a non-superuser-installable alternative. Out of scope — pgvector is a legitimate, intentional dependency for AI/RAG features; redesigning around it is a product/architecture decision, not a bootstrap-mechanics fix.

## Failure status
Not applicable to the bootstrap mechanism itself (proven working). The separate `service_setup_templates` migration bug is tracked as a distinct, real blocker — see remaining blockers. Given this second issue, full "empty database → migrate head succeeds with zero manual intervention" is **not yet achieved end-to-end**, honestly reported rather than hidden.
