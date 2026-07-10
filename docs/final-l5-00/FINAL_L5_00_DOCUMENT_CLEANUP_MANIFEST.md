# FINAL-L5-00 — Document Cleanup Manifest (Parts 10-11)

Scope: read-only classification of the 663 root-level `*.md` files, plus `README.md` /
`REMAINING_BLOCKERS.md` / `TEST_RESULTS.md`, plus `docs/` (46 loose reports + `architecture.md`
+ `DEPLOY.md`/`RELEASE_*`/`FINAL_*` + `docs/archive/` which already contains `obsolete/`).

No files were deleted, moved, or edited to produce this manifest.

## Method

Grouped root `*.md` files by naming-prefix "series" (the sprint/phase/certification code that
starts each filename), inferred purpose from filename + spot-read of 2-3 files per group's first
~30 lines, and checked mtimes for the three ambiguous "living doc" candidates. Full counts derived
from `ls *.md | wc -l` = 663 total root markdown files (higher than the ~400 estimate in the
mission brief — the actual repo has accumulated more series than expected).

## Root-level *.md — grouped classification

All groups below are historical, point-in-time test/certification reports produced by past
Claude Code sessions documenting one sprint/phase's verification work (API mapping, permission
checks, forbidden-label scans, test results, remaining blockers, browser evidence, etc). They are
narrative snapshots, not living documentation — content is superseded by the current codebase and
by whichever later sprint's report addressed the same area next. None are referenced by the app,
CI, or docs at build/runtime (spot check: no cross-references found from code to these filenames).

| Series (prefix) | Approx count | Purpose (inferred) | Current relevance | Classification |
|---|---:|---|---|---|
| `ADMIN_TENANT_E2E_01_*` | 198 | Admin+Tenant E2E certification sprint: login/browser/route-smoke/permission/forbidden-label/data-accuracy reports for admin & tenant portals | Historical snapshot of one certification pass; portals have moved on since (many later ADMIN_A2/A3/A11, HS, PHASE_6B docs supersede specific sub-areas) | ARCHIVE_HISTORICAL |
| `HS0`–`HS10` + `B`-suffix variants (`HS0_*` … `HS10_*`, `HS2B_*`…`HS9B_*`) | 178 | "Home Services" vertical build-out, phase-by-phase (catalog → pricing → matching → booking → job execution → finance/credit ledger), each phase producing API-mapping/permission/forbidden-label/test-results/remaining-blockers reports | Historical phase certification trail for a specific vertical rollout; superseded by current Home Services code + later Sprint 34+ /P0 rewrites noted in memory index | ARCHIVE_HISTORICAL |
| `CUSTOMER_FRONTEND_01_*` | 16 | Customer-app frontend connectivity sprint 1 (auth/booking/tracking/review/UI reports) | Historical; customer frontend since iterated further per memory index | ARCHIVE_HISTORICAL |
| `CUSTOMER_FRONTEND_02_*` | 15 | Customer-app frontend connectivity sprint 2 | Historical, same as above | ARCHIVE_HISTORICAL |
| `FRONTEND_CONNECT_01_*` | 15 | Cross-app "connect real backend" verification sprint (admin/tenant/shared, mock-vs-live checks) | Historical point-in-time connectivity audit | ARCHIVE_HISTORICAL |
| `CUSTOMER_FRONTEND_02B_*` | 13 | Follow-up/hardening pass on Customer Frontend 02 (safety, seed data, mock removal) | Historical | ARCHIVE_HISTORICAL |
| `PHASE_7_STAFF_*` / `PHASE_7B_STAFF_*` | 17 | Staff security phase 7/7B certification reports | Historical; Sprint 20/Phase0E staff/security work superseded per memory index | ARCHIVE_HISTORICAL |
| `PHASE_6_TENANT_*` | 9 | Tenant-side phase 6 certification | Historical | ARCHIVE_HISTORICAL |
| `PHASE_5_TENANT_*` | 9 | Tenant-side phase 5 certification | Historical | ARCHIVE_HISTORICAL |
| `PHASE_1_ADMIN_*` / `PHASE_1B_*` | ~19 | Admin phase 1/1B certification (roles, permissions, login events, 500-request debugging) | Historical | ARCHIVE_HISTORICAL |
| `PHASE_4_FINANCE_*` | 9 | Finance module phase 4 certification | Historical; superseded by Sprint 23/33 finance work | ARCHIVE_HISTORICAL |
| `PHASE_3_PRICING_*` / `PHASE_3B_*` / `PHASE_3C_*` / `PHASE_3D_*` | ~42 | Pricing module phases 3/3B/3C/3D certification (backend, frontend, bargain module, closure) | Historical; superseded by Sprint 8 pricing catalog + later P0 pricing fixes | ARCHIVE_HISTORICAL |
| `TYPE_DEPENDENT_BRAND_*` / `TENANT_TYPE_BRAND_*` / `TENANT_TYPE_SPECIFIC_*` | ~14 | Type/brand-dependent pricing & catalog reports | Historical; superseded by Sprint 76 Types & Brands module | ARCHIVE_HISTORICAL |
| `TENANT_MY_OFFERINGS_*` / `TENANT_MY_STATUS_*` | 13 | Tenant offering-enablement & bookable-status reports | Historical; superseded by Sprint 11/12 | ARCHIVE_HISTORICAL |
| `TENANT_HOME_SERVICES_*` | 6 | Tenant Home Services setup reports | Historical | ARCHIVE_HISTORICAL |
| `AUTO_PRICE_OPTIONS_*` | 6 | Auto price option computation reports | Historical | ARCHIVE_HISTORICAL |
| `ADMIN_HOME_SERVICES_*` | 6 | Admin Home Services catalog reports (mostly duplicated in `docs/`, see below) | Historical; also present under different names in `docs/final-l5-00`'s sibling `docs/` root | ARCHIVE_HISTORICAL |
| `TENANT_SERVICE_SETUP_*` / `TENANT_SERVICE_COVERAGE_*` / `TENANT_BUSINESS_PROFILE_*` | 15 | Tenant setup/coverage/profile reports | Historical | ARCHIVE_HISTORICAL |
| `ADMIN_A2_DASHBOARD_*` | 5 | Admin dashboard (A2) API/permission/data-accuracy reports | Historical; memory index shows this sprint is "complete" | ARCHIVE_HISTORICAL |
| `ADMIN_A3_*` | 10 | Admin A3 (finance/tenant mgmt/provider 360) certification | Historical, complete per memory index | ARCHIVE_HISTORICAL |
| `ADMIN_A11_*` | 3 | Admin A11 full E2E certification | Historical | ARCHIVE_HISTORICAL |
| `HOME_SERVICES_MENU_ORGANIZATION*` / `HOME_SERVICES_PRICE_RANGE*` | 4 | Home Services nav/pricing menu reports | Historical | ARCHIVE_HISTORICAL |
| `CUSTOMER_PRICE_EXPERIENCE_*` | 4 | Customer price-experience calculation/API/test reports | Historical | ARCHIVE_HISTORICAL |
| `CROSS_APP_FRONTEND_*` | 3 | Cross-app frontend audit/fix/live-verification | Historical | ARCHIVE_HISTORICAL |
| `PHASE_3_FINAL_CERTIFICATION` | 1 | Final cert for phase 3 pricing | Historical | ARCHIVE_HISTORICAL |
| `PROVIDER_MATCHING_*` | 3 | Provider matching engine test/blockers/enterprise report | Historical | ARCHIVE_HISTORICAL |
| `PHASE_0_*` | 6 | Phase 0 baseline (backend/frontend baseline, idempotency, manual smoke, blockers, test results) | Historical bootstrap-era reports | ARCHIVE_HISTORICAL |
| `MANUAL_BARGAIN_*` | 2 | Bargain module deactivation reports | Historical; a copy of the related `PHASE_3C_BARGAIN_FRONTEND_REPORT.md` already lives in `docs/archive/obsolete/` — see Duplicate note below | ARCHIVE_HISTORICAL |
| `JOB_COMPLETION_*` | 3 | Job completion flow audit/bugfix/live-smoke | Historical | ARCHIVE_HISTORICAL |
| `DATA_RESET_SAFETY_CHECK` / `DATA_CLEANUP_AUDIT` | 2 | One-off data-safety audit notes | Historical, narrowly scoped one-off checks | ARCHIVE_HISTORICAL |
| `BASELINE_SEED_REPORT` | 1 | Seed-data baseline report | Historical | ARCHIVE_HISTORICAL |
| `ADMIN_TYPESCRIPT_ERROR_AUDIT` | 1 | One-off TS error audit | Historical, point-in-time; current "0 TS errors" state is tracked in memory index instead | ARCHIVE_HISTORICAL |

**Total root historical report files identified for archival: ~658** (663 total minus the 3 living
docs below, less any of the above overlapping — counts are approximate per the mission's own
"approx count" instruction; exact figures can be regenerated via `ls *.md | wc -l` at archive time).

## Root-level living/state docs (verify by recency)

| File | mtime | Classification | Reasoning |
|---|---|---|---|
| `README.md` | Jun 26 12:16 | KEEP_CURRENT | Standard project entry point; not part of any report series; oldest mtime of the three but that is expected for a README (edited only when project shape changes, not every sprint) |
| `REMAINING_BLOCKERS.md` | Jul 7 12:38 | KEEP_CURRENT | Explicitly framed as superseding prior sprints' blocker notes ("This supersedes the previous sprint's note..."); most recently meaningful cross-cutting blockers doc; most recent mtime among report-style docs at root |
| `TEST_RESULTS.md` | Jul 7 11:29 | KEEP_CURRENT | Root-level rollup of latest test results (distinct from the hundreds of `*_TEST_RESULTS.md` per-sprint reports); recent mtime |

Note: both `REMAINING_BLOCKERS.md` and `TEST_RESULTS.md` are themselves sprint-scoped snapshots
by content (they describe one specific sprint's findings, e.g. "Job Completion Sprint — Test
Results"), not continuously-maintained living documents. They are marked KEEP_CURRENT here because
they are the *most recent* root-level instance of their type and a later session may still be
relying on them as the latest status pointer; downgrade to ARCHIVE_HISTORICAL is reasonable once a
newer status doc supersedes them.

## `docs/` directory (non-archive contents)

46 loose report files plus `architecture.md`, `DEPLOY.md`, `RELEASE_NOTES_rc1.md`,
`RELEASE_CANDIDATE_SUMMARY.md`, and 8 `FINAL_*` release-certification docs, plus subdirs
`docs/archive/` (contains `obsolete/`) and `docs/final-l5-00/` (this manifest's own location).

| Group | Count | Classification | Reasoning |
|---|---:|---|---|
| `architecture.md` | 1 | KEEP_REFERENCE | Standing architecture reference doc, not a sprint report |
| `DEPLOY.md` | 1 | KEEP_REFERENCE | Standing deployment instructions |
| `RELEASE_NOTES_rc1.md`, `RELEASE_CANDIDATE_SUMMARY.md` | 2 | KEEP_REFERENCE | rc-1 release record; still the most recent named release per memory index (Sprint 35 "READY_FOR_DEPLOYMENT") |
| `FINAL_API_COVERAGE_REPORT.md`, `FINAL_DEPLOYMENT_REPORT.md`, `FINAL_E2E_SMOKE_REPORT.md`, `FINAL_EXECUTIVE_SUMMARY.md`, `FINAL_KNOWN_ISSUES_REGISTER.md`, `FINAL_LEVEL_5_PROOF_REPORT.md`, `FINAL_PERFORMANCE_REPORT.md`, `FINAL_RELEASE_DECISION.md`, `FINAL_SECURITY_PROOF_REPORT.md`, `FINAL_TENANT_ISOLATION_REPORT.md` | 10 | KEEP_REFERENCE | Sprint 36 "Level 5 Proof Documentation" set, explicitly called out in memory index as "10 final docs in docs/, STAGING_READY" — these are the canonical release-readiness record, not disposable sprint noise |
| `ADMIN_TENANT_DETAIL_*` (API mapping, finance labels, permission, provider-360, remaining-blockers, test-results) | 6 | ARCHIVE_HISTORICAL | Same pattern as root-level per-sprint certification reports, just filed under `docs/` instead of root |
| `PHASE_6B_TENANT_DASHBOARD_*` / `PHASE_6B_TENANT_PORTAL_*` | 8 | ARCHIVE_HISTORICAL | Phase 6B tenant dashboard/portal certification set |
| `TENANT_AVAILABILITY_*` | 2 | ARCHIVE_HISTORICAL | Availability API mapping + emergency bugfix report |
| `TENANT_BUSINESS_HOURS_*` | 4 | ARCHIVE_HISTORICAL | Business-hours availability reports |
| `TENANT_HOME_SERVICES_SETUP_*` | 5 | ARCHIVE_HISTORICAL | Home Services setup wizard reports (duplicates the root-level `ADMIN_HOME_SERVICES_CATALOG_SETUP_UI_REPORT*` pattern conceptually, different scope) |
| `TENANT_MENU_CLEANUP_*` / `TENANT_MENU_ROUTE_CLEANUP_REPORT.md` | 4 | ARCHIVE_HISTORICAL | Menu cleanup reports |
| `TENANT_PROFILE_API_MAPPING_REPORT.md`, `TENANT_SERVICE_AREAS_API_MAPPING_REPORT.md`, `TENANT_SERVICE_SETUP_PRICING_LOCATION_REPORT.md` | 3 | ARCHIVE_HISTORICAL | One-off tenant API mapping reports |

### `docs/archive/obsolete/` (already exists)

Contains 3 files: `BARGAIN_MODULE_REMAINING_BLOCKERS.md`, `BARGAIN_MODULE_TEST_RESULTS.md`,
`PHASE_3C_BARGAIN_FRONTEND_REPORT.md` — all dated Jul 8, all related to the bargain module
deactivation. This confirms a prior session already began exactly this kind of archival triage
and used `docs/archive/obsolete/` as the destination. **Recommendation: reuse this same folder
(or a peer `docs/archive/reports/` folder) as the archive destination for the ARCHIVE_HISTORICAL
groups above**, rather than inventing a new location.

## DUPLICATE_SUPERSEDED note

Root `MANUAL_BARGAIN_MODULE_DEACTIVATION_REPORT.md` and `MANUAL_BARGAIN_DEACTIVATION_FINAL_REPORT.md`
cover the same bargain-module deactivation event already documented by the three files sitting in
`docs/archive/obsolete/`. These two root files are effectively duplicate/superseded content and
should archive alongside (or be merged into) the existing `docs/archive/obsolete/` set — flagged
`DUPLICATE_SUPERSEDED` rather than plain `ARCHIVE_HISTORICAL`.

## REVIEW_REQUIRED

None of the root or docs/ report files needed REVIEW_REQUIRED — all classify cleanly as either
ARCHIVE_HISTORICAL, KEEP_CURRENT, KEEP_REFERENCE, or DUPLICATE_SUPERSEDED based on filename
pattern + spot-read content. No DELETE_CONFIRMED or GENERATED_RECREATABLE classifications were
used for any `*.md` file per mission rules (reports are never deleted, only archived, since any
one of them could be the sole record of a past decision).

## Summary counts

- Root `*.md` files: 663 total — 3 KEEP_CURRENT (`README.md`, `REMAINING_BLOCKERS.md`,
  `TEST_RESULTS.md`), 2 DUPLICATE_SUPERSEDED (bargain manual reports), ~658 ARCHIVE_HISTORICAL.
- `docs/` loose `*.md` files (excluding `archive/` and `final-l5-00/`): 56 total — 14
  KEEP_REFERENCE (architecture, deploy, release notes/summary, 10 Sprint-36 FINAL_* docs),
  ~42 ARCHIVE_HISTORICAL.
- `docs/archive/obsolete/`: 3 files, already correctly archived — no action needed.
