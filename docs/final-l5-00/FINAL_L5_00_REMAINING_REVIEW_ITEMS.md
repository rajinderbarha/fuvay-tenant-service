# FINAL-L5-00 — Remaining Review Items

Everything below requires human judgment before action — none of it was deleted or modified this sprint. Full evidence is in the linked reports.

## High-value, low-risk (recommend a dedicated FINAL-L5-01 pass)
1. **Archive the 663 root-level `*.md` historical reports** into `docs/archive/pre-final-l5/`. Classified `ARCHIVE_HISTORICAL` — see `FINAL_L5_00_DOCUMENT_CLEANUP_MANIFEST.md`. Keep `README.md`, `REMAINING_BLOCKERS.md`, `TEST_RESULTS.md` at root (KEEP_CURRENT).
2. **Remove 2 confirmed-unmounted dead backend routers**: `app/engines/brands/admin_router.py` and `provider_router.py`, superseded by `app/engines/admin_catalog/brand_router.py`/`brand_provider_router.py`. See `FINAL_L5_00_BACKEND_ENDPOINT_INVENTORY.md`. Recommend a human diff/grep double-check plus a quick manual test of `/v1/admin/brands` before deletion.
3. **Consolidate the two parallel Playwright E2E harnesses** (`e2e/` vs `frontend/e2e-admin-tenant/`) — both cover super-admin + tenant-portal with overlapping numbered suites (`e2e02`-`e2e11`). See `FINAL_L5_00_REPOSITORY_INVENTORY.md` and `FINAL_L5_00_TEST_INVENTORY.md`.
4. **`check_all_routes.py`/`check_router.py`/`check_routes.py` (and their v2/v3 successors) plus `inspect_route.py`** — 9 ad-hoc debug scripts, git-tracked, 5 flagged as superseded by later-numbered versions. See `FINAL_L5_00_DEAD_CODE_REPORT.md`.

## Architecture decisions (not cleanup — needs product/eng call)
5. **`design-system/` package is fully built (68+ components) but imported by none of the 3 frontends** — each frontend independently reimplements its own `~650`-line `components/shared/ui.tsx`. Decide: wire frontends up to the shared package, or delete the unused package. See `FINAL_L5_00_DUPLICATE_CODE_REPORT.md`.
6. **`app/engines/vertical_billing` and `app/engines/form_builder`** show zero import references in a sampled grep scan — confirm dead or find the missing reference before removal. See `FINAL_L5_00_DEAD_CODE_REPORT.md`.
7. **79 routes classified `DISCONNECTED_NO_MENU`** — pages exist and presumably work but have no sidebar entry (mostly Super Admin finance/marketing/analytics sub-pages, Tenant Portal service-setup pages). Decide per-route: add to nav, or intentionally keep hidden/contextual. See `FINAL_L5_00_ROUTE_PAGE_INVENTORY.md`.
8. **37 `DUPLICATE_ROUTE` entries across ~15 feature clusters** (biggest: Tenant Portal's 5-page service-setup/offerings cluster; Super Admin's pricing-rules/checklist-templates/workflow-templates/notification-templates/wallets/profile duplicates). See `FINAL_L5_00_ROUTE_PAGE_INVENTORY.md`.

## Security/hygiene, low urgency
9. **Dormant `MOCK_MODE` login bypass** in tenant-portal (`lib/api.ts:1451` + `app/login/page.tsx`) — fabricates a fake session if `NEXT_PUBLIC_USE_MOCK=true` is ever set. Currently `false` in both `.env.local` files (inert) but shipped in the bundle. Recommend removing the code path entirely rather than relying on an env flag to keep it off in production builds. See `FINAL_L5_00_RUNTIME_MOCK_PLACEHOLDER_REPORT.md`.
10. **4 `DIRECT_BYPASS` findings** — super-admin commission-records/payments/refund-requests pages and a tenant-portal login runtime fetch call the API directly instead of through the central client, even though central-client methods already exist for these resources. See `FINAL_L5_00_DIRECT_API_BYPASS_REPORT.md`.
11. **9 git-tracked debug/setup scripts** (`check_*.py`, `inspect_route.py`, `setup_pg*.sh`) were swept into the very first `git add` before `.gitignore` existed — not a security issue, just an unintended inclusion worth a deliberate keep/remove decision rather than accidental permanence.
12. **`db/` directory contains 3 redundant Postgres/pgvector installer copies** (`pgvector.zip`, `pgvector_extract/`, `postgresql-16-fresh.zip`) alongside the live `pgsql`/`pgdata` bundle — already excluded from git, zero risk, but worth a disk-hygiene pass outside of git scope.

## Verification gaps (documented, not silently skipped)
13. Full `pytest` (not just `--collect-only`), `npm run build`/`npm test` for all 3 web frontends, mobile Expo type-check/tests, and a full Playwright browser-driven smoke pass (login → dashboard for all 4 apps) were **not executed** this sprint — see `FINAL_L5_00_BASELINE_TEST_BUILD_REPORT.md` and `FINAL_L5_00_POST_CLEANUP_BROWSER_SMOKE_REPORT.md` for what was and wasn't run and why.
14. Rotate/revoke the GitHub Personal Access Token and Gmail password the user pasted into this chat session — see `FINAL_L5_00_SECRET_SCAN_REPORT.md`.

## No action needed (explicitly confirmed safe)
- No secrets found committed to git.
- No broken menu links anywhere across all 4 frontend apps (0 `MISSING_PAGE`/`BROKEN_ROUTE` classifications).
- No unmounted backend router other than the 2 confirmed-dead brand ones (4 others are deliberately, explicitly disabled via a code comment for non-active verticals).
- Migration chain is a single clean line, no branches, no dangling heads.
- Only 1 `DANGEROUS_RESET` script exists (`scripts/serviceos_reset_dev_data.py`) and it was not executed this sprint.
