# FINAL-L5-00 — Cleanup Execution Report

## Deleted files (disk only — none were git-tracked, so no git history impact)
- 39 stale root-level `*.log` files (34MB total). Full list in `file-cleanup-manifest.csv`.
- 1 stray junk directory: `{app/{core,schemas,models,dependencies,engine_registry,engines/{...}},alembic/{versions,tests,scripts}` — empty, leftover from a broken shell brace-expansion command, removed prior to the baseline commit so it never entered git history.

## Archived files
None this sprint. The 663 root-level historical `*.md` reports were classified `ARCHIVE_HISTORICAL` but the actual move to `docs/archive/pre-final-l5/` was **not executed** — see rationale below.

## Moved files
None.

## Gitignore changes
Created `.gitignore` for the first time in this repository (it did not exist before this sprint). Key additions beyond standard node/python ignores:
- `db/pgsql/`, `db/pgdata/`, `db/*.zip`, `db/pgvector_extract/` — excludes the bundled local PostgreSQL 16 + pgAdmin4 install and live database data directory (discovered during Part 2; this is the reason the initial `git add -A` was pathologically slow)
- `.claude/` — local tool config, not project source
- `uploads/` — runtime upload data, not source
- Standard: `node_modules/`, `.next/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `*.log`, `.env*`, `test-results/`, `playwright-report/`

## Space recovered
- 34MB of stale logs removed from disk.
- The `db/pgsql`/`db/pgdata` exclusion prevents an estimated multi-GB bundle from ever entering git history (it was never committed, so no history rewrite was needed — pure avoidance, not recovery).

## Files intentionally retained despite being flagged
- 663 historical `*.md` reports — retained in place rather than archived. **Reason**: moving 663 files is a large, high-diff-noise operation that benefits from a dedicated, human-reviewed sprint (proposed FINAL-L5-01) rather than being folded into this baseline/inventory sprint. Deleting or moving them now, without per-file confirmation that no unique decision record would be lost, would violate the mission's explicit rule against destroying "the only source of a business rule."
- 2 unmounted dead router files (`app/engines/brands/{admin,provider}_router.py`) — retained. Confirmed unmounted and apparently superseded by grep evidence alone; per mission rules this requires manual/human confirmation before deletion, not just static-analysis confidence.
- `app/engines/vertical_billing`, `app/engines/form_builder` — retained, same reasoning.
- `design-system/` package — retained. This is a product/architecture decision (wire it up vs. remove it), not a cleanup decision.
- `check_*.py` / `inspect_route.py` debug scripts (9 files, git-tracked) — retained. Low risk to remove but not exercised by any test or build step to *prove* safety; carried to remaining review items instead of unilaterally deleted.

## Unexpected findings during execution
- 4 `*.log` files at repo root were being actively written to by running dev servers at scan time (`backend_new_run.log`, `customer-app-run.log`, `frontend-tenant.log`, `super-admin-run.log`) — excluded from deletion.
- `db/` contains not just a Postgres binary bundle but also `pgvector.zip`, `pgvector_extract/`, and a `postgresql-16-fresh.zip` — multiple redundant installer copies. Not touched this sprint (already gitignored/untracked, zero risk either way); noted for a future disk-hygiene pass outside of git scope.
- `check_*.py`, `inspect_route.py`, and `setup_pg*.sh` debug/setup scripts were unexpectedly swept into the very first `git add` (before `.gitignore` existed) and are now part of the git-tracked baseline. Not a security issue (no secrets in them) but flagged as an unintended inclusion — see remaining review items.
