# Test Report — Slice 2F-14

## New tests

`tests/test_phase2f14_field_ops_staff_authorization.py` — 34 tests, all passing. Covers:
role-gate on staff_router and the 7 field_ops.router execution alternates, tenant_owner
exclusion from execution alternates, access-scope awareness on assign/update_status,
`require_staff_or_technician_only` unit test (parametrized allowed/denied roles), object-
ownership re-verification (unmodified pre-existing checks), and the new completion-gate state
guard (4 tests).

## Regression

- `tests/test_phase2f14_field_ops_staff_authorization.py` + `test_step8_quote_checklist.py` +
  `test_p0_job_completion_credit_deduction.py`: **143 passed, 0 failed**.
- Broad sweep `-k "field_ops or checklist or step8 or job_type or complaints or real_estate or
  coaching"`: **865 passed, 1 failed, 2 errors** (out of 868 collected + deselected others). The
  1 failure (`test_module_l5_35_staff_app_jobs_api.py::TestLive::...`) and 2 errors
  (`test_p0_navigation_operation_visibility.py::TestEffectiveMenuResolver::...`) are all
  `httpx.ConnectError: All connection attempts failed` — live-server-dependent tests that require
  a running app instance, unrelated to any change made this slice (confirmed via traceback:
  connection failure, not an assertion failure).

## Fixes updated in pre-existing test files

- `tests/test_step8_quote_checklist.py` — 2 fixtures updated to set
  `status=JS.CHECKLIST_STARTED` (previously defaulted to `JS.ARRIVED`, which now correctly
  triggers the new `CHECKLIST_NOT_ACTIVE` guard before the tests' own note/photo assertions).
- `tests/test_p0_job_completion_credit_deduction.py` — 2 source-string regression tests updated
  to assert the new named-dependency pattern instead of the old inline-check string.

## Conclusion

No test failure introduced by this slice's changes. All regressions traced to pre-existing
live-network dependencies unrelated to field_ops.
