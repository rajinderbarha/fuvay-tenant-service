# FINAL-L5-00 — Generated Artifact Report (Parts 10-11)

Scope: read-only investigation of generated/ephemeral artifacts at repo root and in build
directories. No files were deleted, moved, or edited to produce this report.

## Loose *.log files at repo root

Found **40 files** (mission brief estimated ~20; actual count is double). All are stale
backend/frontend/server debug logs from dev sessions on various dates (Jul 2 – Jul 10), sizes
ranging from 0 bytes (`uvicorn_out.log`) to ~10 MB (`backend_live_err.log`).

| File | Size | Last modified |
|---|---:|---|
| backend.log | 2.25 MB | Jul 10 19:14 |
| backend_8000_final.log | 89 KB | Jul 7 16:16 |
| backend_8000_final2.log | 1.99 MB | Jul 7 16:29 |
| backend_8000_final3.log | 2.04 MB | Jul 7 16:54 |
| backend_8001.log | 329 KB | Jul 7 12:08 |
| backend_8001_v2.log | 91.6 KB | Jul 7 12:09 |
| backend_8001_v3.log | 80 KB | Jul 7 12:13 |
| backend_8001_v4.log | 1.7 KB | Jul 7 12:13 |
| backend_8001_v5.log | 599 KB | Jul 7 12:15 |
| backend_8001_v6.log | 7.3 KB | Jul 7 12:16 |
| backend_dashboard.log | 2.4 MB | Jul 7 21:50 |
| backend_dashboard2.log | 4.49 MB | Jul 7 22:15 |
| backend_err.log | 705 B | Jul 4 15:20 |
| backend_live.log | 2.0 MB | Jul 4 18:49 |
| backend_live_err.log | 10.06 MB | Jul 3 22:33 |
| backend_marketing.log | 422 KB | Jul 7 16:56 |
| backend_new.log | 8.2 KB | Jul 2 10:49 |
| backend_new_err.log | 2.7 KB | Jul 2 10:49 |
| backend_stderr.log | 40.3 KB | Jul 9 09:59 |
| backend_stderr_8001.log | 199 B | Jul 7 11:22 |
| backend_stdout.log | 730 KB | Jul 9 10:34 |
| backend_stdout_8001.log | 2.4 KB | Jul 7 11:37 |
| backend_v2.log | 1.3 KB | Jul 2 10:51 |
| backend_v2_err.log | 392 B | Jul 2 10:51 |
| frontend-admin.log | 247 KB | Jul 10 21:05 |
| frontend-customer.log | 419 B | Jul 10 18:52 |
| frontend-tenant.log | 330 KB | Jul 10 21:09 |
| frontend_sa.log | 4.3 KB | Jul 4 15:12 |
| frontend_tp.log | 1.1 KB | Jul 4 13:45 |
| server.log | 177 KB | Jul 4 19:14 |
| server_new.log | 2.73 MB | Jul 6 16:08 |
| server_out.log | 71.8 KB | Jul 4 19:04 |
| start_err.log | 392 B | Jul 4 19:02 |
| super-admin.log | 71.8 KB | Jul 2 09:11 |
| super_admin_dev.log | 272 KB | Jul 9 18:25 |
| tenant-portal.log | 477 KB | Jul 2 09:17 |
| tenant_portal_dev.log | 54.2 KB | Jul 9 18:41 |
| uvicorn.log | 178 B | Jul 2 10:28 |
| uvicorn_out.log | 0 B | Jul 4 18:55 |
| uvicorn_start.log | 20 B | Jul 4 18:55 |

**Total: ~35 MB across 40 files.**

**Classification: DELETE_CONFIRMED** for all 40. Rationale:
- `.gitignore` line 24 is a bare `*.log` rule, confirmed to cover every one of these filenames.
- `git ls-files | grep '\.log$'` returned **zero** results — none of these logs were ever
  committed to git. They exist only on local disk.
- Content is stdout/stderr capture from ad-hoc local dev server runs (uvicorn/next dev), not
  build artifacts referenced by any script, test, or CI config (`grep`-checked: no references to
  these specific filenames found in `package.json`, `pytest.ini`, or CI workflow files).
- Deleting them from disk is low-risk: they are not tracked, not referenced, and pure debug
  exhaust from a running local session — the newest (`backend.log`, `frontend-admin.log`,
  `frontend-tenant.log`, all Jul 10) may belong to a *currently running* dev server for today's
  session, so if any process is still writing to them, deletion should happen after stopping
  those processes (not investigated here — read-only mission scope).

## Playwright test-results / playwright-report directories

`test-results` directories found (via `find . -maxdepth 3 -type d -name test-results`):
- `frontend/customer-app/test-results`
- `frontend/e2e-admin-tenant/test-results`
- `frontend/super-admin/test-results`

No `playwright-report` directory found anywhere under maxdepth 3.

**Classification: GENERATED_RECREATABLE.** `.gitignore` line 27 already excludes `test-results/`
project-wide, and `git ls-files` confirms none are tracked. These are regenerated automatically
on every Playwright run; safe to delete but not urgent (already invisible to git).

## .next build directories

Found: `frontend/customer-app/.next`, `frontend/super-admin/.next`, `frontend/tenant-portal/.next`.
Covered by `.gitignore` line 12 (`.next/`). **Classification: GENERATED_RECREATABLE** — standard
Next.js build cache, safe to delete, regenerates on next `npm run dev`/`build`.

## __pycache__ directories

Found 12 under `app/` and `alembic/` (e.g. `app/core/__pycache__`, `app/models/__pycache__`,
`tests/__pycache__`, `alembic/__pycache__`, `alembic/versions/__pycache__`, etc). Covered by
`.gitignore` line 3 (`__pycache__/`). **Classification: GENERATED_RECREATABLE** — standard
Python bytecode cache, safe to delete, regenerates automatically on next import/run.

## coverage/ directories

None found under the searched depth (`.gitignore` line 15 pre-emptively excludes `coverage/` but
no such directory currently exists on disk). No action needed.

## Loose debug scripts at repo root: check_*.py, inspect_route.py, setup_pg*.sh

| File | Purpose (inferred from content) |
|---|---|
| `check_all_routes.py`, `check_all_routes2.py` | Ad-hoc route-listing scripts (import `app.main`, iterate `app.routes`, print paths matching a keyword — e.g. "customer") |
| `check_router.py`, `check_router2.py`, `check_router3.py` | Ad-hoc single-router inspection scripts, iterative debug variants |
| `check_routes.py`, `check_routes2.py`, `check_routes3.py` | Same pattern as `check_all_routes*`, likely earlier drafts |
| `inspect_route.py` | Ad-hoc single-route inspection script |
| `setup_pg.sh`, `setup_pg_root.sh`, `setup_pg_wsl.sh` | Ad-hoc local Postgres setup scripts (root vs WSL variants), not part of the formal `alembic` migration tooling |

**Finding: these 11 files (8 `check_*`/`inspect_route.py` + 3 `setup_pg*.sh`) ARE git-tracked** —
confirmed via `git ls-files`, and all first appear in the repo's `36efe8d chore(final-l5-00):
initial baseline commit before Level-5 cleanup` commit. This means they were accidentally (or at
least without curation) swept into the baseline commit alongside real source, unlike the `*.log`
files which correctly stayed untracked throughout.

**Classification: REVIEW_REQUIRED** (not DELETE_CONFIRMED). Reasoning: their content (print-route
debug snippets, one-off Postgres bootstrap scripts) strongly suggests disposable, superseded-many-
times-over ad-hoc tooling — the numbered suffixes (`_2`, `_3`, `v2`...) are themselves a signal of
"kept every iteration instead of overwriting." However:
- They ARE committed to git, so removing them is a content change to tracked history, not a
  disk-only cleanup — outside this mission's read-only/report-file-only scope and outside the
  "DO NOT delete/move/edit any file except report files" instruction given for this task.
- A human or a future cleanup mission should decide whether to consolidate to one canonical
  `scripts/check_routes.py` + `scripts/setup_pg.sh` and remove the redundant numbered variants,
  or keep them as-is as informal dev utilities.
- Flagging here as a **non-urgent but real finding**: these should not have been part of a
  "baseline commit" if the intent was a clean starting point; future baselining should exclude
  loose root-level debug scripts via `.gitignore` or by moving them to a `scripts/debug/` folder
  (itself gitignored) before committing.

## Summary

- **40 loose `*.log` files** at root (~35 MB) — all untracked, all `.gitignore`-covered,
  classified DELETE_CONFIRMED, safe to remove from disk (verify no dev server is actively writing
  to the Jul-10-dated ones first).
- **3 `test-results/` dirs + 3 `.next/` dirs + 12 `__pycache__/` dirs** — all untracked,
  `.gitignore`-covered, classified GENERATED_RECREATABLE.
- **0 `coverage/` or `playwright-report/` directories** currently present.
- **11 loose debug scripts** (`check_*.py` x8, `inspect_route.py`, `setup_pg*.sh` x3) — classified
  REVIEW_REQUIRED; flagged as an important non-urgent finding that they were committed into the
  `36efe8d` baseline commit despite being ad-hoc/disposable in nature, unlike the logs which were
  correctly kept out of git throughout.
