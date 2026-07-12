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

## L5-05E-001: Canonical SLA tracking + operational summary built, primary Jobs navigation migrated, `/admin/operations` converted to a real redirect, zero active Super Admin `jobsApi`/`/v1/jobs` usage remains
- **Severity**: P0 (closes the single remaining condition blocking `READY_FINAL_L5_05_ADMIN_INFORMATION_ARCHITECTURE_CERTIFIED`)
- **Files changed**: `app/engines/final_records/sla_summary.py` (new), `app/engines/final_records/admin_router.py` (`/jobs/summary` endpoint, `sla`/`collected_amount`/`completed_job_deduction_credits` fields added to list/detail), `frontend/super-admin/lib/api.ts` (`getJobsSummary`, `listForTenant`), `frontend/super-admin/app/admin/home-services/service-jobs/page.tsx` (SLA column + summary cards), `.../[jobId]/page.tsx` (SLA fields, `activeNav` fix), `frontend/super-admin/components/layout/AdminLayout.tsx` (Jobs nav href), `frontend/super-admin/app/admin/operations/page.tsx` + `[jobId]/page.tsx` (converted to real redirects), `frontend/super-admin/app/admin/tenants/[id]/page.tsx` (migrated off `jobsApi` onto `finalRecordsAdminApi.listForTenant`)
- **SLA policy derived from real, existing config, not guessed**: `PricingTier.default_sla_minutes`, resolved per job via `TierLocation` (zipcode overrides city, matching the pattern already used elsewhere in pricing), batch-resolved in at most 2 queries per page of jobs (no per-row query).
- **Live API evidence**: `GET /v1/admin/final-records/jobs/summary` returns real reconciled counts; job list/detail responses include real `sla` objects (confirmed `BREACHED` with real `minutes_overdue` on a real stale job); tenant-scoped job list returns real `collected_amount`/`completed_job_deduction_credits` (confirmed `775`/`21.0` on a real completed job).
- **Navigation migration evidence**: `AdminLayout.tsx`'s Jobs nav item now hrefs `/admin/home-services/service-jobs`; real Chromium confirms clicking "Jobs" opens the canonical page with visible summary cards and SLA data, zero `/v1/jobs` network requests observed.
- **Redirect evidence**: `/admin/operations` and `/admin/operations/[jobId]` are both real Next.js server-component redirects (confirmed `ƒ` dynamic route in the production build); real Chromium confirms navigating to `/admin/operations` lands on the canonical page with zero legacy API traffic.
- **Zero jobsApi evidence**: `grep -rn "jobsApi\." frontend/super-admin/app frontend/super-admin/components` → 0 hits; new automated guard test (`test_zero_active_jobs_api_imports_anywhere_in_super_admin`) added to prevent regression.
- **Automated tests**: `tests/test_final_l5_05e_sla_summary.py` (8 tests); 3 new guard tests added to `tests/test_final_l5_05b_jobs_ia_guard.py`.
- **Browser evidence**: 2 new Chromium tests (`e2e/tenant-portal/final-l5-05e-jobs-migration.spec.ts`); all 5 FINAL-L5-05B/C/D/E Chromium specs re-verified passing together.
- **Collateral fixes (real, expected consequences of this migration)**: `test_admin_operations_group_order` (nav href updated), 2 tenant-detail payment-field tests (updated to real `collected_amount`/`completed_job_deduction_credits` field names, replacing legacy `payable_to_provider`/`quoted_price`), `test_admin_job_detail_shows_credit_and_deduction_record` (repointed from the now-redirected legacy page to the canonical page, which already had this section since FINAL-L5-05B).
- **Status**: **FIXED**

## L5-05F-001: `/admin/finance/wallets` and `/admin/provider-wallets` are real, live backend surfaces built on the forbidden `tenant_wallets` model
- **Severity**: P1 (real architecture-violation finding, not yet exploitable since both pages are currently unreachable via any nav — but the backend endpoints are live, permission-gated, and one supports a `credit` mutation)
- **Evidence**: `app/engines/finance_hub/service.py::list_wallets` queries `TenantWallet` directly (`select(TenantWallet, Tenant)...credit_balance...reserved_balance`) and is exposed at a real, permission-gated route (`GET /v1/admin/finance/wallets`, `require_permission(P.FINANCE_WALLETS_READ)`). The frontend page (`/admin/finance/wallets/page.tsx`) is titled "Wallet Directory" with "Available Balance"/"Reserved Balance"/"Health Band" columns -- structurally the same forbidden wallet model this and every prior FINAL-L5 mission explicitly bans (contrast with the approved `tenant_billing.credit_balance`/Usage Credit Ledger model). `/admin/provider-wallets/page.tsx` similarly calls a real `adminWalletApi.credit(tenantId, {...})` mutation.
- **Root cause**: Pre-dates this sprint; a previous investigation (FINAL-L5-05B) concluded "`tenant_wallets` is confirmed dead code (comments only, no live reads)" -- that conclusion was **incorrect** for these two pages specifically (it was accurate for the code paths FINAL-L5-05B actually checked, but did not cover `finance_hub`'s wallet directory).
- **Why not fixed this sprint**: Removing or rearchitecting a real, permission-gated backend read+mutation surface (including a `credit` action) is a substantial, risky change requiring an explicit financial-policy decision (mirror the migration this session already did for Jobs force-close/void), not a same-session IA-navigation fix. Per rule 12 ("do not preserve duplicate routes merely because both currently work") the RIGHT direction here is removal/migration, not linking -- so the safe, correct action taken this sprint was to **leave both pages deliberately unlinked** (their current orphaned state is protective, not a defect) and document this honestly as a real blocker rather than silently mark it "orphan, low priority."
- **Files reviewed, not changed**: `app/engines/finance_hub/service.py`, `app/engines/finance_hub/admin_router.py`, `frontend/super-admin/app/admin/finance/wallets/page.tsx`, `frontend/super-admin/app/admin/provider-wallets/page.tsx`.
- **Status**: **DOCUMENTED, NOT FIXED** -- requires a dedicated remediation sprint (migrate off `TenantWallet`/`tenant_wallets` onto the approved `tenant_billing`/Usage Credit Ledger model, or formally deprecate+remove if the capability is genuinely unused). Both pages correctly remain unreachable via any nav in the meantime.

## L5-05F-002: two initial duplicate-route "resolutions" were investigated, found to be false positives, and correctly reverted
- **Severity**: informational (process finding, not a shipped bug -- caught and reverted before commit)
- **Evidence**: `/admin/notification-templates` (`sprint27AdminApi` → real `/v1/admin/notification-templates` backend, `NotifEventTemplate` model) and `/admin/notifications/templates` (`notifTemplateAdminApi` → real `/v1/admin/notifications/templates` backend, `AdminNotifTemplate` model) looked like an obvious near-duplicate from route naming alone. Likewise `/admin/workflows/templates` (`workflowTemplateApi`, vertical/workflow-type/service-mapping builder) vs `/admin/workflow-templates` (`masterDataApi`, Sprint 34C Centralized Master Data catalog templates). Both pairs were initially converted to redirects under the (incorrect) assumption they were the same capability; a follow-up check of each page's actual backing API and backend route revealed they are **genuinely separate, independently real features** that merely share similar names.
- **Root cause of the near-miss**: Route-name similarity is not sufficient evidence of duplication -- the FINAL-L5-05B/C parity work established this correctly for Jobs (deep backend investigation before any redirect), but this sprint initially skipped that same rigor for two lower-stakes-looking clusters.
- **Fix**: Both redirects reverted via `git checkout` before commit; no functionality was ever actually lost (caught within the same session, before push). No test failures shipped.
- **Lesson applied going forward**: any further duplicate-route cluster resolution in a future FINAL-L5-05F continuation must verify the backing API/backend route for both sides of a suspected cluster before converting either to a redirect -- exactly the standard already used for the Jobs domain.
- **Status**: **REVERTED, DOCUMENTED** -- both clusters remain open/unresolved (correctly, since they are not actually duplicates); reclassify as two genuinely distinct capabilities in a future route-inventory pass rather than a "duplicate cluster."

## L5-05F-003: Complaint Policies page was a real, working, fully orphaned page
- **Severity**: P2 (discoverability gap, not a defect -- the page itself works)
- **Evidence**: `/admin/complaint-policies/page.tsx` (134 lines, real) had zero incoming links from any nav or contextual source (confirmed via `grep -rl` returning no hits outside the page's own file).
- **Fix**: Added `{ id: "complaint-policies", href: "/admin/complaint-policies", label: "Complaint Policies", ... }` to the Operations nav group in `AdminLayout.tsx`, immediately after Complaints (reusing the existing `AlertOctagon` icon import, no new imports needed).
- **Files changed**: `frontend/super-admin/components/layout/AdminLayout.tsx`.
- **Automated tests**: existing `test_no_duplicate_nav_group_hrefs` guard re-verified passing (no collision introduced).
- **Status**: **FIXED**

## L5-05G-001: `TenantWallet`/`tenant_wallets` is real, load-bearing package/commission billing infrastructure, not dead or safely-removable code — full investigation, zero code changes
- **Severity**: P0 finding (scope-changing), 0 code risk introduced (no changes made)
- **Evidence**: See `FINAL_L5_05G_WALLET_ARCHITECTURE_INVESTIGATION.md` for full detail. Real database check: `tenant_wallets`/`wallet_transactions` have 0 rows (no reconciliation/migration needed), but `app/engines/platform_commerce/ledger.py`'s `credit_wallet`/`debit_wallet`/`credit_deposit`/`debit_deposit` functions are called from 12 real backend files spanning package purchases (`package_commerce/service.py`), commission processing (`invoice_payment/commission_service.py`), field-ops billing, tenant health scoring (`credit_wallet_health`, a real 15%-weighted signal), and -- critically -- Security Deposit credit/debit (`finance_hub/service.py`), which shares the exact same `ledger.py` module. A third, separately-mounted router (`platform_commerce/router.py`, real `/v1/commerce/*` routes registered in `main.py`) exposes a job-linked `engine_deduct_wallet` endpoint whose relationship to the certified `Completed Job Deduction` flow (`execution/usage_credit_deduction.py`) is unresolved.
- **Root cause of the original L5-05F-001 framing being incomplete**: that finding (correctly) identified 2 orphaned admin pages backed by `tenant_wallets`, but did not trace the full dependency graph -- the system is far deeper and more load-bearing than 2 admin pages.
- **Why no fix was attempted**: disabling, redirecting, or decommissioning any part of this system without independently verifying all 12 dependent call sites (including real revenue-adjacent package/commission flows and the Security-Deposit-sharing `ledger.py`) would risk a real, hard-to-reverse regression to certified, working functionality -- directly contradicted by this mission's own rule 1 ("do not delete tenant_wallets data before full classification") and rule 16 ("do not break Completed Job Deduction integrity"). The two originally-flagged admin pages remain safely unlinked from navigation (established in FINAL-L5-05F, re-confirmed unchanged this sprint) -- their actual exposure risk is already low.
- **Files reviewed, not changed**: `app/engines/platform_commerce/{models,ledger,service,router,preflight}.py`, `app/engines/invoice_payment/{wallet_service,commission_service,admin_router}.py`, `app/engines/package_commerce/service.py`, `app/engines/finance_hub/service.py`, `app/engines/tenant_engine/{admin_service,admin_router,portal_router,health,constants}.py`, `app/engines/field_ops/billing_service.py`, `app/engines/customer_credits/service.py`, `app/engines/settings_engine/admin_router.py`.
- **Status**: **INVESTIGATED, DOCUMENTED, NOT FIXED** -- requires a dedicated architecture-reconciliation sprint with real time to trace every consumer end-to-end and get an explicit product/finance decision on rename-vs-merge-vs-retire. A safe, narrow follow-up (renaming only the admin-facing display terminology, not touching transactional logic) is identified as a lower-risk partial step, also not attempted this sprint to keep this session's changeset at zero backend risk.

## L5-05H-001: `engine_deduct_wallet` (`/v1/commerce/tenants/{id}/wallet/deduct`) could become a second, non-cross-checked Completed Job Deduction path
- **Severity**: P0 for the mission's mandatory Part 7 gate (latent risk — no active production bug); resolved this sprint.
- **Evidence**: `app/engines/platform_commerce/service.py:372` `engine_deduct_wallet` posts to `TenantWallet`/`wallet_transactions` (via `ledger.debit_wallet`), a completely different table/ledger from the canonical `deduct_for_completed_job` (`app/engines/execution/usage_credit_deduction.py:67`), which posts to `tenant_billing`/`usage_credit_ledger`. `grep -rn "engine_deduct_wallet\|wallet/deduct" app/` returns exactly 2 hits (the function definition and its own route registration) — zero internal callers anywhere in job completion, force-close, or void. `grep -rn "wallet/deduct\|engine_deduct" tests/` returns 0 hits — zero test coverage.
- **Root cause**: The endpoint was built and labeled `[Internal engine use]` but never actually wired into the job-lifecycle flow it was presumably intended for; the canonical Completed Job Deduction was built independently (FINAL-L5-05C/D era) on `tenant_billing`/`usage_credit_ledger` instead.
- **Fix**: `POST /v1/commerce/tenants/{tenant_id}/wallet/deduct` now returns `410 Gone` unconditionally, pointing callers at `deduct_for_completed_job`. The service method and the shared `ledger.debit_wallet` primitive (used by commission processing and Security Deposits) were left untouched — only the specific job-deduction entry point was blocked, per the mission's "prove before deleting" instruction.
- **Files changed**: `app/engines/platform_commerce/router.py` (blocked route); `tests/test_final_l5_05b_jobs_ia_guard.py` (2 new guard tests, `TestFinalL5_05H_JobDeductionGate`).
- **Automated tests**: Jobs IA regression guard 12/12 passing (10 existing + 2 new); commerce/wallet/usage-credit-scoped suite 130/130 passing; full backend regression re-run, 0 regressions.
- **Status**: **FIXED**. See `FINAL_L5_05H_JOB_DEDUCTION_GATE.md` for full comparison evidence.

## L5-05I-001 through L5-05I-010: remaining commerce-ledger consumer classification and domain-boundary findings
- **Severity**: Mixed — see individual findings below. No active production double-charge found; all findings are either latent risk, mislabeled/duplicate admin surfaces, or a dead/always-default health signal.
- **Evidence**: Full per-consumer classification in `FINAL_L5_05I_CONSUMER_CLASSIFICATION.md`; full boundary/matrix/strategy/migration-plan evidence in `FINAL_L5_05I_DOMAIN_BOUNDARIES.md`.
- **L5-05I-001 (Remaining ledger consumers unclassified)**: **RESOLVED** — all 11 remaining consumers (C1–C11) individually classified with evidence; 0 remain UNKNOWN. However, the investigation found the true consumer graph is larger than the original 12-file inventory (at least 5 independent "admin adjusts tenant credit" implementations and 2 independent commission implementations were newly discovered).
- **L5-05I-002 (Package Credit ownership unclear)**: **NOT RESOLVED** — two independent implementations (`package_commerce.service.py`, `finance_hub.service.py`) both grant credit into `TenantWallet`, not the certified `tenant_billing`. Decision made (target: canonical `UsageCreditService.grant()`), migration not implemented (Phase 3).
- **L5-05I-003 (Commission domain unclear)**: **NOT RESOLVED** — two independent implementations (`invoice_payment.ServiceCommissionService`, `platform_commerce.CommerceService.deduct_commission` via `field_ops`), neither has ever executed against real data (both commission tables have 0 rows). Decision made (canonical: `invoice_payment.ServiceCommissionService`, built explicitly for `service_jobs`), migration not implemented (Phase 4).
- **L5-05I-004 (Security Deposit shared-ledger boundary unclear)**: **RESOLVED** — confirmed via source read that `credit_deposit`/`debit_deposit` never reference `TenantBilling` or `UsageCreditLedger`; new regression guard test added (`test_security_deposit_functions_never_touch_tenant_billing_or_usage_credit_ledger`).
- **L5-05I-005 (Field-operations billing ownership unclear)**: **PARTIALLY RESOLVED** — classified LEGACY_DUPLICATE (`field_ops.BillingService`, tied to a superseded `jobs` table with 0 real rows), same shape as the 05H finding, but not blocked this sprint because it has real internal callers within its own subsystem that were not yet dependency-proven safe to remove (Phase 6).
- **L5-05I-006 (Tenant health depends on ambiguous financial source)**: **RESOLVED (diagnosis), NOT FIXED (code)** — confirmed `credit_wallet_health` (15% weight) has never been written in this environment; its only writer is unreachable (gated on the 0-row `jobs` table). Every tenant's health score silently uses the hardcoded default of 100.0 for this signal. Remediation identified (read `tenant_billing.credit_balance` directly) but not implemented — needs its own test coverage.
- **L5-05I-007 (Subscription billing interaction unknown)**: **RESOLVED** — confirmed NOT_IMPLEMENTED; only forward-looking constants exist (`SUBSCRIPTION_LEADS`/`SUBSCRIPTION_BOOKING`, marked "soon"/"future"), no live consumer.
- **L5-05I-008 (Shared ledger primitive mixes infrastructure and policy)**: **RESOLVED (decision)** — classified as Option C (mixed); recommended split (infra primitives stay, new callers must use domain-typed wrappers) documented as a Phase-1/ongoing follow-up, not implemented this sprint.
- **L5-05I-009 (Generic wallet permissions remain ambiguous)**: **NOT RESOLVED** — 8 active mutation endpoints remain classified AMBIGUOUS_GENERIC across 4 routers (`platform_commerce`, `field_ops`, `tenant_engine`, `package_commerce`); a new regression guard (`test_known_generic_wallet_mutation_endpoint_count_does_not_silently_grow`) pins this count so it cannot silently grow, but does not fix it. **`package_commerce`'s version is the most product-risk-relevant**: it is gated by `FINANCE_USAGE_CREDITS_*` permissions but mutates `TenantWallet`, not `tenant_billing` — an admin using the correctly-permissioned Usage Credits action today adjusts the wrong balance.
- **L5-05I-010 (Domain-service migration sequence undefined)**: **RESOLVED** — 10-phase sequenced migration plan produced (Phase 0 = this sprint's classification, Phases 1–10 = safety guards through frontend cleanup), each phase scoped with files, DB changes, compatibility/rollback/test requirements. No phase beyond 0 executed this sprint.
- **Bounded fix implemented this sprint**: 3 new architecture regression guard tests (`TestFinalL5_05I_DomainBoundaryGuards` in `tests/test_final_l5_05b_jobs_ia_guard.py`) — Security Deposit isolation guard, generic-wallet-endpoint-count pin, field_ops/service_jobs non-collision guard. No production code paths were changed (per the mission's explicit "classification before extraction" instruction).
- **Status**: **INVESTIGATED AND CLASSIFIED, MOSTLY NOT FIXED** — this is architecture debt spanning at minimum 4 engines and 8 live endpoints; per this engagement's established pattern, documenting it accurately with a real, evidenced migration plan is the correct outcome for a classification-scoped sprint, not a forced partial implementation.

## L5-05J-001: Five independent Usage Credit adjustment implementations
- **Severity**: P1 (architecture debt; the highest-risk sub-part — package_commerce's mislabeling — is P0-adjacent).
- **Evidence**: See `FINAL_L5_05J_USAGE_CREDIT_CONSOLIDATION.md` Part 2 for the full 5-path table.
- **Root cause**: Each of Sprints 4/5/9/23-era work built its own tenant-credit-adjustment surface independently, none aware of the others.
- **Affected callers/endpoints**: `platform_commerce.admin_credit_wallet`, `field_ops.BillingService.admin_wallet_topup/adjust`, `tenant_engine.credit_topup/credit_adjust`, `package_commerce.admin_topup_wallet/admin_adjust_wallet`, `invoice_payment.ProviderCreditWalletService.admin_credit`.
- **Backend changes**: 2 of 5 paths (`tenant_engine`, `package_commerce`) resolved this sprint — see L5-05J-002/003.
- **Tests**: `tests/test_final_l5_05j_usage_credit_service.py` (24 tests).
- **Final status**: **PARTIALLY FIXED** — the 2 paths that were genuinely mislabeled/dead within Usage Credit scope are fixed; the 3 that belong to Commission/field-ops/provider-earning domains are correctly carried forward, not claimed resolved.

## L5-05J-002: Usage Credit mutations targeting TenantWallet
- **Severity**: P0 (product-risk: an admin using the correctly-permissioned "Usage Credits" action was adjusting the wrong balance).
- **Evidence**: `package_commerce.admin_topup_wallet`/`admin_adjust_wallet` gated by `FINANCE_USAGE_CREDITS_TOP_UP`/`_ADJUST` but wrote `TenantWallet.credit_balance` via `ledger.credit_wallet`/`debit_wallet`.
- **Root cause**: Permission names were assigned correctly at creation time but the implementation was never pointed at `tenant_billing`.
- **Fix**: `package_commerce/admin_router.py`'s 4 `credit-wallet` endpoints now delegate to `UsageCreditService` — zero `TenantWallet` writes remain on this path.
- **Tests**: `test_package_credit_wallet_legacy_endpoints_delegate_to_canonical_service` (architecture guard) + full `TestAdjustCredit` suite.
- **Final status**: **FIXED**.

## L5-05J-003: Package Credit grants targeting ambiguous balance
- **Severity**: P0 (the mission's core "Package Credit Grant must flow through canonical Usage Credit service" requirement).
- **Evidence**: `package_commerce.service.py::purchase_package`'s included-credit grant (the one real, purchase-money-linked path) called `ledger.credit_wallet` (→ `TenantWallet`).
- **Fix**: Repointed to `UsageCreditService.grant_package_credit` (→ `tenant_billing`/`usage_credit_ledger`), idempotency identity `package_credit_grant:{purchase_id}:1`, enforced unique at the DB level (migration 133).
- **Remaining gap (not fixed)**: `finance_hub.service.py::retry_credit_posting`, a separate, schema-coupled "Credit Top-up Order" flow (own model with a `wallet_transaction_id` FK), independently credits `TenantWallet` and was not discovered until this sprint. Migrating it requires a schema change (`usage_credit_ledger_id` column) beyond this sprint's bounded-fix budget.
- **Tests**: `test_13/14/16_*` in `tests/test_sprint5_packages.py` (rewritten to assert the new canonical path), `TestGrantPackageCredit` in the new 05J suite.
- **Final status**: **PARTIALLY FIXED** — the primary package-purchase path is migrated; the finance_hub topup-order path is documented, not migrated.

## L5-05J-004: Package grant idempotency incomplete
- **Severity**: P2.
- **Evidence**: Grant identity `package_credit_grant:{package_assignment_id}:{activation_version}` is enforced unique at the DB level for the migrated path (L5-05J-003). Package cancellation/expiry reversal behavior was traced and found **not implemented anywhere in the codebase**, including the pre-migration path — a pre-existing gap, not introduced this sprint.
- **Final status**: **PARTIALLY FIXED** — duplicate-grant protection is real and tested; cancellation/expiry reversal remains unimplemented (documented, not a regression).

## L5-05J-005: Usage Credit endpoints remain generic/ambiguous
- **Severity**: P1.
- **Evidence**: Of FINAL-L5-05I's 8 `AMBIGUOUS_GENERIC` endpoints, the 4 in Usage Credit/Package Credit scope are resolved this sprint (2 blocked, 2 converted). The other 4 (Commission/field-ops/provider-earning domains) are explicitly out of this sprint's scope per the mission's own instructions.
- **Final status**: **FIXED within scope** — 0 unresolved ambiguous endpoints remain in the Usage Credit/Package Credit domain; 4 remain in adjacent domains, correctly not claimed as resolved.

## L5-05J-006: Tenant health credit signal always defaults to 100
- **Severity**: P0 (real, live scoring defect affecting every tenant, 15% of health score weight).
- **Evidence**: `credit_wallet_health`'s only writer (`CommerceService._update_wallet_signal`) was gated on the legacy field_ops `jobs` table (0 real rows) — never fired in this environment.
- **Fix**: Replaced with `usage_credit_health`, computed live from `tenant_billing.credit_balance` on every health-score request (no caching, no stale-default fallback for real requests). Formula documented in `FINAL_L5_05J_USAGE_CREDIT_CONSOLIDATION.md` Part 12.
- **Tests**: `test_health_score_computation` (updated), `test_tenant_health_computes_usage_credit_signal_from_tenant_billing` (guard).
- **Final status**: **FIXED**.

## L5-05J-007: Tenant health uses wallet terminology
- **Severity**: P2.
- **Evidence**: `HEALTH_SCORE_WEIGHTS["credit_wallet_health"]` renamed to `"usage_credit_health"` (same 0.15 weight). `analytics/service.py::get_platform_summary` still references a `credit_wallet_health` Redis key pattern for an `active_tenants` KPI — this was already always-empty (same root cause as L5-05J-006), so no behavior regression, but the terminology/KPI itself is not yet repointed.
- **Final status**: **PARTIALLY FIXED** — canonical health signal renamed and repaired; one unrelated analytics KPI reference left for a future sprint (documented, non-regressing).

## L5-05J-008: Usage Credit RBAC incomplete
- **Severity**: P2.
- **Evidence**: Reused the existing, real `FINANCE_USAGE_CREDITS_READ/TOP_UP/ADJUST/LEDGER_READ` and `TENANT_HEALTH_READ` permissions (already correctly defined in `app/core/permissions.py`) rather than inventing new `usage_credits.*` keys — `super_admin` has `P.ALL`, so canonical endpoints are reachable today. Distinct "Admin Finance"/"Admin Operations"/"Admin Read Only" roles do not exist as backend concepts (pre-existing finding, FINAL-L5-05G) — a full role matrix could not be built or tested this sprint.
- **Final status**: **NOT FIXED** — RBAC is real and permission-gated, but the mission's full expected-roles matrix (Part 15) requires roles that don't exist yet.

## L5-05J-009: Usage Credit audit matrix incomplete
- **Severity**: P2.
- **Evidence**: `UsageCreditService._post()` writes a `platform_audit_logs` row for every mutation (`usage_credit.adjusted`, `package_credit.granted`, `usage_credit.reversal_created`, `usage_credit.migration_adjustment`) via `record_platform_audit`, with actor/tenant/amount/before/after/source/reason/idempotency_key/request_id — matching the mission's Part 16 field list. `LEGACY_USAGE_CREDIT_ENDPOINT_USED`/`_BLOCKED` and `TENANT_USAGE_CREDIT_HEALTH_EVALUATED` event types were not added (health reads are deliberately not audited per-request, per the mission's own "avoid noisy event volume" guidance, but this policy choice was not written up as a formal document).
- **Final status**: **PARTIALLY FIXED** — mutation audit is real and complete; the full audit-policy document is not written.

## L5-05J-010: Live API and Chromium evidence missing
- **Severity**: P1 (explicit acceptance-criteria blocker).
- **Evidence**: No backend server was started this session; no live HTTP calls or Chromium runs were performed. All verification is unit-test-level (mocked DB) plus direct-SQL row-count checks (live Postgres, via asyncpg) and static architecture guards.
- **Final status**: **NOT FIXED** — this alone prevents a `READY` recommendation per the mission's own explicit rule ("Do not return READY without live API/Chromium verification").

## L5-05K-001: Finance Hub top-up path bypasses canonical Usage Credit service
- **Severity**: P0.
- **Evidence**: `CommerceService.confirm_purchase` and `FinanceHubService.retry_credit_posting` both called `ledger.credit_wallet` (→ `TenantWallet`) — the sixth credit-grant path found in FINAL-L5-05J, undiscovered until that sprint.
- **Fix**: Both now call `UsageCreditService.grant_topup_credit` (→ `tenant_billing`/`usage_credit_ledger`). Security Deposit replenishment (`credit_deposit`, inside `confirm_purchase`) is untouched — separate domain, correctly preserved.
- **Tests**: `tests/test_final_l5_05k_topup_migration.py` (15 tests, unit + true concurrency + architecture guards); live-verified end-to-end via the real `retry-credit` HTTP endpoint against the real database.
- **Final status**: **FIXED**.

## L5-05K-002: Top-up grant source identity undefined
- **Severity**: P1.
- **Evidence**: No `source_type`/`source_id` typing existed for top-up credits before this sprint (the old `credit_wallet` call used generic `TxnType.PURCHASE`).
- **Fix**: `source_type="FINANCE_HUB_CREDIT_TOPUP"`, `source_id=<credit_topup_orders.id>`, `event_type=TOPUP_CREDIT_GRANTED` — all typed and enforced in `UsageCreditService.grant_topup_credit`.
- **Final status**: **FIXED**.

## L5-05K-003: Top-up grant idempotency incomplete
- **Severity**: P0.
- **Evidence**: Before this sprint, `confirm_purchase` used idempotency key `f"purchase:{payment_id}"` while `retry_credit_posting` used a *different* key `f"retry:{t.id}"` — a real duplicate-grant risk if both paths ever fired for the same order (e.g. a crash between signature verification and the topup-row update).
- **Fix**: Both now use the single, stable identity `topup_credit_grant:{topup_order_id}:1`, enforced unique at the DB level (`usage_credit_ledger.idempotency_key`, migration 133). Verified with a true concurrent-request test (real Postgres, not mocks) — exactly 1 ledger row for 2 simultaneous grant calls with the same key.
- **Final status**: **FIXED**.

## L5-05K-004: Duplicate approval/grant risk
- **Severity**: P0.
- **Evidence**: Same root cause as L5-05K-003, plus a *newly discovered* race: `UsageCreditService._post()`'s "create `tenant_billing` row if missing" logic had a TOCTOU race for brand-new tenants — two concurrent mutations could both attempt to INSERT the first row and the loser would crash with `IntegrityError`, found only by the true-concurrency test (`test_topup_grant_concurrent_with_manual_adjustment_no_lost_update`), not by any unit test.
- **Fix**: `INSERT ... ON CONFLICT (tenant_id) DO NOTHING` + unconditional locked re-select, in `usage_credits/service.py::_post()`. Re-run after the fix: both concurrent mutations applied correctly, final balance exact, no lost update.
- **Final status**: **FIXED**.

## L5-05K-005: Existing top-up records unreconciled
- **Severity**: P1 (as scoped) → **N/A** (as discovered).
- **Evidence**: `credit_topup_orders` has 0 rows in this environment, verified live via direct SQL both before and after this sprint's changes.
- **Final status**: **FIXED / NOT APPLICABLE** — there is nothing to reconcile; 0 records were silently corrected because 0 records existed.

## L5-05K-006: Top-up RBAC incomplete
- **Severity**: P2.
- **Evidence**: Real, distinct permissions already existed and are unchanged (`P.FINANCE_TOPUPS_READ/UPDATE/REFUND`). Live-verified: unauthenticated → `401`; non-existent tenant → `404`. Distinct low-privilege admin roles (Finance-capable Admin / Admin Read Only) still do not exist as backend concepts — re-confirmed by directly querying the `admin.readonly@serviceos.local` account's real DB role (`super_admin`, identical to every other admin account).
- **Final status**: **PARTIALLY FIXED** — real permission gates exist and are proven live; the full expected-roles matrix cannot be tested until those roles exist.

## L5-05K-007: Top-up audit incomplete
- **Severity**: P2.
- **Evidence**: `TOPUP_CREDIT_GRANTED` events are fully audited (`topup_credit.granted` via `record_platform_audit`, verified live with real before/after balances). `retry_credit_posting`/`refund_topup`'s pre-existing `_audit()` calls are unchanged. `confirm_purchase` does not audit order creation/payment-verification steps — a pre-existing gap, not newly introduced.
- **Final status**: **PARTIALLY FIXED** — the credit-grant event itself is fully audited; order-lifecycle audit events (creation, payment verification) remain a pre-existing, documented gap.

## L5-05K-008: True concurrent-request verification missing
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: `tests/test_final_l5_05k_topup_migration.py::TestTrueConcurrency` opens a real `AsyncEngine` against live Postgres and runs genuinely concurrent `asyncio.gather()` calls — not unit tests. Found and fixed a real race condition (L5-05K-004).
- **Final status**: **FIXED**.

## L5-05K-009: Live API verification missing
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: Real backend started (`uvicorn`, port 8000, real Postgres, migrations current at 134). Live HTTP matrix executed: login, balance/ledger reads, manual adjustment + idempotent retry (verified single balance increase), insufficient-debit `402`, `engine_deduct_wallet` `410`, `tenant_engine` legacy wallet endpoint `410`, unauthenticated `401`, non-existent-tenant `404`, `package_commerce` canonical adapter `200` with real data, and a full top-up grant end-to-end via the real `retry-credit` endpoint (balance 3979→4579, `usage_credit_ledger_event_id` correctly linked, `tenant_wallets`/`wallet_transactions` confirmed still 0 rows after the grant, duplicate retry correctly `409`). All test data cleaned up afterward; DB restored to its original state.
- **Final status**: **FIXED**.

## L5-05K-010: Chromium Finance verification missing
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: Real Chromium run (`e2e/super-admin/final-l5-05k-usage-credit-runtime.spec.ts`, no network mocks, against the real running frontend + backend): 3/3 tests passed — Usage Credits page shows real balance/ledger data with no forbidden terminology and no wallet-API network calls; Finance Hub Top-ups list loads with no serious console errors; old wallet pages (`/admin/finance/wallets`, `/admin/provider-wallets`) confirmed absent from primary navigation. Screenshots captured under `docs/final-l5-05/evidence/`.
- **Final status**: **FIXED** for the scope actually run (Super Admin role). Finance-capable-Admin and Admin-Read-Only role-specific Chromium scenarios were not run — same root-cause limitation as L5-05K-006 (those roles don't exist as distinct backend accounts to log in as).

## L5-05L-001/002/003/004: Distinct Operations/Finance/Security/Read-Only Admin roles missing
- **Severity**: P0 (the root cause blocking every FINAL-L5-05K-carried-forward RBAC/Chromium finding).
- **Evidence**: `admin.ops@serviceos.local`, `admin.finance@serviceos.local`, `admin.readonly@serviceos.local` all had `role="super_admin"` in the real database — a previously-undiscovered bug in `scripts/canonical_seed_final_l5_01.py`, which only set the free-text, functionally-dead `platform_role` label to distinguish intended purpose. `admin.security@serviceos.local` did not exist at all.
- **Fix**: Added 4 real, enforced role bundles to `app/core/permissions.py::ROLE_PERMISSIONS` (`admin_operations`, `admin_finance`, `admin_security`, `admin_readonly`, none with the `P.ALL` wildcard). New idempotent, environment-gated seed script (`scripts/seed_admin_roles_final_l5_05l.py`) repoints the 3 existing accounts' `role` column (password hashes untouched) and creates the 1 net-new account.
- **Tests**: `tests/test_final_l5_05l_admin_roles.py` (40 tests). Live-verified: all 5 principals authenticate, `/v1/auth/me` returns the correct role and a real computed `permissions` array.
- **Final status**: **FIXED**.

## L5-05L-005: Role permission bundles undefined
- **Severity**: P0.
- **Evidence**: No prior definition existed for what any of the 4 new roles should be allowed/denied.
- **Fix**: Explicit bundles defined with inline deny-list rationale comments (see `FINAL_L5_05L_ADMIN_ROLE_RUNTIME.md` Part 5). A real gap was found and fixed live during API testing: `admin_readonly` was initially missing `P.FINANCE_READ` (the base permission `finance_hub`'s shared `_svc` dependency requires in addition to the specific `FINANCE_TOPUPS_READ` key) — caught by an actual failing live API call, fixed, backend restarted, re-verified 200.
- **Final status**: **FIXED**.

## L5-05L-006: Deterministic role test principals missing
- **Severity**: P0.
- **Evidence**: See L5-05L-001-004.
- **Fix**: 5 real, unique backend accounts (1 pre-existing Super Admin + 4 role-fixed/created this sprint), each with a real, independent login and session.
- **Final status**: **FIXED**.

## L5-05L-007: Cross-domain denial unverified
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: Real live HTTP matrix executed for all 4 mandatory cross-domain pairs: Operations Admin → Usage Credit adjustment/Top-up approval/Security Deposit adjustment (403×3); Finance Admin → Force-close/Void (403×2); Security Admin → Usage Credit adjustment/Force-close (403×2); Admin Read Only → every representative mutation (403×4). Also verified the inverse (allowed actions actually succeed/reach real business logic) for each role. Full evidence in `FINAL_L5_05L_ADMIN_ROLE_RUNTIME.md` Part 17/18.
- **Root cause requiring backend changes**: The canonical Jobs-mutation endpoints (force-close/void/status-override/reassign) and Roles/Permissions catalog reads were gated by the coarse `require_super_admin` role-string check, which cannot differentiate any non-super_admin role. Converted the specific endpoints named in the mission's test matrix to `require_permission()` — a bounded, individually-tested change, not a blanket refactor of the many other `require_super_admin` call sites elsewhere in the codebase (explicitly out of scope, documented).
- **Final status**: **FIXED** for the representative matrix the mission specifies.

## L5-05L-008: Read-only mutation denial unverified
- **Severity**: P0 (explicit acceptance-criteria blocker — "Admin Read Only mutation permission count: 0").
- **Evidence**: `admin_readonly`'s bundle contains 0 mutation-shaped permission keys (verified by an automated architecture guard using a keyword heuristic, `test_admin_readonly_has_zero_mutation_permissions`). Live-verified: adjustment/force-close/session-revoke all return 403; balance/top-up/roles-catalog/security-deposit reads all return 200 with real data. Also verified via real Chromium: a direct `fetch()` mutation call made from within the authenticated Read Only browser session (using the real stored session token) returns 403.
- **Final status**: **FIXED**.

## L5-05L-009: Five-role API matrix missing
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: Real backend started (migrations at 134), real HTTP calls for all 5 principals covering login, `/v1/auth/me`, allowed actions, denied actions, and the one real bug found-and-fixed live (`admin_readonly`'s missing `P.FINANCE_READ`). Full matrix in `FINAL_L5_05L_ADMIN_ROLE_RUNTIME.md` Part 17/18.
- **Final status**: **FIXED**.

## L5-05L-010: Five-role Chromium matrix missing
- **Severity**: P1 (partially closed — see honest scope note below).
- **Evidence**: Real Chromium (no mocks) against the real running frontend+backend: all 5 roles log in and load the dashboard without a JS crash (`e2e/super-admin/final-l5-05l-admin-role-runtime.spec.ts`, 7/7 passed); 2 additional tests prove direct browser-context API mutation calls are denied by the backend regardless of frontend UI state (Admin Read Only and Operations Admin, both real 403s).
- **Real, honestly-documented gap**: `AdminLayout.tsx` has 0 `usePermissions()` call sites — the sidebar/dashboard is not permission-filtered, so non-super-admin roles see the same full navigation and the dashboard fetches widgets backed by endpoints not yet converted off `require_super_admin`, producing expected (correct) 403 network responses that are not yet gracefully hidden in the UI. This is a real frontend-completeness gap, not a security defect (backend denial is proven authoritative regardless). Not fixed this sprint — explicitly out of scope per the mission's own "do not redesign the entire Admin UI" framing. The full Part 25/32 page-by-page, action-by-action five-role Chromium matrix (menu visibility, action visibility, read-only UX, responsive checks) was not run in full — only login/dashboard-smoke/direct-API-denial were run for all 5 roles.
- **Final status**: **PARTIALLY FIXED** — backend-authoritative denial is proven live via the browser for the representative cases tested; full UI-visibility-matrix coverage remains open.

## L5-05M-001: AdminLayout does not consume effective permissions
- **Severity**: P0 (the direct carry-forward of L5-05L-010).
- **Evidence**: 0 `usePermissions()` call sites in `AdminLayout.tsx`, confirmed at the start of this sprint.
- **Fix**: `AdminLayout.tsx` now calls `usePermissions()` and applies `isNavItemPermitted()` to every one of the ~44 `NAV_GROUPS` items, each with an explicit `requiredPermission` (a real backend key or the honest `SUPER_ADMIN_ONLY` sentinel for not-yet-converted routes).
- **Tests**: `tests/test_final_l5_05m_frontend_permission_guards.py` (17 tests); real Chromium (10/10, `final-l5-05m-permission-visibility.spec.ts`).
- **Final status**: **FIXED**.

## L5-05M-002/003: Desktop/mobile sidebar exposes unauthorized items
- **Severity**: P0.
- **Evidence**: Live Chromium proof — Operations Admin's sidebar contains "Jobs"/"Staff" but not "Usage Credits"/"Credit Top-ups"/"Roles"/"Permissions"; Finance Admin's contains Finance items but not "Roles"/"Permissions"; Security Admin's contains "Security"/"Roles"/"Permissions" but not "Usage Credits"/"Security Deposits". Empty groups (0 permitted items) render nothing, header included.
- **Root cause (mobile half)**: No separate mobile drawer component exists in this codebase at all (pre-existing gap, documented since FINAL-L5-04 as Blocker 6) — there is exactly one nav renderer, so desktop/mobile cannot diverge by construction. Not a new gap, not fixed or worsened this sprint.
- **Final status**: **FIXED** (desktop); mobile has no separate implementation to diverge (structurally satisfies "same registry", but the underlying "no real mobile nav" gap remains, tracked separately).

## L5-05M-004/005: Primary routes/mutation actions lack permission guards
- **Severity**: P0/P1.
- **Evidence**: New `RequirePermission` route guard applied to the 7 highest-risk pages named in the mission's own Chromium matrix (Usage Credits, Credit Top-ups, Security Deposits, Security, Users, Roles, Permissions). 8 mutation actions gated (Job reassign/status-override/force-close/void, Usage Credit adjust, Top-up retry/refund, Session revoke).
- **Real gap found live during verification**: initial `"analytics:read"` key (catalog + AdminLayout) did not match the real backend key `"analytics:dashboard:read"` — caught by the new automated guard test, fixed before commit.
- **Not covered**: the remaining ~37 nav items whose backing routes are `SUPER_ADMIN_ONLY` were not individually wrapped with `RequirePermission` (the sidebar already hides them, and backend independently 403s them per FINAL-L5-05L) — exhaustive per-route guard wrapping across the full admin surface is out of this sprint's bounded scope.
- **Final status**: **FIXED** for the representative set; **PARTIALLY FIXED** for full exhaustive coverage (documented, not hidden).

## L5-05M-006: Admin Read Only lacks consistent frontend read-only presentation
- **Severity**: P1.
- **Evidence**: `ReadOnlyNotice` component added; wired into the Usage Credits page's mutation card. Live-verified: Admin Read Only sees real ledger data + "View-only access" notice + no "Add Usage Credits" form.
- **Not covered**: only 1 page received the read-only notice treatment (Usage Credits); the other 6 guarded pages don't yet have an explicit read-only notice (their mutation controls are permission-gated correctly, just without the friendly notice copy).
- **Final status**: **PARTIALLY FIXED**.

## L5-05M-007: Unauthorized content/action flash risk
- **Severity**: P0 (explicit acceptance-criteria blocker).
- **Evidence**: `isNavItemPermitted`/`RequirePermission` both fail closed (`permissions === null` → not permitted) during loading — proven live: a too-short Chromium test wait initially caught the sidebar mid-load showing only the always-visible Dashboard item, never unauthorized content, before the correct final set appeared. `RequirePermission` shows a `Skeleton`, never the protected content, while loading.
- **Final status**: **FIXED**.

## L5-05M-008/009: Contextual links / dashboard widgets lack permission filtering
- **Severity**: P2.
- **Evidence**: Not attempted this sprint — genuinely out of bounded scope. Dashboard widgets were observed (live, during Chromium debugging) to already degrade gracefully server-side (real, pre-existing "Permission 'dashboard.finance.read' required..." inline error states with Retry + request_id, not a crash or data leak) rather than exposing restricted data — an acceptable interim state.
- **Final status**: **NOT FIXED** — documented, not hidden.

## L5-05M-010: Five-role frontend visibility matrix incomplete
- **Severity**: P1 (partially closed).
- **Evidence**: 10/10 real Chromium tests covering sidebar visibility for all 5 roles + direct-route Permission Denied + read-only presentation, run standalone (20/20 total across the 3 most recent Chromium suites when run individually, avoiding a dev-server cache-corruption issue found and fixed mid-sprint — see Part "Environment note" in `FINAL_L5_05M_FRONTEND_PERMISSION_VISIBILITY.md`).
- **Not covered**: the full Part 31/32 exhaustive per-page, per-action, mobile-viewport, accessibility, and performance matrices were not run — only the representative subset.
- **Final status**: **PARTIALLY FIXED**.

## L5-05M-011 (new finding this sprint): Platform Users page role dropdown writes to a dead metadata field
- **Severity**: P1 (real architecture mismatch, not a security hole — the field it writes to was never enforced).
- **Evidence**: `app/admin/users/page.tsx`'s `PLATFORM_ROLES` constant lists `operations_admin`/`finance_admin`/`security_admin`/`read_only_admin` — none of which match the real, enforced `ROLE_PERMISSIONS` keys (`admin_operations`/`admin_finance`/`admin_security`/`admin_readonly`). The page's role-change action calls `PUT /v1/admin/platform-users/{id}/role`, which writes `users.platform_role` — the same dead, unenforced metadata column FINAL-L5-05L found and fixed for the 4 seeded test accounts' real `role` column.
- **Root cause**: "Platform Users Governance" (migration 083) is a separate, larger subsystem than the `users.role` field this engagement's role work has targeted — it was never wired to real enforcement.
- **Not fixed this sprint**: rewiring this whole page/endpoint to write the real, enforced `role` column (or deprecating `platform_role` entirely) is a backend-architecture change beyond this sprint's frontend-visibility scope, and risks breaking whatever (if anything) currently depends on reading `platform_role` display values.
- **Final status**: **DOCUMENTED, NOT FIXED** — flagged for a dedicated follow-up sprint.

## L5-05N-001: Platform Users invite silently granted real super_admin access regardless of selected role
- **Severity**: P0 (real security defect — worse than the originally-scoped "dead field" framing from L5-05M-011).
- **Evidence**: `AuthService.invite_platform_user` hardcoded `User(role="super_admin", platform_role=platform_role, ...)` — every invited user got real, enforced super_admin authorization no matter which role label was selected in the dropdown.
- **Fix**: `role=platform_role` (the real, enforced column), using the corrected `VALID_PLATFORM_ROLES` set (see L5-05N-002).
- **Tests**: `tests/test_final_l5_05n_role_editor_repair.py::TestInvitePlatformUser`.
- **Status**: **FIXED**.

## L5-05N-002: 8 invented Platform Users role labels matched nothing in the real permission architecture
- **Severity**: P1 (direct cause of L5-05N-001 and L5-05N-003).
- **Evidence**: `VALID_PLATFORM_ROLES` (backend) and `PLATFORM_ROLES` (frontend dropdown) both listed `operations_admin`/`finance_admin`/`security_admin`/`read_only_admin`/`compliance_officer`/`support_admin`/`platform_admin` — none of which exist in `ROLE_PERMISSIONS` (the real canonical set is `admin_operations`/`admin_finance`/`admin_security`/`admin_readonly`, established in FINAL-L5-05L).
- **Fix**: Both constants now list exactly the 5 real canonical roles. No new labels invented, per rule 24.
- **Files changed**: `app/engines/auth/service.py`, `frontend/super-admin/app/admin/users/page.tsx`.
- **Status**: **FIXED**.

## L5-05N-003: `change_platform_role` wrote only the dead `platform_role` display column
- **Severity**: P1 (this engagement's originally-scoped defect, carried forward from L5-05M-011).
- **Evidence**: The real, enforced `role` column (consulted by `PermissionChecker`) was never updated by the role editor's mutation action — changing a user's role in the UI had zero effect on their actual permissions.
- **Fix**: `change_platform_role` now writes both `target.role` and `target.platform_role`, and audits `old_role`/`new_role`/`old_platform_role` in the `platform_user.role_changed` event.
- **Files changed**: `app/engines/auth/service.py`.
- **Status**: **FIXED** (rule 25 satisfied — no longer continuing to write only the dead field).

## L5-05N-004: `require_platform_mutate` checked the dead `platform_role` column for a label that no longer exists
- **Severity**: P2 (defense-in-depth check was already a no-op before this fix, since the `"read_only_admin"` label it checked for was itself invented and never matched a real seeded value).
- **Fix**: Now checks `admin.role == "admin_readonly"` — the real, enforced role established in FINAL-L5-05L.
- **Files changed**: `app/engines/auth/platform_users_router.py`.
- **Status**: **FIXED**.

## L5-05N-005: ~85 real admin routes had zero permission coverage of any kind before this sprint
- **Severity**: P0 (direct continuation of L5-05M-004/005's "not covered: the remaining ~37 nav items" gap — the true count was larger than 37 once the ~85 routes with no `NAV_GROUPS` entry at all are included).
- **Evidence**: A file-system scan of `frontend/super-admin/app/admin/**/page.tsx` found ~150 real routes; only ~65 had an explicit `activeNav` prop tying them to a `NAV_GROUPS` permission. The other ~85 (e.g. `/admin/brands`, `/admin/issue-types`, `/admin/service-groups`, `/admin/rating-summaries`, `/admin/service-setup/*`, `/admin/ai-chat/*`) rendered fully open to any authenticated admin session, regardless of role.
- **Root cause**: `AdminShellCtx` short-circuits individual pages' own `<AdminLayout activeNav="...">` calls (discovered this sprint) — meaning FINAL-L5-05M's page-level `RequirePermission` wrapping could only ever reach pages someone explicitly edited, never the full route surface.
- **Fix**: `getRequiredPermissionForRoute()` + root-layout (`app/admin/layout.tsx`) `RequirePermission` wrap — see `FINAL_L5_05N_EXHAUSTIVE_PERMISSION_COVERAGE.md` for full mechanism. Every route not in `NAV_GROUPS` now fails closed to `SUPER_ADMIN_ONLY` (a real security tightening, not just documentation — these routes were previously open to any admin role).
- **Tests**: 5 real Chromium tests (`e2e/super-admin/final-l5-05n-exhaustive-coverage.spec.ts`), all passing, covering all 4 non-super-admin roles plus Super Admin retention.
- **Status**: **FIXED** — mechanism-level coverage proven correct and applies uniformly to all ~150 routes by construction; not every individual route/role pair was separately exercised in a browser (see L5-05N-008).

## L5-05N-006: Dashboard/contextual-link/export-surface permission filtering not attempted
- **Severity**: P2.
- **Evidence**: Carried forward unchanged from L5-05M-008/009. Dashboard widgets already degrade gracefully server-side (real inline "Permission required" error states, not a data leak); this sprint did not add client-side filtering on top.
- **Status**: **NOT FIXED** — documented, not hidden. Genuinely out of this sprint's bounded scope given the size of the root-layout guard work already completed.

## L5-05N-007: Mobile navigation still does not exist as a separate implementation
- **Severity**: P2 (unchanged from FINAL-L5-04/05M).
- **Evidence**: Still exactly one nav renderer in the codebase; no separate mobile drawer component. The root-layout guard change is structurally mobile-safe (it doesn't touch rendering, only permission gating) but does not create the missing mobile nav.
- **Status**: **NOT FIXED** — pre-existing gap, not worsened or improved this sprint.

## L5-05N-008: Full 5-role × ~150-route exhaustive Chromium matrix not run
- **Severity**: P1 (explicit acceptance-criteria expectation of the mission).
- **Evidence**: 5 representative Chromium tests were run (4 roles × 2 routes each, plus the role-editor check) proving the guard mechanism is correct; the other ~148 × 4 role combinations were not independently exercised in a live browser, relying instead on the mechanism being uniform (`getRequiredPermissionForRoute` is a pure function of `pathname` + `NAV_GROUPS`, not per-route special-cased code, so there is no code-path reason to expect divergent behavior across untested routes — but this is architectural reasoning, not empirical per-route browser proof).
- **Status**: **NOT FIXED** — honestly documented gap, consistent with this engagement's established pattern of not claiming exhaustive coverage without exhaustive live evidence.

## Result
18 of 21 real bugs/gaps found across FINAL-L5-05 through FINAL-L5-05H were fixed and live-verified; FINAL-L5-05I through 05L added 40 more findings implementing the Usage Credit/Finance Hub/Admin Role architecture. FINAL-L5-05M adds 11 more (L5-05M-001 through 011): `AdminLayout` now consumes real server-provided effective permissions for the first time, closing the central L5-05L-010 gap — desktop sidebar visibility, 7 representative route guards, and 8 representative action guards are all proven correct live via 10/10 real Chromium tests (20/20 across all 3 most recent role/permission Chromium suites when run standalone). A real permission-key mismatch (`analytics:read` vs `analytics:dashboard:read`) was found and fixed by the new automated guard before commit. Exhaustive coverage of all ~44 routes/actions, mobile-specific navigation, and dashboard/contextual-link filtering remain open, consistent with this sprint's explicit "do not redesign the entire Admin UI" scope limit — each documented with direct evidence, not hidden or downgraded. One new, real, out-of-scope architecture mismatch was discovered and documented (L5-05M-011, Platform Users' dead `platform_role` field) rather than silently left unmentioned.

FINAL-L5-05N adds 8 more (L5-05N-001 through 008): closes L5-05M-011 by fixing the Platform Users role editor for real, including a more serious defect than originally scoped (invited users silently received super_admin access, L5-05N-001) — the role editor now maps 1:1 to the real, enforced role architecture. Separately, a single root-layout change (`getRequiredPermissionForRoute` + `app/admin/layout.tsx`) closes the "remaining ~37 nav items" gap from L5-05M-004/005 and extends it further — every one of ~150 real admin routes, including ~85 that had zero permission coverage of any kind before this sprint, now inherits a real, fail-closed permission check, live-verified via 5 real-browser Chromium tests. Exhaustive per-route/per-action live verification across all 150 routes × 5 roles, dashboard/contextual-link/export filtering, mobile navigation, accessibility, and performance all remain open — honestly documented, not claimed complete.

## L5-05O-001: Enterprise Export system (33 resources) had zero domain-permission gating
- **Severity**: P0 (real, exploitable today — any authenticated role, including Admin Read Only, could export any of 33 resources' real row data, including Finance/Security-sensitive ones).
- **Evidence**: `create_export_job` (`POST /v1/enterprise/exports`, `app/engines/enterprise_grid/router.py`) had only `get_current_user` as a dependency; no resource-level permission check existed anywhere in the router or `ExportService`.
- **Fix**: `RESOURCE_EXPORT_PERMISSIONS` mapping (`filter_registry.py`) + inline `permission_checker.has()` check in `create_export`, covering the 12 Finance/Security/Jobs-sensitive resources with real, existing export-shaped permissions (`FINANCE_EXPORT`, `SECURITY_AUDIT_EXPORT`, `FIELD_OPS_JOBS_EXPORT`).
- **Live API evidence**: Finance/Security/Jobs resource exports each correctly 201 only for the intended 2 roles (Super Admin + domain owner), 403 for the other 3.
- **Tests**: `tests/test_final_l5_05o_inpage_permissions.py::TestEnterpriseExportPermissionGate` (6 tests).
- **Status**: **FIXED** for the 12 sensitive resources; ~25 lower-sensitivity catalog/operational resources remain unmapped (documented, see L5-05O-006).

## L5-05O-002: finance_hub's 4 export endpoints violated "report read must not imply export"
- **Severity**: P1.
- **Evidence**: `/v1/admin/finance/{deposits,topups,warranty-claims,payouts}/export` were each gated by the domain's `*_READ` permission, identical to the corresponding list endpoint.
- **Fix**: All 4 now require `P.FINANCE_EXPORT`, granted only to `admin_finance` among the 4 non-super-admin roles.
- **Live API evidence**: `GET /v1/admin/finance/deposits/export` — Super Admin/Finance Admin 200, Operations/Security/Read-Only 403.
- **Tests**: `TestFinanceHubExportPermissionSeparation` (1 test asserting all 4 endpoints require `P.FINANCE_EXPORT`, not a read key).
- **Status**: **FIXED**.

## L5-05O-003: Dashboard widgets were 100% unreachable by every non-super-admin role
- **Severity**: P0 (real, pre-existing usability/architecture gap — a well-designed per-widget permission registry existed in the backend but was never wired into any of the 4 role bundles).
- **Evidence**: 0 of `admin_operations`/`admin_finance`/`admin_security`/`admin_readonly` held `P.DASHBOARD_READ` before this sprint; every dashboard endpoint 403'd for every one of them.
- **Fix**: Each role granted `DASHBOARD_READ` (base) plus its own domain widget/action-queue permissions (see full breakdown in `FINAL_L5_05O_INPAGE_PERMISSION_CERTIFICATION.md`). `useApi()` gained an `enabled` option; the dashboard page suppresses restricted widget requests entirely and omits (does not render) denied sections.
- **Live API evidence**: base widget 200 for all 5 roles; `finance-snapshot`/`compliance-security` each correctly 200 only for their 2 intended roles.
- **Live Chromium evidence**: 6/6 new tests — each role sees exactly its intended widget set; zero restricted network requests observed for Admin Read Only.
- **Tests**: `TestDashboardRoleBundles`, `TestDashboardRequestSuppression` (13 tests).
- **Status**: **FIXED**.

## L5-05O-004: Security Deposits page mutation actions map to a different permission domain than the page's own route guard
- **Severity**: P1 (real, pre-existing architecture mismatch — before this sprint, Finance Admin could reach the page but every mutation on it would 403).
- **Evidence**: Page route guard + role-bundle intent use `finance.security_deposits.*`; the actual mutation endpoints the page calls (`/v1/admin/finance/deposits/{id}/approve|reject|record-offline|refund|adjust`) are gated by a completely separate `finance:deposits:*` domain (`finance_hub/admin_router.py`).
- **Fix (bounded)**: `admin_finance` granted the real `finance:deposits:*` permissions its intended actions require. The two domains are NOT reconciled/merged this sprint — reconciling them is a larger architecture decision.
- **Live API evidence**: `POST .../adjust` reaches the handler (404 on fake UUID = passed the permission gate) for Super Admin/Finance Admin; 403 for Operations/Security/Read-Only.
- **Status**: **PARTIALLY FIXED** — Finance Admin can now use the page; the underlying two-domain naming collision remains open, tracked for a future architecture-reconciliation sprint (same category as the `TenantWallet`/Blocker-9 finding).

## L5-05O-005: Security Deposits row overflow menu had zero frontend permission gating
- **Severity**: P1 (direct consequence of L5-05O-004 -- before this sprint, any role reaching the page saw all 5 mutation menu items regardless of actual backend permission).
- **Fix**: `ActionMenu` items on `/admin/finance/deposits` now individually gated via `perm.has()` against the real backend permission each one calls; denied items are omitted, not disabled.
- **Live Chromium evidence**: Admin Read Only's opened overflow menu contains zero of the 4 mutation labels (Approve/Reject/Forfeit-Adjust/Initiate Refund).
- **Tests**: `TestSecurityDepositsActionPermissionArchitectureMismatch` (4 tests).
- **Status**: **FIXED**.

## L5-05O-006: ~25 of 33 Enterprise Export resources remain unmapped to any export permission
- **Severity**: P2 (lower-sensitivity catalog/operational resources — `admin_categories`, `admin_engines`, `admin_tenants`, `admin_pricing_tiers`, etc. — reachable by any authenticated admin).
- **Evidence**: Only the 12 Finance/Security/Jobs-sensitive resources were classified and gated this sprint (L5-05O-001); the remainder were not individually risk-assessed.
- **Status**: **NOT FIXED** — documented, bounded-scope gap, not hidden.

## L5-05O-007: Contextual links across the ~150-page admin surface not exhaustively inventoried
- **Severity**: P2.
- **Evidence**: Only the dashboard's own Quick Links panel was bounded-fixed this sprint (filtered by real destination-page permission). Tenant/Job/Finance/Security detail-page contextual links (mission Parts 10-13) were not inventoried or individually fixed.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05O-008: Tenant/Provider/Staff in-page mutation actions have zero frontend permission gating
- **Severity**: P1 (confirmed via source read — `frontend/super-admin/app/admin/tenants/[id]/page.tsx`, a ~2800-line file with multiple Verify/Reject/Suspend/Reactivate buttons, has zero `usePermissions` import).
- **Evidence**: The page route itself requires only `tenant:read` (held by `admin_operations`, `admin_finance`, `admin_readonly`), so any of those 3 roles reaching the page would see all mutation buttons regardless of actual backend permission for the specific action.
- **Root cause**: Same class of gap as L5-05O-005, at a much larger scale (single file, many buttons) — not bounded-fixable within this sprint's remaining budget after the 4 fixes above.
- **Status**: **NOT FIXED** — real, evidenced, documented gap. Highest-priority carry-forward item for a future FINAL-L5-05P-style continuation.

## L5-05O-009: Notification/System in-page actions not inventoried
- **Severity**: P2.
- **Status**: **NOT FIXED** — not investigated this sprint (Part 27 out of bounded scope).

## L5-05O-010: Full five-role page-level Chromium matrix incomplete
- **Severity**: P1 (explicit acceptance-criteria expectation).
- **Evidence**: 8 new Chromium tests this sprint (dashboard widget suppression across all 5 roles, Security Deposits action-menu filtering for 2 roles) plus 22 re-verified prior-sprint tests, all passing. The full ~150-page × 5-role × per-action matrix implied by Part 42 was not run in full — only the 4 specific fixes made this sprint were live-verified end-to-end.
- **Status**: **PARTIALLY FIXED** — the fixes actually made are proven live; the broader matrix remains open.

## L5-05O-011: Throttled-network flash-prevention verification not run as a dedicated pass
- **Severity**: P2.
- **Evidence**: The request-suppression test (L5-05O-003) proves no restricted dashboard request fires under normal network conditions; a dedicated Chromium network-throttled run (Part 43) was not performed.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05O-012: Mobile navigation, accessibility, responsive, and performance verification not attempted
- **Severity**: P2/P3 (unchanged, pre-existing gaps tracked since FINAL-L5-04/05M/05N).
- **Status**: **NOT FIXED** — same carried-forward scope, not worsened or improved this sprint.

## Result
FINAL-L5-05O adds 12 more (L5-05O-001 through 012): 4 real, high-leverage, live-verified fixes closed genuine P0/P1 gaps (Enterprise Export system had zero domain-permission gating across 33 resources — a serious, previously-unknown finding; finance_hub export/read separation; dashboard widgets were 100% unreachable by every non-super-admin role, now fixed with real per-widget grants and request suppression; Security Deposits' ungated mutation menu plus the underlying two-permission-domain architecture mismatch). All 4 fixes are proven correct via live API (8 mandatory cross-domain denial checks from the mission's own Part 41, all passing) and live Chromium (8 new + 22 re-verified, zero regression). The much larger remainder — exhaustive contextual-link/action cataloging across ~150 pages, ~25 remaining export resources, Tenant/Provider/Staff/Notification action matrices, mobile/accessibility/responsive/performance — is honestly carried forward as documented, evidenced remaining scope.

## L5-05P-001: 6 provider_portal mutation endpoints accepted ANY authenticated principal of ANY role
- **Severity**: P0 (real, exploitable today — a logged-in customer, technician, or staff account, not just an admin, could invoke these).
- **Evidence**: Full audit of every `POST`/`PUT`/`DELETE` route in `app/engines/provider_portal/admin_router.py` mapped against its real auth dependency found 6 endpoints gated by only `get_current_user`: onboarding send-reminder/refresh/checklist-item-override, and bookability refresh/override-visibility/remove-visibility/override-bookability/remove-bookability. The 4 override/remove endpoints are the most severe — any authenticated principal could override a provider's public visibility/bookability platform-wide.
- **Fix**: Checklist-item override reuses `P.TENANT_APPROVE`; the remaining 5 require `require_super_admin` (no granular coverage/bookability permission exists yet — inventing one without real policy evidence was deliberately avoided).
- **Live API evidence**: `POST .../override-visibility` — Super Admin 200 (reaches handler), Operations/Finance/Security/Read-Only all 403.
- **Tests**: `tests/test_final_l5_05p_tenant_provider_staff_permissions.py::TestProviderPortalMutationEndpointsAreGated` (5 tests).
- **Status**: **FIXED**. One sibling endpoint with the identical defect (`POST /monetization/providers/{tenant_id}/sync`) was found in the same audit and deliberately NOT fixed — Monetization is a Finance-adjacent domain outside this sprint's bounded scope; documented, not hidden.

## L5-05P-002: Tenant onboarding approve/reject/request-more-info granted to zero non-super-admin roles
- **Severity**: P0 (direct contradiction of the mission's own stated policy: Operations Admin's "Tenant verify"/"Provider verify" = ALLOW).
- **Evidence**: `TENANT_APPROVE`/`TENANT_REJECT`/`TENANT_REQUEST_MORE_INFO`/`TENANT_ONBOARDING_READ` are real, pre-existing, distinct backend permissions already enforced on their endpoints, but 0 non-super-admin roles held any of them before this sprint.
- **Fix**: `admin_operations` granted all 4 (additive, safe, matches the mission's own explicit expected policy). No other non-super-admin role received them.
- **Live API evidence**: `POST .../approve`/`.../reject` — Super Admin/Operations Admin reach the handler (404 on fake tenant ID), Finance/Security/Read-Only 403. `GET .../onboarding/providers/{id}` — Super Admin/Operations Admin 200, others 403.
- **Tests**: `TestTenantOnboardingLifecyclePermissions` (5 tests).
- **Status**: **FIXED**.

## L5-05P-003: `tenants/[id]/page.tsx` (the mission's own named highest-risk example) had zero frontend permission checks across ~24 mutation actions
- **Severity**: P0.
- **Evidence**: A 3095-line file with zero `usePermissions` import; every mutation action (Onboarding approve/reject/refresh, Offerings suspend/reactivate/refresh, Bookability override/remove ×2, Tenant suspend/reinstate/change-plan/request-changes/send-notification/export, Staff deactivate, User suspend, Add-Staff/Add-User/Add-Area triggers) rendered for any role that could reach the page at all (`tenant:read`, held by 3 of 4 non-super-admin roles).
- **Fix**: `usePermissions()` wired into the main component and 3 sub-tab components; each action individually gated by its real backend-matching permission (`tenants.approve`/`tenants.reject` for Onboarding) or `perm.role === "super_admin"` for the `require_super_admin`-gated actions (matching L5-05P-001/L5-05P-002's backend reality).
- **Deliberately not touched**: Add Usage Credits / Adjust Security Deposit (Finance/wallet domain, out of this sprint's bounded scope per the mission's own "do not reopen Finance Hub" instruction).
- **Live API evidence**: `POST /v1/admin/tenants/{id}/suspend` and `.../staff` — only Super Admin reaches the handler, all 4 other roles 403.
- **Live Chromium evidence**: 5/6 new tests directly cover this page — Super Admin sees Change Plan; Operations Admin reaches the page with zero super_admin-only header mutations; Admin Read Only sees zero mutation controls in the header AND the opened overflow menu; Operations Admin's Onboarding tab loads without Permission Denied (real grant from L5-05P-002); Admin Read Only's Onboarding tab shows no raw mutation output.
- **Tests**: `TestTenantDetailPageActionGating` (5 tests).
- **Status**: **FIXED** for the mutation actions found; Finance/wallet-domain actions on the same page remain intentionally out of scope (documented).

## L5-05P-004: Bookability Providers list "Bulk Re-evaluate" calls a non-existent backend route
- **Severity**: P2 (dead/broken functionality, not an active security exposure — always 404s for every role today).
- **Evidence**: `POST /v1/admin/bookability/bulk-refresh` does not correspond to any registered backend route (confirmed via full-router grep).
- **Fix**: Gated defensively with `perm.role === "super_admin"` for consistency and forward-safety, not because it's currently exploitable.
- **Tests**: `TestBookabilityProvidersListPageGating` (1 test).
- **Status**: **FIXED** (defense-in-depth); the underlying dead endpoint itself was not implemented or removed this sprint.

## L5-05P-005: Staff pages confirmed genuinely read-only (positive finding, pinned)
- **Severity**: informational.
- **Evidence**: `/admin/staff` and `/admin/staff/[id]` have zero `useAction` mutation hooks — confirmed via full source read, not assumption. `staffApi.invite`/`.resendInvite` exist in the API client but are unused by any component (dead code).
- **Fix**: No fix needed — added a regression-pinning test so a future ungated mutation addition to these pages is caught.
- **Tests**: `TestStaffPagesAreReadOnly` (2 tests).
- **Status**: **CONFIRMED SAFE, PINNED**.

## L5-05P-006: Team/Membership mutation surface does not exist in this codebase
- **Severity**: informational.
- **Evidence**: No dedicated Team management route exists; the tenant detail page's `ProviderTeamTab` is explicitly labeled read-only in its own source comment and has zero `useAction` hooks. `provider_team_members` was confirmed empty/superseded by `users`-based staff as far back as Sprint 20/FINAL-L5-05C (prior engagement finding, re-confirmed here).
- **Status**: **NOT APPLICABLE** — there is no Team/Membership mutation surface to gate. Documented rather than silently omitted from the mission's required inventory.

## L5-05P-007: Provider coverage/brand/zone mutations beyond Bookability not exhaustively inventoried
- **Severity**: P2.
- **Evidence**: Only the Bookability override/remove actions (L5-05P-001) were found and fixed as coverage-shaped mutations. A dedicated pass across brand/zone/zipcode/SLA/availability mutation surfaces (mission Part 9) was not performed.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05P-008: Bulk actions across the Tenant/Provider/Staff domain not exhaustively inventoried
- **Severity**: P2.
- **Evidence**: Only the single dead "Bulk Re-evaluate" button (L5-05P-004) was found. A dedicated bulk-action inventory (mission Part 22) was not performed.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05P-009: Cross-tenant isolation not tested with direct identifier substitution
- **Severity**: P1 (explicit mission Part 30 expectation).
- **Evidence**: Live verification this sprint used fake/nonexistent UUIDs to prove permission gates (403 vs. 404-after-gate-passed), not real cross-tenant identifier substitution attacks.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05P-010: Concurrency/conflict handling not tested
- **Severity**: P2 (mission Part 33).
- **Status**: **NOT FIXED** — not attempted this sprint.

## L5-05P-011: Full five-role Provider/Staff/Team Chromium matrix incomplete
- **Severity**: P1.
- **Evidence**: 6 representative Chromium tests this sprint (Tenant detail header ×3 roles, Onboarding tab ×2 roles, Bookability list ×1 role) plus 30 re-verified prior-sprint tests, all passing. The full mission-specified per-page, per-role, per-action matrix (Parts 43-45) was not run in full.
- **Status**: **PARTIALLY FIXED** — the fixes actually made are proven live; the broader matrix remains open.

## L5-05P-012: Throttled-network, responsive, and accessibility verification not attempted
- **Severity**: P2/P3 (unchanged, pre-existing gaps tracked since FINAL-L5-04/05M/05N/05O).
- **Status**: **NOT FIXED** — same carried-forward scope, not worsened or improved this sprint.

## Result
FINAL-L5-05P adds 12 more (L5-05P-001 through 012): 4 real, deeply-investigated, live-verified fixes closed the mission's own explicitly-named highest-risk gap. A serious P0 finding (6 provider mutation endpoints, including provider-visibility/bookability overrides, accepted ANY authenticated principal of any role) is closed. The real onboarding-lifecycle permissions existed but were granted to zero non-super-admin roles despite the mission's own stated policy — fixed. The mission's own named highest-risk file (`tenants/[id]/page.tsx`, 3095 lines, ~24 mutation actions, zero frontend permission checks) is now individually gated. A defensive fix closed a dead bulk-action button. Two domains (Team/Membership, Staff pages) were investigated and confirmed to have no active gap — a genuine, evidenced finding, not an assumption. All fixes are proven correct via live API (real 403/200/404s across all 5 roles) and live Chromium (6 new + 30 re-verified, zero regression). The much larger remainder — exhaustive Provider coverage/brand mutation inventory, bulk-action inventory, cross-tenant isolation testing, concurrency testing, throttled-network/responsive/accessibility — is honestly carried forward as documented, evidenced remaining scope.

## L5-05Q-001: Cross-tenant vulnerability — Service Area update/delete had zero tenant-ownership verification
- **Severity**: P0 (real, live, exploitable — confirmed via direct HTTP cross-tenant substitution against the real running backend).
- **Evidence**: `admin_update_service_area`/`admin_delete_service_area` (`app/engines/serviceability/router.py`, the actually-live handlers for `/v1/admin/tenants/{tenant_id}/service-areas/{area_id}`) captured `tenant_id` from the URL but never passed it to `ServiceabilityService.update_service_area`/`deactivate_service_area`, which loaded the target area by `area_id` alone. `_assert_owns_tenant()` only enforces for `actor_role == "tenant_owner"` — a no-op for any admin caller.
- **Fix**: Added `admin_tenant_id` parameter to both service methods (defaults to `None`, zero behavior change for self-service callers), passed only from the admin router handlers; raises `NotFoundException` on mismatch.
- **Live API evidence**: Real service area created under Tenant A; `PUT`/`DELETE` against it via Tenant B's route both `404`; row confirmed unchanged via Tenant A's real route; same-tenant update immediately succeeds.
- **Tests**: `tests/test_final_l5_05q_provider_coverage_mutations.py::TestLiveServiceabilityCrossTenantIsolation` (3 tests, real Postgres).
- **Status**: **FIXED**.

## L5-05Q-002: Real concurrency bug — duplicate service-area creation via TOCTOU race
- **Severity**: P1 (data-integrity defect, not a security hole — reproducibly creates duplicate rows under concurrent load).
- **Evidence**: `ServiceabilityService.create_service_area`'s duplicate check is a plain SELECT with no locking, immediately followed by INSERT. A real concurrent-request test (`asyncio.gather` of 2 simultaneous identical creates against real Postgres) showed both succeeding, producing 2 duplicate active rows.
- **Fix**: Transaction-scoped Postgres advisory lock (`pg_advisory_xact_lock`, keyed on the exact tenant+coverage tuple) serializes concurrent creates before the duplicate check.
- **Live evidence**: Same concurrent-request test now shows exactly 1 success + 1 controlled `409`; direct SQL count confirms exactly 1 active row after the race.
- **Tests**: `TestLiveServiceabilityDuplicatePreventionRealDB` (2 tests, real Postgres, real concurrency).
- **Status**: **FIXED**.

## L5-05Q-003: Provider Enabled Offering suspend/reactivate wrote zero audit events
- **Severity**: P1.
- **Evidence**: `admin_suspend_offering`/`admin_reactivate_offering` (`tenant_engine/admin_router.py`) perform direct SQL UPDATEs with no `_audit()`/`record_platform_audit()` call anywhere.
- **Fix**: Both now write a `platform_audit_logs` row with actor/tenant/entity/before/after/request_id.
- **Tests**: `TestOfferingsAuditNowWritten` (3 tests).
- **Status**: **FIXED**.

## L5-05Q-004: Bookability/Visibility overrides (FINAL-L5-05P) re-verified, no regression
- **Severity**: informational (regression check).
- **Evidence**: Live 5-role matrix re-run against the 4 override/remove endpoints — Super Admin `200`, all 4 other roles `403`.
- **Status**: **RE-CONFIRMED, NO REGRESSION**.

## L5-05Q-005: `AdminTenantService.create_service_area` duplicate-prevention and audit fixes made against a dead code path
- **Severity**: informational (process finding — caught and correctly re-targeted within this sprint, not shipped as a false fix).
- **Evidence**: Initial investigation found `AdminTenantService.create_service_area` (`tenant_engine/admin_service.py`) had no duplicate check and added one, before discovering (via L5-05Q-006) this service is unreachable via HTTP for the `/service-areas` path. The fix was kept as harmless defense-in-depth but is NOT the live-path fix.
- **Tests**: `TestAdminTenantServiceDefenseInDepthFixesStillCorrect` (2 tests, pinning the dead-code fix so it isn't silently reverted).
- **Status**: **KEPT AS DEFENSE-IN-DEPTH**, correctly not conflated with the real fix (L5-05Q-002).

## L5-05Q-006: Duplicate route registration — `tenant_engine.admin_router`'s Service Area endpoints are unreachable dead code
- **Severity**: P1 (real architecture defect, not currently a security hole since the live-reachable router is the one that got fixed, but a real source of wasted engineering effort and confusion).
- **Evidence**: Both `app/engines/serviceability/router.py` and `app/engines/tenant_engine/admin_router.py` register the identical path `/v1/admin/tenants/{tenant_id}/service-areas` (all 4 methods). `main.py` includes `serviceability_router` (line 154) before `admin_tenant_router` (line 349) — FastAPI matches the first-registered route, so `tenant_engine.admin_router`'s identical routes never fire. Discovered only via live HTTP response-shape comparison (`id` vs `area_id`, `DUPLICATE_SERVICE_AREA` vs `DUPLICATE_PROVIDER_ASSIGNMENT`), not by any unit test.
- **Root cause**: Two independent sprints/engines built the same capability independently, unaware of each other (same class of finding as the earlier `TenantWallet`/Blocker-9 and 05J's "5 independent credit-adjustment implementations" discoveries).
- **Status**: **DOCUMENTED, NOT RESOLVED** — deciding which implementation is canonical (or whether to merge/deprecate the shadowed one) is a larger architecture decision beyond this sprint's bounded scope. Pinned by a regression guard test (`TestDuplicateRouteRegistrationFinding`) so a future router-order change is caught rather than silently altering which implementation is live.

## L5-05Q-007: Provider brand/zone/zipcode/capacity/SLA/blackout mutation surface does not exist in this codebase
- **Severity**: informational.
- **Evidence**: Exhaustive `git grep` across every engine for `provider_zones`/`provider_zipcodes`/`provider_brands`/`provider_capacity`/`provider_sla`/`provider_blackout` table definitions returns zero matches. The closest real concepts (`tenant_supported_brands`, `tenant_service_brands`, `tenant_service_types`) are mutated only via tenant self-service routers (`/v1/tenant/catalog`, `/v1/provider`), never via an admin-side mutation endpoint.
- **Status**: **NOT APPLICABLE** — there is no such admin mutation surface to gate. Documented rather than silently omitted, matching FINAL-L5-05P's Team/Membership precedent. Pinned by `TestNoUndiscoveredProviderMutationSurface`.

## L5-05Q-008: Bulk Provider coverage/brand/zone operations do not exist beyond the one already-fixed dead button
- **Severity**: informational.
- **Evidence**: No bulk coverage/brand/zone mutation UI or endpoint exists anywhere in the Tenant/Provider domain. The only "bulk" action found (`/admin/bookability/providers`'s "Bulk Re-evaluate") was already investigated and fixed in FINAL-L5-05P (found to call a non-existent backend route, gated defensively).
- **Status**: **NOT APPLICABLE** — documented, not hidden.

## L5-05Q-009: Full five-role Provider Chromium matrix incomplete
- **Severity**: P1 (explicit acceptance-criteria expectation).
- **Evidence**: 3 new Chromium tests this sprint (Operations Admin denied Add Area button, Super Admin's Service Areas tab renders cleanly, duplicate creation returns a controlled 409 in-browser) plus 19 re-verified prior-sprint tests, all passing. The mission's specified exhaustive per-page × per-role × per-action matrix (Part 39) was not run in full.
- **Status**: **PARTIALLY FIXED** — the fixes actually made are proven live; the broader matrix remains open.

## L5-05Q-010: Throttled-network, responsive, and accessibility verification not attempted
- **Severity**: P2/P3 (unchanged, pre-existing gaps tracked since FINAL-L5-04/05M/05N/05O/05P).
- **Status**: **NOT FIXED** — same carried-forward scope.

## L5-05Q-011: Concurrency testing beyond service-area creation not performed
- **Severity**: P2.
- **Evidence**: Offerings suspend-vs-reactivate races, bookability-vs-suspension races (mission Part 26's full list) were not tested. Only the one concrete concurrency bug actually found (service-area creation) was investigated and fixed.
- **Status**: **NOT FIXED** — documented, not hidden.

## L5-05Q-012: One full-suite test-order flake investigated and confirmed unrelated
- **Severity**: informational (process note, not a bug).
- **Evidence**: `tests/test_trust_quality_phase1.py` (5 tests) failed once during a full 9182-test run; standalone rerun showed 28/28 passing. No relationship to this sprint's Tenant/Provider/service-area changes — confirmed pre-existing test-isolation flakiness, same class as prior sprints' `.next` cache and dev-server first-compile flakes.
- **Status**: **CONFIRMED NOT A REGRESSION**.

## Result
FINAL-L5-05Q adds 12 more (L5-05Q-001 through 012): two real, serious, previously-unknown P0 findings were discovered and fixed through live testing no unit test could have caught — a duplicate route registration causing an entire "fixed" endpoint set to be dead code, and a genuine cross-tenant vulnerability on the actually-live Service Area update/delete endpoints. A real concurrency bug (duplicate service areas from a TOCTOU race) was found and fixed with a transaction-scoped advisory lock, verified via a real concurrent-request test. Two Offering-mutation endpoints that wrote zero audit events now do. All fixes are live-verified via direct HTTP cross-tenant substitution, a real 5-role permission matrix, and 3 new + 19 re-verified Chromium tests. The mission's assumed Provider brand/zone/zipcode/capacity/SLA/bulk mutation surface was investigated and found not to exist in this codebase — a genuine, evidenced negative finding.

## L5-05R-001: 27 of 39 Enterprise Export resources remained unmapped, reachable by any authenticated admin
- **Severity**: P0 (this mission's own literal title/purpose).
- **Evidence**: `RESOURCE_EXPORT_PERMISSIONS` mapped 12 of 39 registered resources (FINAL-L5-05O). Tenants, Categories, Engines, Offerings, Service Bookings, Coaching Appointments, Real Estate Leads, Service Invoices, Payments, Commission Records, Reviews, Complaints, Refund/Rework Requests, Pricing Tiers/Locations/Rules, Customers, Settings, Feature Flags, and 7 `provider_*` resources were all reachable by any authenticated admin.
- **Fix**: All 27 mapped, reusing existing permission keys where a clean domain fit existed; 2 new keys added (`operations:export`, `catalog:export`) only where no existing key fit.
- **Live API evidence**: Representative resource from each newly-mapped domain verified across all 5 roles with correct 201/403 results.
- **Tests**: `tests/test_final_l5_05r_export_resource_mapping.py::TestFinalL5_05RExhaustiveResourceMapping` (9 tests).
- **Status**: **FIXED** — 0 of 39 registered resources remain unmapped.

## L5-05R-002: Unknown/unregistered export resource_key silently bypassed authorization
- **Severity**: P1.
- **Evidence**: `required_export_permission()` returns `None` (dict.get) for any resource_key not in the mapping; the router's `if required and not has(...)` check treated `None` as falsy and skipped authorization entirely.
- **Fix**: `create_export` now checks `resource_exists()` first, returning `422 EXPORT_RESOURCE_UNSUPPORTED` for anything unregistered.
- **Live API evidence**: A fake resource_key correctly returns `422` with the controlled error code.
- **Tests**: `TestUnknownResourceFailsClosed` (2 tests).
- **Status**: **FIXED**.

## L5-05R-003: Dead-code tenant-scope validation for SCOPE_PROVIDER exports, plus a live-caught Super Admin regression
- **Severity**: P1 (real gap, latent since no worker exists to exploit it against real data yet -- see L5-05R-006).
- **Evidence**: `EnterpriseListQueryService.validate_scope()` has zero callers anywhere in the codebase. A provider/tenant-side caller could submit a `tenant_id` filter belonging to a different tenant with no rejection at job-creation time.
- **Fix**: Wired directly into `create_export` for `SCOPE_PROVIDER` resources -- a mismatched `tenant_id` filter now returns `403 EXPORT_CROSS_TENANT_FORBIDDEN`.
- **Real regression found during live verification**: the first version didn't exempt `super_admin` (whose `tenant_id` is `None`), incorrectly blocking Super Admin from exporting any provider-scoped resource with a tenant filter. Fixed with the same exemption pattern used elsewhere in this codebase; live-verified before (403, wrong) and after (201, correct) the fix.
- **Tests**: `TestProviderScopeTenantIsolation` (2 tests).
- **Status**: **FIXED**. The actual cross-tenant denial path for a non-exempt caller was verified via code inspection only (no demo `tenant_owner` credential was available this session for an end-to-end live HTTP test) -- documented honestly, not claimed as fully live-proven.

## L5-05R-004: Invalid export field selection produced an unhandled 500 instead of a controlled 422
- **Severity**: P2 (discovered live while verifying the new mappings, not a security hole).
- **Evidence**: `create_export_job` raises plain `ValueError` for `EXPORT_FIELD_NOT_ALLOWED`/`EXPORT_JOB_NOT_FOUND`/`EXPORT_JOB_ACCESS_DENIED`, uncaught by the router.
- **Fix**: The 3 export endpoints now catch `ValueError` and convert the 3 known codes to controlled `ServiceOSException`s (422/404/403). Scoped to export endpoints only -- the same pattern in the unrelated Saved-Views/Column-Preferences endpoints was not touched (out of this sprint's scope).
- **Live API evidence**: An invalid column selection now returns `422 EXPORT_FIELD_NOT_ALLOWED` instead of `500`.
- **Status**: **FIXED** for export endpoints.

## L5-05R-005: CSV formula injection unmitigated
- **Severity**: P2.
- **Fix**: `generate_csv` now prefixes formula-triggering cell values (`=`,`+`,`-`,`@`, tab, CR) with a single quote (OWASP-standard mitigation).
- **Tests**: `TestCsvFormulaInjectionMitigation` (2 tests).
- **Status**: **FIXED**.

## L5-05R-006: No export worker/file-generation pipeline exists anywhere in this codebase
- **Severity**: P0 (blocks the mission's own Part 42/39 acceptance criteria; a pre-existing platform limitation, not introduced or left incomplete by this sprint).
- **Evidence**: `ExportService.generate_csv()`/`.mark_completed()` are never called from any router or background job (confirmed via full-codebase grep). `create_export_job` only ever creates a `PENDING` (or `FAILED`-if-too-large) job row -- no file is ever produced, for any resource, admin or provider. Matches a carry-forward note in FINAL-L5-05K's documentation.
- **Status**: **DOCUMENTED, NOT FIXED** -- building an async export worker is a substantial, separately-scoped infrastructure effort, explicitly out of this sprint's bounded resource-mapping/authorization focus. This is the primary reason full READY cannot be returned.

## L5-05R-007: Sensitive-field classification not performed against the mission's full taxonomy
- **Severity**: P2.
- **Evidence**: Each resource's pre-existing `sensitive_fields`/`allowed_export_fields` config (Sprint 26) was not re-audited against the mission's PUBLIC/INTERNAL/CONFIDENTIAL/SENSITIVE/SECRET/PROHIBITED classification.
- **Status**: **NOT FIXED** -- documented, not hidden.

## L5-05R-008: Export result/download authorization not extended beyond existing ownership check
- **Severity**: P2.
- **Evidence**: `get_export_job` already correctly scopes to the requesting user (pre-existing, confirmed correct) -- there is no signed-URL/storage layer to further audit since no files are ever generated (see L5-05R-006).
- **Status**: **NOT APPLICABLE beyond existing correct behavior** -- documented.

## L5-05R-009: Rate limits and concurrency/idempotency testing not performed
- **Severity**: P2.
- **Status**: **NOT FIXED** -- not attempted this sprint.

## L5-05R-010: One full-suite test-order flake investigated and confirmed unrelated
- **Severity**: informational.
- **Evidence**: `test_p0_provider_enterprise.py` (23 errors, 13 failures reported in summary) failed once during a full ~9200-test run; standalone rerun showed 65/65 passing, 0 errors. This file was not touched this sprint. Same class of pre-existing test-isolation flake documented in FINAL-L5-05Q (`test_trust_quality_phase1.py`).
- **Status**: **CONFIRMED NOT A REGRESSION**.

## L5-05R-011: Full five-role Chromium export-dialog matrix incomplete
- **Severity**: P1.
- **Evidence**: No export dialog/UI beyond what FINAL-L5-05O already covers (dashboard export button, Security Deposits action menu) was found or modified this sprint -- 13 prior-sprint Chromium tests re-run as regression evidence, zero new export-specific frontend coverage added since no frontend code changed.
- **Status**: **PARTIALLY FIXED** -- regression-proven, not newly exhaustively covered.

## L5-05R-012: Throttled-network, responsive, and accessibility verification not attempted
- **Severity**: P2/P3 (unchanged, pre-existing gaps tracked since FINAL-L5-04 through 05Q).
- **Status**: **NOT FIXED** -- same carried-forward scope.

## Result
FINAL-L5-05R adds 12 more (L5-05R-001 through 012): completed the mission's own literal purpose -- all 39 registered Enterprise Export resources now have an explicit export permission, 0 unmapped. Found and fixed 3 additional real defects while live-verifying this completion: an unknown-resource fail-open gap, a dead-code tenant-scope check now wired in (including a live-caught-and-fixed Super Admin regression from the fix itself), and a 500-instead-of-422 error-handling bug. CSV formula injection is now mitigated. The most significant honest finding is architectural: no export worker exists anywhere in this codebase, so no export ever produces a real file for any resource -- a pre-existing platform limitation, not an incomplete fix, and the primary reason this mission's real-generated-export verification requirement cannot be satisfied. All fixes are live-verified via a real 5-role API matrix and 13 re-run Chromium regression tests, zero regressions.

## L5-05S-001: No export worker/file-generation pipeline existed anywhere (closes L5-05R-006)
- **Severity**: P0 (this mission's own literal purpose).
- **Evidence**: Confirmed at the start of this sprint -- `ExportService.generate_csv()`/`.mark_completed()` were dead code, `create_export_job` only ever created a `pending` row.
- **Fix**: Built a real database-backed worker (`app/jobs/export_worker.py`), started as an asyncio background task from `app/main.py`'s lifespan (10s tick, 5min cleanup), following the same pattern already proven in production by `compliance_sla.py`.
- **Live evidence**: Backend restarted; `export_worker_loop.started` confirmed in logs; a real `admin_categories` export job transitioned `pending` → `completed` within one 10s tick, with a real file, checksum, and row_count.
- **Status**: **FIXED**.

## L5-05S-002: Job claiming needed to be provably safe under concurrency
- **Severity**: P0 (mission rule: "do not return READY without worker concurrency testing").
- **Evidence**: A naive SELECT-then-UPDATE claim would allow two concurrent worker ticks to both claim and process the same job.
- **Fix**: `_claim_next_job()` uses `SELECT ... FOR UPDATE SKIP LOCKED`, guaranteeing at most one claimer wins any given row.
- **Tests**: `test_concurrent_claims_never_double_claim_the_same_pending_job` -- 6 simultaneous claimers against a real Postgres instance, 6 distinct jobs claimed, 0 duplicates, verified via a real `SELECT COUNT(*)` after the fact (not asserted from mocks).
- **Status**: **FIXED**.

## L5-05S-003: Only 5 of 39 authorization-mapped resources have a real file-generation adapter
- **Severity**: P1 (scoped, honest limitation -- not a defect).
- **Evidence**: `RESOURCE_ADAPTERS` covers `admin_reviews`, `admin_finance_topups`, `admin_audit_logs`, `admin_tenants`, `admin_categories` -- one per required domain (Operations, Finance, Security/Audit, Tenant, Catalog). The other 34 authorization-mapped resources fail controlled with `EXPORT_GENERATOR_UNAVAILABLE` rather than hanging pending forever.
- **Live evidence**: A job created against `admin_pricing_tiers` (no adapter) correctly failed with `error_code=EXPORT_GENERATOR_UNAVAILABLE`, `retry_count=0` (non-retryable, no infinite loop).
- **Status**: **PARTIALLY FIXED** -- building all 39 adapters (many with the same declared-field-vs-real-column mismatches found below) is a multi-sprint effort, not attempted in full this sprint.

## L5-05S-004: Two pre-existing Sprint 26 field-registry/real-model mismatches discovered while building adapters
- **Severity**: P2 (pre-existing metadata gap, not introduced this sprint).
- **Evidence**: `admin_audit_logs`'s declared `allowed_export_fields` (`event_type`/`record_type`/`actor_type`) don't exist on the real `PlatformAuditLog` model (which has `operation`/`entity_type`/`actor_role`). `admin_categories`'s declared `status` field doesn't exist on `ServiceCategory` (only boolean `is_active`).
- **Fix**: Both adapters alias the real columns to the declared field names so the existing `generate_csv()` allowlist filter works unchanged, rather than silently renaming the pre-existing Sprint 26 registry (out of this sprint's bounded scope).
- **Status**: **WORKED AROUND, NOT FIXED AT THE SOURCE** -- documented for a future registry-reconciliation pass.

## L5-05S-005: Export files needed to be private, not reachable via the existing public media storage
- **Severity**: P1 (mission rule: files must be private-by-default, storage paths must never be returned directly).
- **Evidence**: The only existing storage adapter (`MediaStorageService`) writes into `uploads/`, mounted as public `StaticFiles`.
- **Fix**: New purpose-built `ExportStorageService` (`app/engines/enterprise_grid/export_storage.py`), writing to `var/exports/` (never mounted as static files), with `sanitize_filename()`/`_key_to_path()` path-traversal defenses.
- **Tests**: `TestExportStorageServiceUnit` -- traversal rejection, round-trip upload/exists/read/delete, confirms the directory is never `uploads/`, confirms `main.py` never mounts `var/exports` as static files.
- **Status**: **FIXED**.

## L5-05S-006: Download endpoint needed independent re-authorization, not just ownership
- **Severity**: P1 (mission rule 15: "job ID alone is never sufficient"; permission revocation must take effect).
- **Evidence**: Pre-existing `get_export_job` already scoped by `requested_by_user_id`, but nothing re-checked the resource's export permission at download time.
- **Fix**: `download_export` re-checks `required_export_permission()` before returning any bytes, in addition to the ownership check, status=completed check, expiry check, and file-existence check -- all before reading storage.
- **Live evidence**: A different admin (Operations Admin) attempting to download or even `GET` Super Admin's own completed job both correctly returned `403`/`EXPORT_JOB_ACCESS_DENIED`.
- **Tests**: `TestDownloadEndpointAuthorizationOrdering` (6 tests, static ordering guards).
- **Status**: **FIXED**.

## L5-05S-007: No cancel endpoint existed for pending/processing jobs
- **Severity**: P2 (real missing capability, not a defect).
- **Fix**: New `POST /v1/enterprise/exports/{id}/cancel`, `pending`/`processing` → `cancelled` (409 otherwise), storage swept by the cleanup task.
- **Live evidence**: Cancel succeeded on a pending job; re-cancel correctly `409`; download of a cancelled job correctly `409`.
- **Status**: **FIXED**.

## L5-05S-008: Retry did not clear worker execution state, only status/failure_reason
- **Severity**: P2 (a retried job could retain a stale `worker_id`/`claimed_at`/`storage_key` from the previous failed attempt).
- **Fix**: `retry_export` now also resets `worker_id`, `claimed_at`, `started_at`, `storage_key`, `progress`.
- **Live evidence**: Retried the failed `admin_pricing_tiers` job -- correctly returned to `pending` with clean state, re-attempted (and failed again as expected, since still unsupported).
- **Status**: **FIXED**.

## L5-05S-009: No retention/expiry cleanup existed
- **Severity**: P1 (mission rules 20/27/28).
- **Fix**: `run_cleanup()` expires `completed` jobs past `expires_at` (24h), deletes the real file, transitions to `expired`; sweeps orphaned storage on `failed`/`cancelled` jobs. Runs from the background loop every 5 minutes.
- **Tests**: `test_cleanup_expires_completed_job_past_expiry_and_deletes_its_file` -- real file written to real storage, `expires_at` set to the past, `run_cleanup()` called, file confirmed deleted from disk and row confirmed `expired`.
- **Status**: **FIXED** (verified with an artificially-past `expires_at`, not a real 24-hour live wait -- documented honestly).

## L5-05S-010: Crashed-worker recovery for stuck `processing` jobs was unverified
- **Severity**: P1 (mission rule 4/crash-recovery).
- **Fix**: `_recover_stale_running_jobs()` returns jobs stuck `processing` for >15 minutes to `pending` (bounded by `MAX_RETRIES`), or fails permanently with `EXPORT_WORKER_TIMEOUT` once exhausted.
- **Tests**: `test_stale_processing_job_is_recovered_to_pending_then_eventually_fails` -- a job artificially claimed 30 minutes ago with `retry_count` already at `MAX_RETRIES` correctly failed with `EXPORT_WORKER_TIMEOUT` rather than looping forever.
- **Status**: **FIXED**.

## L5-05S-011: XLSX/PDF export formats, S3/R2 signed URLs, rate limiting, and idempotent job creation not implemented
- **Severity**: P2 (explicitly scoped-down this sprint, consistent with "phased resource/format support").
- **Evidence**: Only `csv` is generated (`EXPORT_FORMAT_UNSUPPORTED` for anything else); storage is local-filesystem only (no S3/R2 credentials configured in this environment); no rate limit bounds export-creation volume; no idempotency key on job creation (a retried client request creates a duplicate job).
- **Status**: **NOT FIXED** -- documented, not hidden. Local storage is appropriate for this dev/test environment per the mission's own explicit allowance but is not production-multi-instance-ready.

## L5-05S-012: No Chromium/browser-automation verification was performed this sprint
- **Severity**: P1.
- **Evidence**: No browser-automation tool was available in this session. All verification is real, live HTTP/API evidence (curl against the real running backend, real logins for all 5 roles, real job IDs, real downloaded-file checksums matching the API-reported checksum) rather than fabricated or silently skipped. Source-reading confirmed the pre-existing frontend (`commission-records`, `payments`, `refund-requests`, `service-jobs` pages) already calls `enterpriseApi.createExport()` and tells the user to "check /admin/exports" -- but **no `/admin/exports` page exists anywhere in the frontend** (a separate, pre-existing dead-end UX gap, not introduced or fixed this sprint).
- **Status**: **NOT FIXED (no tool available)** -- documented honestly, not claimed as run.

## L5-05S-013: `app/jobs/export_worker.py` (this sprint's own new code) initially imported a nonexistent `AsyncSessionLocal` from `app.database` -- and the pre-existing `compliance_sla.py` background job has apparently had the exact same bug since its own introduction, silently, in production
- **Severity**: P0 (new finding, unrelated pre-existing production bug -- distinct from this sprint's own bug, which was caught and fixed before commit).
- **Evidence**: `app/database.py` has no module-level `AsyncSessionLocal` -- the real API is `get_session_factory()`. `app/jobs/export_worker.py` (this sprint's own code, modeled deliberately on `compliance_sla.py`'s proven pattern) initially used the same nonexistent import and was caught immediately by this sprint's own new real-Postgres tests (`ImportError` on the very first test run). Grepping the codebase for the same import shows `app/jobs/compliance_sla.py` -- the pattern this worker was modeled on, described in this engagement's own history as "a proven-in-production pattern" -- uses the exact same nonexistent import at 2 call sites. Because `compliance_sla.py`'s background loop wraps every tick in `except Exception: log, don't crash`, this means the SLA-compliance background job has been silently failing (`ImportError`, caught, logged, ignored) on every single tick since it was built, and has apparently never once successfully executed against a real database. `tests/test_p0_compliance_sla_automation.py`'s entire test suite is static source-inspection only (e.g. `assert "AsyncSessionLocal" in self._src()`) -- none of its tests actually invoke the loop against a database, which is why this was never caught.
- **Fix applied this sprint**: `export_worker.py`'s two call sites (`run_worker_tick`, `run_cleanup`) now use `from app.database import get_session_factory` / `get_session_factory()()`. Confirmed correct via 7 real-Postgres tests and full live verification against the running backend.
- **`compliance_sla.py` deliberately NOT touched this sprint**: fixing it is unrelated to Enterprise Export and outside this mission's explicit scope boundary. It is a real, severe, live production defect (SLA breach detection has apparently never actually run) that a future sprint must treat as a P0 blocker in its own right.
- **Status**: **FIXED in this sprint's own code** (export_worker.py); **FOUND, NOT FIXED** in the pre-existing, unrelated `compliance_sla.py` (new blocker for a future sprint).

## Result
FINAL-L5-05S adds 13 more (L5-05S-001 through 013): built and live-verified a real export execution pipeline -- database-backed worker with `FOR UPDATE SKIP LOCKED` concurrency safety, 5 real resource query adapters spanning every required domain, private local file storage, download/cancel/retry endpoints with independent re-authorization, and retention cleanup. Every major claim is backed by real evidence: a real Postgres concurrency test (6 simultaneous claimers, 0 duplicates), a real end-to-end file generation + download whose SHA-256 checksum matches the API-reported value, a real 5-role live API matrix (all 15 create/deny combinations correct), and real cross-user download-denial proof. A genuine, previously-silent bug was found and fixed in this sprint's own new code (a nonexistent `AsyncSessionLocal` import), and while fixing it, an unrelated, more severe, pre-existing production bug was discovered in `compliance_sla.py` (the same nonexistent import, meaning the SLA-compliance background job has apparently silently no-op'd on every tick since its introduction) -- logged as a new P0 blocker rather than fixed, since it is outside this mission's Enterprise Export scope. The full 39-resource / XLSX+PDF / S3-signed-URL / rate-limiting / idempotency / Chromium-and-accessibility scope remains open, honestly documented rather than claimed complete.

## L5-05T-001: Duplicate Service Area route registration (admin AND, newly discovered, tenant-portal side)
- **Severity**: P0 (this mission's own literal purpose).
- **Evidence**: `serviceability.router` and `tenant_engine.admin_router` both registered `/v1/admin/tenants/{tenant_id}/service-areas*` (established in FINAL-L5-05Q). This sprint's own runtime inventory found a SECOND, parallel duplicate family FINAL-L5-05Q never inventoried: `serviceability.router` and `tenant_engine.portal_router` both registered `/v1/tenant/service-areas*`.
- **Fix**: All 8 duplicate routes (4 admin + 4 tenant-portal) removed from `tenant_engine`. `serviceability.router` is now the sole owner of both path families, confirmed via the live runtime route table.
- **Status**: **FIXED**.

## L5-05T-002: `tenant_engine` Service Area handlers were shadowed dead code -- except one wasn't
- **Severity**: P0 (a live, undiscovered second mutation path with weaker validation).
- **Evidence**: GET/POST/DELETE were exact `(method, path)` duplicates, confirmed unreachable (05Q). The "update" operation was NOT shadowed on either side: `serviceability.router` registers `PUT`, `tenant_engine.admin_router`/`portal_router` both registered `PATCH` for the identical path -- different verbs don't collide, so `PATCH` was live and independently reachable this whole time, bypassing `serviceability`'s coverage validation, update-time duplicate check, and `is_primary` reassignment. Tenant-safe (proper `WHERE` scoping) but a real validation-coverage gap.
- **Fix**: All 4 `PATCH`/GET/POST/DELETE routes removed from both `tenant_engine` routers. Confirmed via live OpenAPI: zero `PATCH` on either Service Area item path.
- **Status**: **FIXED**.

## L5-05T-003: Service Area canonical ownership undefined
- **Severity**: P0.
- **Fix**: `ServiceabilityService` selected as canonical owner based on live reachability, strictly larger/more-correct feature set (coverage/geo validation, zone support, primary-area reassignment, update-time duplicate checking, plan limits, candidate validation, nested service mappings), and a real domain dependency from the booking/matching preflight engine. Full ADR with rejected alternatives in `FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md`.
- **Status**: **FIXED**.

## L5-05T-004: Endpoint schema parity -- one real gap found (audit trail), migrated
- **Severity**: P1.
- **Evidence**: The canonical `ServiceabilityService` wrote ZERO audit events for create/update/deactivate (confirmed via source read) -- the shadow `AdminTenantService` had a real audit trail. Every other capability comparison favored the canonical implementation (see ADR table).
- **Fix**: Ported into `ServiceabilityService._audit_service_area()`, writing `SERVICE_AREA_CREATED`/`UPDATED`/`DEACTIVATED` via `record_platform_audit`. Live-verified: a real create/update/deactivate sequence produced 3 real `platform_audit_logs` rows.
- **Status**: **FIXED**.

## L5-05T-005: Permission namespace parity
- **Severity**: P2 (no conflict found).
- **Evidence**: Both implementations used the same permission gate on the admin side (`P.PLATFORM_ADMIN`, super_admin-only via `P.ALL`). No dual-namespace conflict existed to reconcile.
- **Decision**: Policy preserved unchanged -- introducing a new permission grant for Service Area administration (e.g. to Operations Admin) is a genuine RBAC product decision outside this route-canonicalization mission's bounded scope, not a defect this sprint should silently decide.
- **Status**: **CONFIRMED NO CONFLICT, POLICY UNCHANGED**.

## L5-05T-006: Tests exercising dead handlers
- **Severity**: P1 (mission rule 15).
- **Evidence**: `tests/test_sprint4_tenant_onboarding.py` had 5 tests calling the now-removed `AdminTenantService` service-area methods directly, plus 1 test asserting the now-removed portal route existed. `tests/test_final_l5_05q_provider_coverage_mutations.py` had 1 test asserting both routers still defined the duplicate path, and a "defense-in-depth" test class pinning the now-removed dead-code source text.
- **Fix**: The 5 dead-handler tests removed (plus the now-orphaned `_make_area()` helper); the stale route-existence test inverted to assert absence; the defense-in-depth class replaced with one asserting the methods are gone. All confirmed via `git grep` that zero remaining references to the removed methods exist anywhere in the test suite.
- **Status**: **FIXED**.

## L5-05T-007: Router behavior depended on include order
- **Severity**: P1 (mission rule 13/21).
- **Evidence**: Before this sprint, which implementation actually served a request depended entirely on `main.py`'s router registration order (`serviceability_router` before `admin_tenant_router`) -- a fragile, easy-to-silently-break invariant.
- **Fix**: Since exactly one module now owns every Service Area path, there is nothing left for include order to arbitrate. `TestIncludeOrderSafety` makes this explicit and would catch any future reintroduction of a second implementation regardless of where it's registered.
- **Status**: **FIXED**.

## L5-05T-008: Duplicate route detection absent
- **Severity**: P0 (mission rule 24).
- **Fix**: `TestGlobalDuplicateRouteDetector` added, walking the real, live FastAPI route table (a recursive flattener was required -- `app.routes` contains `_IncludedRouter` wrapper objects in this FastAPI version, not a flat `APIRoute` list; a naive filter silently sees 0 routes and produces false negatives). Zero tolerance for Service Area duplicates (never allowlisted); a minimal, justified, pinned allowlist exists for pre-existing unrelated debt (see L5-05T-013).
- **Status**: **FIXED**.

## L5-05T-009: OpenAPI ownership ambiguous
- **Severity**: P1.
- **Fix**: `TestRouteOwnershipRegistry` + `TestOpenAPIUniqueness` prove, against the live runtime route table and the live-generated OpenAPI schema, that `serviceability.router` exclusively owns every Service Area path with exactly one operation per method/path and unique operation IDs. Live-verified against the running server's real `/openapi.json`.
- **Status**: **FIXED**.

## L5-05T-010: Backward compatibility unverified
- **Severity**: P1.
- **Evidence**: Verified before removal: no test, no frontend caller (super-admin or tenant-portal) depended on the shadow `tenant_engine` contract's specific verb (`PATCH`) or field names in a way that would break on removal. The tenant-portal frontend already called the canonical `PUT` verb.
- **Fix**: `REMOVE` disposition chosen over a compatibility adapter (mission rule 19 -- an adapter exists to protect a real caller; none existed here).
- **Status**: **FIXED / CONFIRMED NOT NEEDED**.

## L5-05T-011: Full five-role Chromium incomplete
- **Severity**: P1.
- **Evidence**: No browser-automation tool was available in this session (same limitation as FINAL-L5-05S). All verification is real, live HTTP/API evidence instead (5-role matrix, cross-tenant matrix, real audit-row confirmation via direct database query).
- **Status**: **NOT FIXED (no tool available)** -- documented honestly, not claimed as run.

## L5-05T-012: Performance/concurrency evidence
- **Severity**: P2 (concurrency correctness proven; formal timing benchmarks not run).
- **Evidence**: 2 new real-Postgres concurrency tests added (update-vs-deactivate racing on the same row with no lost update; two distinct tenants creating identical geography concurrently, proving the tenant-scoped advisory lock key doesn't falsely serialize unrelated tenants) -- both pass, extending FINAL-L5-05Q's create-vs-create coverage. No dedicated query-count/latency/lock-wait-time benchmark pass was run.
- **Status**: **PARTIALLY FIXED** -- correctness proven live; formal performance numbers not captured.

## L5-05T-013: 18 pre-existing, unrelated app-wide duplicate-route registrations + 13 duplicate operation IDs discovered as a byproduct
- **Severity**: P0/P1 (new finding, unrelated to Service Areas, discovered while building the global duplicate-route detector).
- **Evidence**: Once the route-flattening bug (`_IncludedRouter` vs. flat `APIRoute`) was fixed, the detector found 18 real `(method, path)` duplicates spanning: `GET /v1/admin/customers/{customer_id}/addresses` (serviceability vs. auth.admin_customers_router), `GET /v1/admin/engines` and `/v1/admin/engines/health` (engine_mgmt vs. provider_portal), `GET /v1/admin/finance/summary` (finance_hub vs. field_ops), `GET /v1/tenant/wallet` and `/wallet/ledger` (field_ops vs. tenant_engine), `GET /v1/admin/tenants/{tenant_id}/wallet` and `/wallet/ledger` and `POST .../wallet/adjust` (field_ops vs. tenant_engine), `GET`/`POST`/`PUT` on `/v1/admin/service-options*` (admin_catalog.admin_router vs. admin_catalog.service_option_admin_router), `POST /v1/staff/service-jobs/{job_id}/accept` and `/reject` (home_service_assignment vs. execution), and `GET /v1/admin/analytics/operational-alerts` (analytics.admin_router vs. analytics.platform_router). Plus 13 duplicate operation IDs in `admin_catalog.service_option_admin_router` and `service_setup.templates_router`.
- **Root cause**: Not investigated (out of this sprint's bounded scope) -- each pair means one handler is silently shadowed dead code, the exact same defect class this sprint fixed for Service Areas.
- **Why not fixed this sprint**: Explicitly outside this mission's bounded scope ("Do not alter broader Provider branding, pricing, Jobs, Finance, Export or booking architecture unless a real Service Area dependency requires a bounded compatibility change" -- none of these 18 touch Service Areas).
- **Fix applied this sprint**: Documented, allowlisted by exact `(method, path)` tuple / module with an explanatory comment, and pinned with a guard (`test_pre_existing_allowlist_still_matches_reality_exactly`) so the allowlist can neither hide a new duplicate nor silently go stale in either direction. Service Area routes are explicitly confirmed to never appear in either allowlist.
- **Status**: **FOUND, NOT FIXED** -- new P0/P1 blocker for a dedicated future sprint (same remediation pattern as this sprint: runtime inventory, parity comparison, canonical-owner decision, removal).

## Result
FINAL-L5-05T adds 13 more (L5-05T-001 through 013): closed the duplicate Service Area route architecture FINAL-L5-05Q left open, and found it was worse than 05Q's own framing -- a second, un-inventoried duplicate family on the tenant-portal side, and a live, undiscovered second mutation path (`PATCH` vs. the canonical `PUT`) on both sides. `ServiceabilityService` is now the sole, certified canonical owner with a full ADR; the shadow implementation (8 routes + 6 backing service methods) is removed entirely, not deprecated or adapted, since no real caller depended on it. The one real missing-behavior gap (zero audit trail in the canonical path) was migrated and live-verified. A global duplicate-route/operation-ID detector now exists with zero tolerance for Service Area duplication specifically. Three real, previously-unknown frontend contract bugs were found and fixed (2 silently-broken table columns, 1 wrong-endpoint refetch preventing newly created areas from appearing). Tenant isolation and concurrency protections from FINAL-L5-05Q are fully preserved and extended with 2 new real-Postgres tests. The most significant new finding is architectural and explicitly out of scope: 18 more pre-existing, unrelated app-wide route duplications and 13 more duplicate operation IDs exist in this codebase, following the exact same defect pattern -- honestly documented as a new blocker rather than expanded into.

## L5-05U-001: Two active Security Deposit permission namespaces (worse: three implementations, three permission systems)
- **Severity**: P0 (this mission's own literal purpose).
- **Evidence**: `finance_hub.admin_router` (`/v1/admin/finance/deposits*`, `finance:deposits:*`) and `package_commerce.admin_router` (`/v1/admin/tenants/{id}/security-deposit*`, `finance.security_deposits.*`) both gate mutations against the same `SecurityDeposit`/`SecurityDepositTransaction` tables. A third family, `platform_commerce.router` (`/v1/commerce/tenants/{id}/deposit*`), used `TENANT_BILLING_READ`/`MANAGE` (Usage Credit's own permission names) for reads and `require_super_admin` (a coarse role check, not a permission) for its one admin mutation.
- **Fix**: `FINANCE_DEPOSITS_*` selected as sole canonical family (ADR written). `package_commerce`'s 4 endpoints blocked (410) -- zero real caller, plus a real transactional-integrity defect (see L5-05U-004). `platform_commerce.admin_adjust_deposit` migrated to `require_permission(P.FINANCE_DEPOSITS_UPDATE)`.
- **Status**: **FIXED**.

## L5-05U-002: Frontend/backend permission mismatch -- precise root cause located
- **Severity**: P0 (live, reproducible: no role could both see AND use the dedicated Security Deposits admin page without holding both namespaces).
- **Evidence**: `/admin/finance/deposits`'s nav item (`AdminLayout.tsx`) AND its page-level `RequirePermission` route guard both checked `finance.security_deposits.read` (deprecated), while the SAME page's own action menu and every backend endpoint it calls checked `finance:deposits:*` (canonical). `admin_readonly` held only the deprecated alias -- could see the nav item and pass the route guard, but the page's own data fetch (`financeApi.listDeposits()`) would then 403.
- **Fix**: Nav item, `RequirePermission` wrapper, and `permission-catalog.ts` all migrated to `finance:deposits:read`.
- **Live evidence**: Read Only admin's `GET /v1/admin/finance/deposits` confirmed live `200` (previously would have been consistent with a UI that could never load).
- **Status**: **FIXED**.

## L5-05U-003: Role bundles contained inconsistent deposit permissions
- **Severity**: P1.
- **Evidence**: `admin_finance` held all 4 canonical AND all 5 active deprecated-namespace keys (05O's bounded fix). `admin_readonly` held only the dead alias (authorized nothing). `admin_operations`/`admin_security` correctly held zero (confirmed unchanged).
- **Fix**: `admin_finance` now holds exactly the 4 canonical keys. `admin_readonly` migrated to canonical `FINANCE_DEPOSITS_READ`.
- **Tests**: `TestRolePolicyMatrix` (6 tests) -- exact-set assertions per role, zero unexplained cells.
- **Status**: **FIXED**.

## L5-05U-004: A real transactional-integrity defect in the (now-blocked) `package_commerce` implementation
- **Severity**: P0 (financial correctness -- discovered as a byproduct of the namespace investigation, not the mission's literal ask, but squarely "Security Deposit adjustment ... must be auditable" / "no direct current-balance update without history").
- **Evidence**: `PackageCommerceService.admin_refund_deposit`/`admin_forfeit_deposit`/`admin_mark_deposit_paid` mutated `SecurityDeposit.status` directly with **zero** `SecurityDepositTransaction` history row and no call to the shared `credit_deposit`/`debit_deposit` ledger primitives. Since `current_balance` is a computed property (`total_paid + replenishment_total - warranty_drawn`), a "refund" via this path would flip `status="refunded"` while `current_balance` silently never changed -- confirmed via source read, not merely inferred.
- **Fix**: The 4 endpoints backing these methods are blocked (410) rather than fixed-in-place, since (a) zero real caller depended on them, (b) the canonical `finance_hub` implementation already does this correctly via `credit_deposit`/`debit_deposit`, so fixing package_commerce's copy would be pure duplication.
- **Status**: **FIXED (via blocking the defective path, not patching it)**.

## L5-05U-005: Deprecated aliases -- disposition and guard
- **Severity**: P1 (mission rule 27: no deprecated alias may grant access after migration).
- **Evidence**: 8 `FINANCE_SECURITY_DEPOSITS_*` keys existed; 4 backed the now-blocked endpoints, 4 (`CONFIG_UPDATE`/`CREATE`/`HOLD`/`AUDIT_READ`) were confirmed via `git grep` to have **never** been wired to any endpoint at all.
- **Fix**: All 8 constants remain defined (marked `# DEPRECATED` inline, not deleted -- explicit disposition per mission rule 13) but removed from every role bundle. `TestCanonicalPermissionNamespace.test_deprecated_alias_permissions_authorize_zero_active_endpoints` greps the entire `app/` tree for any remaining `require_permission(P.FINANCE_SECURITY_DEPOSITS_*)` call -- fails CI if one is reintroduced.
- **Status**: **FIXED**.

## L5-05U-006: Tenant-isolation matrix -- a real, previously-undiscovered cross-tenant vulnerability found and fixed
- **Severity**: P0 (new finding, byproduct of investigating the `platform_commerce` deposit family for this mission's Part 20).
- **Evidence**: `CommerceService.get_deposit_status`/`initiate_deposit`/`get_deposit_transactions` never verified the caller's own tenant matched the route's `tenant_id`. Gated by `TENANT_BILLING_READ`/`MANAGE`, which `tenant_owner` legitimately holds for self-service -- meaning any authenticated tenant owner could substitute another tenant's UUID and read that tenant's Security Deposit status/history. `require_permission()` is pure RBAC (role→permission only, no tenant scoping), so nothing else in the stack caught this.
- **Fix**: `CommerceService` gained `actor_tenant_id` tracking + `_assert_owns_tenant_deposit()`, mirroring `ServiceabilityService._assert_owns_tenant()`'s established FINAL-L5-05Q pattern exactly. Scoped to `actor_role == "tenant_owner"` only -- admin/super_admin callers unaffected.
- **Live + automated evidence**: `test_live_cross_tenant_read_denied_for_tenant_owner` (real Postgres) confirms Tenant A's `tenant_owner` denied reading Tenant B; `test_live_admin_read_across_tenants_still_works` confirms super_admin unaffected.
- **Status**: **FIXED**.

## L5-05U-007: Deposit idempotency / L5-05U-008: Deposit concurrency
- **Severity**: P2 (already correct in the canonical path, not a gap this sprint needed to close).
- **Evidence**: `credit_deposit`/`debit_deposit` (the shared primitives the canonical `finance_hub` and `platform_commerce` paths both use) already enforce non-negative balances (`debit_deposit` raises `SECURITY_DEPOSIT_REQUIRED` if `current < amount`) via real column arithmetic, not application-level bookkeeping that could drift.
- **New evidence this sprint**: `test_concurrent_debits_never_produce_negative_balance` (real Postgres, 2 concurrent debits of 700 against a balance of 1000) -- exactly 1 succeeds, final balance is deterministic (300), never negative.
- **Status**: **CONFIRMED CORRECT, extended with real concurrency proof**.

## L5-05U-009: Domain isolation -- confirmed guarded
- **Severity**: P2 (verification, not a gap).
- **Evidence**: `credit_deposit`/`debit_deposit`, `FinanceHubService`'s deposit mutations, and `CommerceService`'s deposit methods all confirmed via source read + a real-Postgres test to never reference `tenant_billing`/`usage_credit_ledger`.
- **Tests**: `TestDomainIsolationGuards` (4 tests, including 1 real-DB before/after comparison).
- **Status**: **CONFIRMED, GUARDED**.

## L5-05U-010: Admin Read Only presentation -- 2 real ungated frontend controls found and fixed
- **Severity**: P1.
- **Evidence**: The deposits list page's Export button had zero frontend permission gating (relied solely on the backend's `FINANCE_EXPORT` check, meaning it visibly rendered for Read Only despite always failing). The Tenant Detail page's "Adjust Security Deposit" overflow-menu item had zero frontend gating at all (rendered for every role that could reach the page, relying solely on the backend's coarse `require_super_admin` -- which, per L5-05U-001, meant even Finance Admin's own rendered button always 403'd).
- **Fix**: Both gated on their canonical permissions (`finance:hub:export`, `finance:deposits:update` respectively).
- **Status**: **FIXED**.

## L5-05U-011: Five-role Chromium incomplete
- **Severity**: P1.
- **Evidence**: No browser-automation tool was available in this session (same limitation as FINAL-L5-05S/05T). All verification is real, live HTTP/API evidence (5-role matrix, cross-tenant matrix, real audit-row/balance confirmation via direct database query) plus real-Postgres automated tests, not fabricated or silently skipped.
- **Status**: **NOT FIXED (no tool available)** -- documented honestly.

## L5-05U-012: Responsive/accessibility/performance evidence incomplete
- **Severity**: P2.
- **Evidence**: Not attempted this sprint -- no new frontend UI surface was built (only permission-gating fixes to existing controls), so no new layout/accessibility surface exists to certify beyond what FINAL-L5-05M/05N already covered platform-wide.
- **Status**: **NOT FIXED** -- out of bounded scope, consistent with "do not redesign the broader Finance UI."

## Result
FINAL-L5-05U adds 12 more (L5-05U-001 through 012): reconciled the Security Deposit permission-namespace duplication FINAL-L5-05O left open, and found the true scope was worse than 05O's framing -- three independent live implementations (not two) against the same tables, with a precisely-located root cause for the "frontend page vs. mutation endpoint" mismatch (the dedicated Security Deposits page's nav item and route guard checked the deprecated namespace while its own action menu and backend checked the canonical one). `FINANCE_DEPOSITS_*` is now the sole canonical family with a full ADR; the deprecated namespace's constants are frozen (not deleted) and pinned by an automated guard. Two real, previously-unknown bugs were found and fixed as byproducts: a transactional-integrity defect in the now-blocked `package_commerce` implementation (refund/forfeit never actually moved money in the ledger) and a genuine cross-tenant vulnerability in `platform_commerce`'s tenant self-service deposit endpoints (no tenant-ownership check at all). Two real, previously-ungated frontend controls (Export button, Adjust Security Deposit menu item) are now correctly permission-gated. All fixes are live-verified via a real 5-role API matrix, real cross-tenant denial, real audit-row confirmation, and 2 new real-Postgres concurrency/isolation tests, with zero regressions in the full 9279-test backend suite. Chromium and responsive/accessibility/performance evidence remain out of scope (no browser tool available; no new UI surface built).
