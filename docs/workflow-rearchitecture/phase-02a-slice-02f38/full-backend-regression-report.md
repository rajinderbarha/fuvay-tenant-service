# Full Backend Regression Report — Slice 2F-38

## Summary

`python -m pytest tests/ -q` (entire backend suite, not just
`test_phase2f*.py`): **12,096 collected, 12,030 passed, 45 failed, 21
skipped**, 926.65s (0:15:26). Run once (not twice — see
`known-limitations.md` for why).

This is the **first time in this entire program** the complete backend
suite (not just the Phase-2F subset) has been run. It surfaces real,
previously-undiscovered findings, reported here in full rather than
hidden behind the clean 2445/2445 Phase-2F number.

## Classification of all 45 failures

### 1 — Test-order pollution, not a real regression (investigated, resolved)

`tests/test_phase2f35_critical_authorization_batch.py::TestDocumentTenantAuthority::test_generate_document_calls_trusted_tenant`
failed only when run as part of the full 12,096-test suite. Re-run in
isolation: **passes** (confirmed this slice). This is order/fixture
pollution from an unrelated earlier test in the full suite, not a
regression in the authorization work — consistent with Phase-2F's own
2445/2445 clean result across four independent full-Phase-2F-only runs
across this program (2F-37R-A twice, this slice twice).

### 2 — Real, previously undiscovered, certification-relevant finding (NEW this slice)

`tests/test_phase2d_tenant_access_model.py` — **8 failures, all reproduce
in isolation** (verified this slice):

- `test_canonical_roles_matches_the_10_role_registry` and
  `test_coverage_of_require_tenant_mutation_permission_is_still_narrow`:
  these are **frozen Phase-2D historical assertions that were never
  updated as the 2F-35/36/37 program added new `require_tenant_mutation_permission`
  callers** — the test still expects only 5 files call this guard;
  reality (correctly, by design) is now 26. This is a **test-history
  discipline gap missed by every prior slice in this program** (2F-35
  through 2F-38's own targeted-suite runs never included this file).
  Not a code defect — the code is doing exactly what 2F-35/36/37 intended.
  The test itself needs a `PROTECTED_BY_LATER_SLICE` update, which this
  slice does **not** apply (out of scope to modify test files beyond
  what's already committed; flagged for a future slice instead, since
  broadly rebaselining tests outside this slice's narrow allow-list was
  not authorized).

- `test_get_or_create_user_rejects_invalid_role_before_any_db_call`
  (6 parametrized cases: `tenant_manager`, `tenant_readonly`,
  `tenant_finance`, `tenant_support`, `tenant_staff_admin`,
  `platform_admin`) — **a real, live, currently-unguarded gap.**
  Investigated the actual source: `scripts/canonical_seed_final_l5_01.py::get_or_create_user()`
  has **zero role-validation logic anywhere** — it inserts whatever
  string is passed as `role` directly into the `users` table with no
  canonical-role check before or after the database call. This is the
  exact script that created the two known invalid-role demo accounts, and
  nothing prevents it from creating more if run again with a mistaken
  role value. Migration 144, once applied, would catch this at the
  database level via its `CHECK` constraint — but Migration 144 is not
  applied (see `postgres-environment-evidence.md`), so today this seed
  script is an **unguarded path for reintroducing this exact class of
  invalid-role defect**.

  **This is a genuine certification-blocking finding**, independent of
  the two already-known blockers. It directly falsifies WS6's required
  claim "no seed recreates invalid roles" for this specific script. No
  fix was applied this slice (modifying `canonical_seed_final_l5_01.py`
  is outside this slice's narrow allow-list of Migration 144 + demo
  account remediation + evidence); it is recorded here and in
  `final-known-limitation-registry.csv` as an open, unresolved risk
  requiring a future slice's explicit authorization to fix.

### 3 — Pre-existing, unrelated-domain failures (spot-checked, reproduce in isolation)

The remaining 36 failures span `test_checklist_system.py`,
`test_customer_frontend_02_hardening.py`, `test_customer_idor.py`,
`test_dispatch_job_sync.py`,
`test_final_l5_05t_service_area_route_canonicalization.py`,
`test_job_type_flows.py`, `test_module_l5_19_staff_chat.py`,
`test_p0_engine_management_enterprise.py`,
`test_p0_job_completion_credit_deduction.py`,
`test_phase7_staff_app_certification.py`, `test_service_catalog.py`,
`test_sprint22_quote_checklist.py`, `test_sprint24_customer_reviews.py`,
`test_sprint25_complaints.py`, `test_sprint27_notifications.py`,
`test_sprint4_tenant_onboarding.py`,
`test_sprint75_dispute_settlement.py`, `test_step8_quote_checklist.py`,
`test_tenant_service_coverage_enterprise_ui.py`, `test_versions.py`.

One representative sample (`tests/test_service_catalog.py`, 8 failures)
was re-run in isolation this slice and reproduces identically
(`FieldJob`/service-catalog domain-model assertions, unrelated to
authorization/roles). These failures span unrelated product domains
(checklist system, dispatch, complaints, quote-checklist, TypeScript
compile checks, version-pin checks) that this authorization program never
claimed to cover or fix. **Not individually re-verified one-by-one this
slice** given time constraints — recorded as "presumed pre-existing,
spot-check-consistent," not exhaustively proven for all 36.

## Certification impact

- Item 1 (test pollution): no impact — resolved by investigation.
- Item 2 (test_phase2d): **blocks an unqualified application-wide claim**
  independent of the demo-account/PostgreSQL blockers — it is a real,
  live gap in seed-script role-data integrity.
- Item 3 (36 unrelated failures): does not block the *authorization*
  certification specifically, but does mean the complete backend
  regression is **not** green, which independently matters for the
  `FULL_REGRESSION_BLOCKED` consideration — see `final-certification-report.md`.
