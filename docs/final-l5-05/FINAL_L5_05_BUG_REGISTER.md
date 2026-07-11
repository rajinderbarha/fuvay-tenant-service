# FINAL-L5-05 — Bug Register

## L5-05-001: `hs-overview` nav item duplicated `hs-price-experience`'s href, orphaning the real Overview page
- **Severity**: P2 (broken discoverability, not data-loss)
- **Evidence**: Both nav items pointed to `/admin/home-services/price-experience`; `/admin/home-services/overview/page.tsx` (125 lines, real API-backed, built in an earlier sprint per its own header comment) was completely unreferenced
- **Root cause**: Nav item created with the wrong href, likely copy-paste from the adjacent item
- **Files changed**: `frontend/super-admin/components/layout/AdminLayout.tsx`
- **Fix**: `hs-overview` now points to `/admin/home-services/overview`
- **Browser evidence**: Real Chromium test confirms both "Overview" and "Customer Price Experience" now navigate to distinct, correct pages
- **Status**: **FIXED**

## L5-05-002: "Wallet Balance" forbidden label in `field-labels.ts`
- **Severity**: P2 (terminology policy violation)
- **Files changed**: `frontend/super-admin/lib/field-labels.ts`
- **Fix**: `wallet_balance`/`credit_balance` field keys now both display "Usage Credit Balance"
- **Status**: **FIXED**

## L5-05-003: "Tenant Payouts" forbidden label in Settings category table
- **Files changed**: `frontend/super-admin/app/admin/settings/page.tsx`
- **Fix**: Column header changed to "Payouts" (consistent with the existing, already-approved nav label)
- **Status**: **FIXED**

## L5-05-004/005/006: 3 backend `platform_settings` rows with forbidden-terminology labels — found via real Chromium, not static grep
- **Severity**: P1 (static source-code grep found zero hits — these labels come from the database, not source code; only real browser rendering revealed them)
- **Evidence**: Live Chromium run on `/admin/settings` rendered "Usage Credit Is Cash Wallet", "Usage Credit Is Withdrawable", and (from the same table) a `tenant_payouts_enabled` row
- **Root cause**: `platform_settings.label` is a real, admin-editable database column; these 3 rows were seeded with forbidden terminology baked directly into the label text
- **Fix**: Direct `UPDATE platform_settings SET label = ...` for all 3 rows (`usage_credit_is_cash_wallet` → "Usage Credit Treated As Cash", `usage_credit_is_withdrawable` → "Usage Credit External Redemption Allowed", `tenant_payouts_enabled` → "Payouts Enabled") — key names and values untouched, purely a display-label fix, verified as safe via a full settings-related pytest run (58/58 passing) after the change
- **Browser evidence**: Real Chromium re-run confirms zero forbidden terms remain on `/admin/settings`
- **Status**: **FIXED**

## L5-05-007: Usage Credits and Reports — real, mission-critical pages orphaned from navigation
- **Severity**: P1 (Part 14 explicitly requires Usage Credits be discoverable via `tenant_billing`; Part 17 explicitly requires Reports be discoverable)
- **Files changed**: `frontend/super-admin/components/layout/AdminLayout.tsx`
- **Fix**: Added `finance-usage-credits` → `/admin/finance/usage-credits` to the Finance group; `reports` → `/admin/reports` to the Marketing & Growth group
- **Browser evidence**: Real Chromium confirms both nav items navigate to real, non-trivial, working pages
- **Status**: **FIXED**

## L5-05-008 / L5-05B-001: `/admin/operations` (the sidebar's "Jobs" item) is backed by the legacy `/v1/jobs` API, not the canonical `service_jobs`/final-records API
- **Severity**: P0 — directly implicates rule 12 ("do not reintroduce /v1/jobs") and Part 12's explicit requirement ("no /v1/jobs dependency")
- **Evidence**: `jobsApi` in `lib/api.ts` (base path `/v1/jobs`) is imported and used by `app/admin/operations/page.tsx`, `app/admin/operations/[jobId]/page.tsx`, and `app/admin/tenants/[id]/page.tsx`. A separate, newer, canonical page (`/admin/home-services/service-jobs`, backed by `/v1/admin/final-records/jobs`) already exists but is **not** the one linked from the sidebar's "Jobs" item
- **Root cause**: Pre-existing architecture debt — `/v1/jobs` was never fully retired after the canonical final-records API was introduced in an earlier sprint; the sidebar was never updated to point at the newer page
- **FINAL-L5-05B update — full parity investigation completed** (see `FINAL_L5_05B_JOBS_MIGRATION.md`): the canonical page is confirmed **materially thinner** than legacy — missing reassign, status override, force-close, void, SLA tracking, and summary stats, none of which have ANY backend implementation against `service_jobs` today (not a wiring gap — genuinely missing capability). Two real wiring gaps (assignment/execution timeline, notes) WERE closed this sprint (see L5-05B-002).
- **Decision**: per rule 5 ("do not remove working job actions") and rule 3 ("do not solve the Jobs defect by only replacing an endpoint string"), the sidebar "Jobs" item was **deliberately not repointed** this sprint — doing so would silently remove 4 real, actively-usable admin mutation actions with no replacement.
- **Status**: **NOT FIXED — correctly deferred, not hidden.** Real remediation requires building 4 new backend mutation endpoints (with permission/audit/idempotency per Part 5) plus SLA/summary equivalents against `service_jobs` — a substantial, separately-scoped effort. Remains the top Remaining Blocker.

## L5-05B-002: Canonical job detail page had zero timeline/notes visibility despite the backend and API client already supporting it
- **Severity**: P2 (real capability was dead code, not exposed to users — not a P0/P1 since it's an enhancement, not a defect that removes something)
- **Evidence**: `adminServiceJobAssignmentApi.getJobTimeline`, `adminExecutionApi.getJobTimeline`, `adminExecutionApi.getJobNotes` — all real, typed, already calling real, working backend endpoints (confirmed via live curl: all 3 return `200` with real JSON) — were never called from any page
- **Root cause**: Built in an earlier sprint as part of a different feature (service-job-assignments / execution engines), never wired into the canonical job detail page
- **Files changed**: `frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx`
- **Fix**: Added a "Timeline & Notes" section rendering both timelines (merged, sorted by timestamp) and any notes, with an honest empty state when none exist
- **Automated tests**: `tests/test_final_l5_05b_jobs_ia_guard.py::TestJobsNavigationGuard::test_canonical_job_detail_page_renders_timeline_and_notes` — regression guard against this being silently dropped again
- **Live API evidence**: `GET /v1/admin/service-jobs/{id}/assignment-timeline`, `.../execution-timeline`, `.../notes` all return real `200` responses
- **Browser evidence**: Real Chromium confirms the section renders correctly with an honest empty state for a job with no events
- **Status**: **FIXED**

## L5-05B-003: 5 new automated IA regression guards added (Part 16)
- **Files changed**: `tests/test_final_l5_05b_jobs_ia_guard.py` (new file, 6 tests)
- **Coverage**: legacy-page legacy-disclosure banner presence, canonical page non-stub check, timeline/notes wiring regression guard, zero-forbidden-terminology sweep across all of `frontend/super-admin/**/*.ts*` (not just the specific files fixed — the whole tree), zero-duplicate-NAV_GROUPS-href guard (regression guard for L5-05-001), Usage-Credits/Reports-remain-in-nav guard (regression guard for L5-05-007)
- **Status**: **ADDED**, all 6 passing

## L5-05C-001: `HomeServiceJobAssignmentService._load_staff` queried an empty table — real reassignment was unusable against production/demo data
- **Severity**: P0 (the mutation this sprint was built to add would 422 on every real job)
- **Evidence**: `provider_team_members` has 0 rows; every real `service_jobs.assigned_staff_id` actually references `users.id` (role `technician`/`staff`) — confirmed via live DB query. Calling the new admin reassign endpoint against a real job before the fix returned `422 TECHNICIAN_NOT_ELIGIBLE` / `JOB_ASSIGNMENT_STAFF_NOT_FOUND`.
- **Root cause**: `HomeServiceJobAssignmentService._load_staff`/`validate_staff_eligibility` were built against `ProviderTeamMember`, a model/table that was apparently superseded by `users`-based staff (consistent with the separately-shipped "P0 Admin Staff fix" sprint, which already lists real staff from `users`) but never updated in this service.
- **Files changed**: `app/engines/home_service_assignment/service.py` (`_load_staff` falls back to `User` when `ProviderTeamMember` misses; `validate_staff_eligibility` handles both shapes)
- **Live API evidence**: `POST /v1/admin/service-jobs/7caeb8fd-2c6d-4629-be31-e60d940a56a2/reassign` returns real `200` against a live job/technician; job row, `platform_audit_logs`, and `service_job_assignment_events` all updated, confirmed via direct DB query
- **Automated tests**: `tests/test_final_l5_05c_reassign.py` (7 tests); `tests/test_sprint20_job_assignment.py::TestStaffEligibility::test_staff_not_found_raises` updated (now expects 2 lookups, not 1)
- **Status**: **FIXED**

## L5-05C-002: Admin-facing service_jobs reassignment mutation built (Part 4 of FINAL-L5-05C, 1 of 4 required mutations)
- **Severity**: P1 (real missing capability closed, not a defect fix)
- **Files changed**: `app/engines/home_service_assignment/admin_router.py` (new `POST /{job_id}/reassign`, `GET /{job_id}/eligible-technicians`), `frontend/super-admin/lib/api.ts` (`reassignJob`, `getEligibleTechnicians`), `frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx` (`ReassignModal`, "Reassign Technician" action)
- **RBAC**: `require_super_admin` dependency (platform's only granular-enough role for this write today — see Blocker 4, no distinct Admin Operations/Finance role exists yet)
- **Audit**: real `platform_audit_logs` row via `record_platform_audit` (`operation="service_job.reassigned"`) plus the pre-existing `service_job_assignment_events` timeline row
- **Error contract**: maps to the mission's required codes (404 `JOB_NOT_FOUND`, 403 `JOB_REASSIGN_FORBIDDEN`, 409 `JOB_REASSIGN_NOT_ALLOWED`/`TECHNICIAN_TENANT_MISMATCH`, 422 `TECHNICIAN_NOT_ELIGIBLE`/`REASON_REQUIRED`)
- **Live API evidence**: 200 success case, 404 (unknown job), 422 (empty reason, schema-validated), 401 (no auth) all confirmed via live `curl`
- **Browser evidence**: real Chromium E2E (`e2e/tenant-portal/final-l5-05c-reassign.spec.ts`) — login, open modal, real technician list loads (not empty/mocked), submit with reason, modal closes only on real success, new timeline event renders
- **Status**: **FIXED** (1 of 4 required canonical mutations; status override / force-close / void remain unbuilt — see `FINAL_L5_05B_JOBS_MIGRATION.md`)

## L5-05D-001: Status override, force-close, void built (3 more of 4 required canonical mutations)
- **Severity**: P1 (real missing capability closed, not a defect fix)
- **Files changed**: `app/engines/execution/admin_job_actions.py` (new — centralized `AdminJobActionsService`), `app/engines/execution/home_service_router.py` (4 new endpoints on the existing `admin_router` at `/v1/admin/service-jobs`), `frontend/super-admin/lib/api.ts` (`getAllowedServiceJobOverrideTargets`, `overrideServiceJobStatus`, `forceCloseServiceJob`, `voidServiceJob`), `frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx` (`StatusOverrideModal`, `ForceCloseModal`, `VoidModal`)
- **Policy derived from real code, not guessed**: force-close (Policy A: never creates an automatic Completed Job Deduction) and void (BLOCK_VOID_AFTER_DEDUCTION) were both derived from `app/engines/execution/usage_credit_deduction.py`'s real, idempotent-per-job deduction logic — see `FINAL_L5_05B_JOBS_MIGRATION.md` for full rationale.
- **Real, pre-existing architecture inconsistency found and documented**: 3 separate, overlapping `JOB_STATUS_*`/`JOB_TRANSITIONS` constant sets exist across `execution/constants.py`, `final_records/constants.py`, and `home_service_assignment/constants.py`, none of which fully matches the real, live `service_jobs.status` values seen in production/demo data. These 3 new mutations are deliberately terminal-status-based (not dependent on resolving which constant set is authoritative), so they work correctly today; reconciling the 3 sets into one is a real, documented follow-up, not attempted this sprint.
- **RBAC**: `require_super_admin` on all 4 new endpoints.
- **Audit + timeline**: every mutation writes both a `service_job_execution_events` row and a `platform_audit_logs` row.
- **Error contract**: `JOB_STATUS_CONFLICT` (409), `JOB_ALREADY_TERMINAL`/`JOB_ALREADY_CLOSED`/`JOB_ALREADY_VOIDED` (409), `INVALID_ADMIN_OVERRIDE_TRANSITION` (422), `JOB_DEDUCTION_REVERSAL_REQUIRED` (409), `REASON_REQUIRED` (422).
- **Live API evidence**: all 3 mutations run against real jobs via curl with real DB verification — status override (`assigned`→`cancelled`), force-close (`in_progress`→`force_closed`, `deduction_created: false`), void (`new`→`voided`), duplicate force-close correctly 409s, and void against a job with a real `completed_job_deduction` row (`L501-JOB-0004`) correctly blocked with `JOB_DEDUCTION_REVERSAL_REQUIRED`.
- **Automated tests**: `tests/test_final_l5_05d_exceptional_mutations.py` (14 tests).
- **Browser evidence**: real Chromium E2E (`e2e/tenant-portal/final-l5-05d-exceptional-mutations.spec.ts`) covering the full status-override UI flow end-to-end.
- **Status**: **FIXED** (3 of 4 required canonical mutations now closed; SLA tracking and operational summary remain unbuilt — see `FINAL_L5_05B_JOBS_MIGRATION.md`)

## Result
14 of 15 real bugs/gaps found across FINAL-L5-05, FINAL-L5-05B, FINAL-L5-05C, and FINAL-L5-05D were fixed and live-verified via real Chromium and/or live API calls (not just static analysis — several were only discoverable by actually rendering the page or calling the real API). 1 real, pre-existing, rule-relevant architecture gap (`/v1/jobs` on the primary Jobs nav item) remains fully investigated (complete parity matrix built, now with 3 of 4 mutations closed) and correctly, deliberately NOT force-migrated, since SLA/summary tracking still don't exist and full parity has not been re-proven — the single reason this sprint cannot honestly claim full READY certification.
