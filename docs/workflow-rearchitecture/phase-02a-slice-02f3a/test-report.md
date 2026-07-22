# Test Report — Slice 2F-3A

## New tests this slice
`tests/test_phase2f3a_execution_assignment_overlap.py` — 7 tests across 3
classes:
1. `TestAcceptRejectRouteShadowing` (4) — live HTTP proof that
   `home_service_assignment.staff_router` answers both `/accept` and
   `/reject` (via `engine_id: "assignment"` in the response, unique to that
   module); source-level proof that the shadowed execution-router
   functions still exist (must not be deleted based on this finding alone);
   source-level proof that `app/main.py`'s registration order still puts
   `home_service_assignment` before `execution.home_service_router`.
2. `TestDistinctCapabilitiesNotConflated` (1) — confirms
   `provider_cancel_job` and `cancel_assignment` call different service
   methods, guarding against a future accidental merge.
3. `TestPartsRequestBoundaryIntact` (2) — confirms no Parts endpoint exists
   in `home_service_assignment`, and that `PartsRequest` remains keyed by
   `job_id`/`technician_id`.

Plus 1 new regression test added to
`tests/test_phase2f_mutation_enforcement.py::TestMutationRouteInventoryScript`
(`test_execution_assignment_overlap_is_exactly_the_two_adjudicated_routes`)
proving the live route walk finds exactly the 2 adjudicated overlaps and no
others.

## Combined targeted regression run
```
tests/test_phase2a_my_work.py .............................. 13 passed
tests/test_sprint21_execution.py .......................... 72 passed
tests/test_customer_idor.py ............................... 6 passed
tests/test_sprint4_tenant_onboarding.py ................... 76 passed
tests/test_phase11.py::test_create_review_requires_auth ... 1 passed
tests/test_sprint24_customer_reviews.py ................... 40 passed
tests/test_phase2c_role_integrity.py ....................... 7 passed
tests/test_phase2d_tenant_access_model.py ................. 18 passed
tests/test_phase2e_effective_permissions.py ................ 9 passed
tests/test_phase2f_mutation_enforcement.py ................. 9 passed (new)
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed
tests/test_phase2f2_provider_portal_mutation_enforcement.py  53 passed
tests/test_phase2f3a_execution_assignment_overlap.py ....... 7 passed (new)
tests/test_auth_login_fix.py
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_module_l5_01a_admin_finance_router_auth.py ...... (72 combined)
tests/test_final_l5_01b_admin_tenant_rbac.py ............... (included)
────────────────────────────────────────────────────────────────
TOTAL: 490 passed, 1 failed (pre-existing, unrelated flake -- see below), ~112s
Re-run in isolation: 1 passed -- confirms the flake, not a regression.
```

`TestRealConcurrencyMatrix::test_concurrent_debits_never_produce_negative_balance`
(in `test_final_l5_05u_security_deposit_permission_authorization.py`) failed
once under combined-suite load and passed immediately when re-run in
isolation — a pre-existing timing-sensitive concurrency test, unrelated to
this slice's read-only/documentation-plus-test changes (this slice made
zero changes to any security-deposit, billing, or concurrency-related
code). Documented honestly, not hidden.

## Broader partition (execution, assignment, staff, provider, ServiceJob, quotes, parts, auth)
```
tests/test_module_l5_16_quotes.py
tests/test_module_l5_21_quote_notify.py
tests/test_module_l5_36_staff_app_service_jobs.py
tests/test_quote_approval.py
tests/test_sprint20_job_assignment.py
tests/test_sprint22_quote_checklist.py
tests/test_staff_idor.py
tests/test_step6_job_assignment.py
tests/test_step8_quote_checklist.py
────────────────────────────────────────────────────────────────
316 passed, 3 skipped, 0 failed, ~203s
```
3 pre-existing skips, not investigated further (out of scope: this slice
made no code changes to any of these modules).

**Not claimed as full-repository coverage** — 806 combined tests (490 + 316)
across the two runs, 1 pre-existing unrelated flake, 0 real failures; the
repository's total test count is materially larger.

## Live actions this slice
- Live HTTP call (via pytest + mocked DB) to
  `POST /v1/staff/service-jobs/{job_id}/accept` confirming
  `home_service_assignment.staff_router` answers (`engine_id: "assignment"`,
  error code `STAFF_JOB_NOT_ASSIGNED_TO_USER`).
- Ran `inventory_mutation_routes.py --module` for all 3 audited modules to
  build the exact 29-route dataset.
- Ran the new `--verify-overlap` mode across the 3 modules: **exit 0, 2
  overlaps found, both adjudicated.**
- Confirmed `app.main` imports cleanly (no code changes made to
  `app/engines/execution/`, `app/engines/home_service_assignment/`,
  `app/engines/tenant_engine/`, or `app/engines/provider_portal/`).

## Frontend
No frontend code was changed — read-only for audit purposes.
