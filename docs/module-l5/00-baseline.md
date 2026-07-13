# MODULE-L5-00 — Repository Baseline

| Item | Value |
|---|---|
| Repository root | `g:\serviceos` |
| Branch | `master` |
| HEAD (start) | `37b8911` |
| `origin/master` (start) | `37b8911` (identical) |
| Ahead/behind | `0 / 0` |
| Working tree (start) | 49 entries changed/untracked — all attributable to the concurrent, unrelated `mobile/customer-app` session (see below); zero unexplained drift |
| Migration head | `136` |
| Migration current | `136` (matches head) |
| Backend health | `ok` (PostgreSQL `ok`, Redis `ok`) |
| Frontend apps present | `frontend/super-admin`, `frontend/tenant-portal`, `frontend/customer-app`, `frontend/e2e-admin-tenant` (test harness, not a product app), `mobile/customer-app`, `mobile/staff-app` |
| Playwright | proven available and working throughout the FINAL-L5-05 program (see reconciliation doc) |
| Test command (backend) | `python -m pytest tests/` |
| Test command (frontend, super-admin/tenant-portal) | no jest suite exists; Playwright + isolated TypeScript + `next build` is this program's established verification stack |
| Backend baseline (this sprint) | last confirmed clean run (FINAL-L5-05AM): 9310 passed, 1 skipped, 1 failed (unrelated concurrent mobile-app Expo SDK drift) — not re-run in full this sprint since MODULE-L5-00 is a discovery/documentation gate, not a runtime-certification gate (Non-Negotiable Rule 53/54: small bounded tooling fixes only) |

## Real repository-wide counts (source-derived, not estimated)

| Metric | Count | Method |
|---|---|---|
| Backend engine directories (`app/engines/*`) | 71 directories on disk; 68 scanned as real modules (3 excluded: `__pycache__`, and 2 non-directory/utility entries) | `ls app/engines/` |
| Alembic migrations | 129 | `ls alembic/versions/*.py` |
| Distinct database tables (`__tablename__`) | 351, across 118 model files | `grep -rho "__tablename__ = ..."` |
| Files declaring `APIRouter(` | 144 | `grep -rl "APIRouter("` |
| `@router.{get,post,put,patch,delete}(` decorators | 1,788 | `grep -rhoE` |
| Super Admin frontend routes (`page.tsx`) | 163 | `find frontend/super-admin/app -name page.tsx` |
| Tenant Portal frontend routes (`page.tsx`) | 104 | `find frontend/tenant-portal/app -name page.tsx` |
| Customer web app routes (`page.tsx`) | 8 | `find frontend/customer-app -name page.tsx` |
| Mobile customer-app screens | 53 | `find mobile/customer-app/src -iname "*screen*.tsx"` |
| Mobile staff-app screens | 8 | `find mobile/staff-app -iname "*screen*.tsx"` |
| Permission constants (`app/core/permissions.py`) | 280 | `grep -c` |
| Canonical roles | **10**: `super_admin`, `tenant_owner`, `staff`, `technician`, `customer`, `guest`, `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly` | `grep -oE '"[a-z_]+":\s*\['` in `permissions.py` |
| Files referencing scheduler/cron/celery patterns | 23 | `grep -rl` |
| `docs/final-l5-05/*.md` (this engagement's own cert program) | 46 | `ls` |

**Important correction to this mission's own framing**: the FINAL-L5-05 program (FINAL-L5-05 through 05AM) scoped its "5 canonical roles" narrative to the 5 `admin_*` roles only. The platform's real, full role set is **10 roles** — `tenant_owner`, `staff`, `technician`, `customer`, and `guest` were never in scope for that program's five-role matrices. This is a genuine, material finding for this inventory: any future platform-wide Level 5 claim must cover all 10 roles, not 5.

## Additional pre-existing certification programs discovered (not previously reconciled by the FINAL-L5-05 chain)

Beyond `docs/final-l5-05/`, the repository contains substantial prior certification work never referenced by any FINAL-L5-05 sprint:

- `docs/final-l5-00/`, `final-l5-01/`, `final-l5-01b/`, `final-l5-01b-plus/`, `final-l5-01d/`, `final-l5-01e/`, `final-l5-02/`, `final-l5-02b/`, `final-l5-03/`, `final-l5-04/`, `final-l5-04b/` — an earlier, apparently more granular FINAL-L5-01..04 sub-program that predates or parallels the summarized `FINAL-L5-01` through `FINAL-L5-04` results this engagement inherited as pre-verified facts.
- A large `PHASE_6B_TENANT_*` and `TENANT_*` document set (23 files) — an apparently separate Tenant Portal certification effort (API mapping reports, UI quality reports, remaining-blockers docs) not previously reconciled against the FINAL-L5-05 Super-Admin-focused chain.
- `FINAL_EXECUTIVE_SUMMARY.md`, `FINAL_LEVEL_5_PROOF_REPORT.md`, `FINAL_RELEASE_DECISION.md`, `FINAL_SECURITY_PROOF_REPORT.md`, `FINAL_TENANT_ISOLATION_REPORT.md`, `FINAL_PERFORMANCE_REPORT.md`, `FINAL_DEPLOYMENT_REPORT.md`, `FINAL_API_COVERAGE_REPORT.md`, `FINAL_E2E_SMOKE_REPORT.md`, `FINAL_KNOWN_ISSUES_REGISTER.md`, `RELEASE_CANDIDATE_SUMMARY.md`, `RELEASE_NOTES_rc1.md` — apparent artifacts of an earlier full "release candidate" declaration, whose relationship to the current, still-open FINAL-L5-05 chain (which has run 13 sub-sprints past that point, AE through AM, all still `PARTIAL_READY`) is unclear and requires explicit reconciliation before being trusted.
- `docs/customer-app/` — a **currently active, concurrent** `CUSTOMER-L5-*` certification program (baseline, auth architecture, contract matrix, failure matrix, known-gaps docs), being run by a different, concurrent session against `mobile/customer-app`. This program is out of this session's scope to touch, but its existence and scope must be recorded so this inventory does not duplicate or contradict it.

See `01-previous-sprint-reconciliation.md` for classification of all of the above.
