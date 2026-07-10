# FINAL-L5-00 — File Cleanup Manifest

Consolidated from all Part 3–15 inventory reports (see individual reports in this directory for full detail and grep evidence). This manifest lists only items with a concrete cleanup disposition; routine KEEP items (the vast majority of the repo) are not repeated here.

## Summary counts

| Category | Count | Action taken this sprint |
|---|---|---|
| Stale root-level `*.log` files | 39 | **DELETED** (Part 17, executed) |
| Live/actively-written `*.log` files | 4 | KEEP — dev servers writing to them at scan time |
| Bundled local PostgreSQL/pgAdmin install (`db/pgsql`, `db/pgdata`, zips) | 1 dir tree, ~GBs | GITIGNORED, never committed — no action needed, already outside git |
| Stray junk directory `{app/{core,schemas,...}` | 1 | **DELETED** (empty broken brace-expansion artifact, removed before baseline commit) |
| Root-level `*.md` historical report files | 663 | REVIEW_REQUIRED / ARCHIVE_HISTORICAL — **not moved this sprint** (see below) |
| `check_*.py` / `inspect_route.py` debug scripts | 9 | REVIEW_REQUIRED — **not deleted this sprint** (see below) |
| Unmounted dead router files (`app/engines/brands/admin_router.py`, `provider_router.py`) | 2 | REVIEW_REQUIRED — **not deleted this sprint** (see below) |
| `app/engines/vertical_billing`, `app/engines/form_builder` | 2 dirs | REVIEW_REQUIRED — **not deleted this sprint** |
| `design-system/` package (unused by any frontend) | 1 dir | REVIEW_REQUIRED — **not deleted this sprint** |
| `__pycache__`, `.pytest_cache`, `.next` dirs | 15 dirs | GENERATED_RECREATABLE, gitignored, untracked — left in place (harmless, regenerate automatically) |
| Frontend/mobile/backend dependencies flagged POTENTIALLY_UNUSED | ~5 | REVIEW_REQUIRED — **no uninstalls performed** |

## Why most REVIEW_REQUIRED items were not deleted this sprint

Per the mission's non-negotiable safety rules: **"Only `DELETE_CONFIRMED` and approved `GENERATED_RECREATABLE` files may be removed in this sprint"** and **"Do not delete any file whose usage cannot be proven."** The dead-code, duplicate-code, route, and document agents each explicitly flagged their less-than-certain findings as `REVIEW_REQUIRED` rather than `DELETE_CONFIRMED` — meaning grep evidence was suggestive but not exhaustive (e.g., dynamic imports, string-built router registration, or cross-package references could exist that a sampled grep scan would miss). Deleting source code, migrations, or 663 historical certification reports on a single-pass heuristic scan carries real risk of destroying the "only record of a decision" the mission explicitly warns against.

The two genuinely `DELETE_CONFIRMED` categories this sprint (stale logs, the stray junk directory) share a property the REVIEW_REQUIRED items don't: they are unambiguously non-source, disk-only, zero-reference artifacts with no plausible reader.

## Detailed candidates carried to `FINAL_L5_00_REMAINING_REVIEW_ITEMS.md`

See that file for the full path-by-path list with owner recommendation for a *future, human-reviewed* cleanup pass (FINAL-L5-01 or similar), covering:
- Archiving (not deleting) the 663 root `*.md` reports into `docs/archive/pre-final-l5/`
- Removing the 2 confirmed-dead brand router files after a human confirms no dynamic reference
- Consolidating the two parallel Playwright E2E harnesses
- Deciding the fate of `design-system/` (wire it up or remove it — currently dead weight either way)
- The `check_*.py`/`inspect_route.py` debug script series (5 of 9 flagged superseded by later-numbered versions)

## CSV
See `file-cleanup-manifest.csv` for the machine-readable version of the DELETE_CONFIRMED and REVIEW_REQUIRED rows.
