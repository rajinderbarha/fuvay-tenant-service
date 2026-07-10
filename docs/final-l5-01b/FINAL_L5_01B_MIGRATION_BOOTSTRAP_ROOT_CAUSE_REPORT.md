# FINAL-L5-01B — Migration Bootstrap Root Cause Report

| Field | Value |
|---|---|
| Database engine/version | PostgreSQL 16.4 (local bundled install) |
| Migration tool | Alembic |
| Failing migration | The first migration in the chain that runs `CREATE EXTENSION IF NOT EXISTS vector` (pgvector, used for AI/RAG embedding columns) |
| Operation requiring elevated privilege | `CREATE EXTENSION` |
| Required extension/schema/role | `vector` extension must be created by a Postgres superuser (or a role with `CREATEDB`+extension-owner privileges, not present here) |
| Current migration user privileges | `serviceos` application user — confirmed via `SELECT usename, usesuper FROM pg_user`: `usesuper = false` (correctly non-superuser) |
| Exact safe error | `asyncpg.exceptions.InsufficientPrivilegeError: permission denied to create extension "vector" — HINT: Must be superuser to create this extension.` |

## Determination
Root cause is definitively **`CREATE EXTENSION`** — not `CREATE SCHEMA`, `ALTER ROLE`, `CREATE DATABASE`, ownership change, a superuser-only function, or a missing bootstrap schema. Confirmed by reproducing the exact failure against a freshly created throwaway database (`serviceos_l501b_replay`) and by inspecting the migration file that issues the `CREATE EXTENSION IF NOT EXISTS vector` statement.

## Second, independent finding (surfaced only once the extension blocker was resolved)
After building and applying the bootstrap solution (see `FINAL_L5_01B_MIGRATION_BOOTSTRAP_SOLUTION.md`), the migration chain proceeded much further against the same fresh database and hit a **second, unrelated failure**: `DuplicateTableError: relation "service_setup_templates" already exists`. Root-caused to two separate migration files both issuing `op.create_table(...)` for a table named `service_setup_templates`:
- `alembic/versions/058_sprint34f_service_setup_templates.py`
- `alembic/versions/097_service_setup_templates_enterprise.py`

This is a genuine, pre-existing migration-authoring defect, unrelated to privileges — it has never surfaced before because the actual long-lived development database was built up incrementally across many prior sprints (never replayed from empty), so this collision was never exercised until this sprint's empty-database replay attempt. Per the mission's non-negotiable rule "Never rewrite applied migrations without a formal corrective migration," this was **not patched in-place** during this sprint — migration 097 (and any environment where it has already run) may already depend on its current exact form, and correcting it safely requires a dedicated migration-authoring review, not a quick fix layered onto a data-seeding sprint. Documented in full in `FINAL_L5_01B_REMAINING_BLOCKERS.md`.
