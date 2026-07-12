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

## Result
18 of 21 real bugs/gaps found across FINAL-L5-05 through FINAL-L5-05H were fixed and live-verified; FINAL-L5-05I through 05L added 40 more findings implementing the Usage Credit/Finance Hub/Admin Role architecture. FINAL-L5-05M adds 11 more (L5-05M-001 through 011): `AdminLayout` now consumes real server-provided effective permissions for the first time, closing the central L5-05L-010 gap — desktop sidebar visibility, 7 representative route guards, and 8 representative action guards are all proven correct live via 10/10 real Chromium tests (20/20 across all 3 most recent role/permission Chromium suites when run standalone). A real permission-key mismatch (`analytics:read` vs `analytics:dashboard:read`) was found and fixed by the new automated guard before commit. Exhaustive coverage of all ~44 routes/actions, mobile-specific navigation, and dashboard/contextual-link filtering remain open, consistent with this sprint's explicit "do not redesign the entire Admin UI" scope limit — each documented with direct evidence, not hidden or downgraded. One new, real, out-of-scope architecture mismatch was discovered and documented (L5-05M-011, Platform Users' dead `platform_role` field) rather than silently left unmentioned.
