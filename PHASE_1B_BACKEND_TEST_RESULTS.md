# Phase 1B — Backend Test Results

## Command

```bash
pytest tests/ -q
```

## Result

**7981 passed, 37 failed, 1 skipped** (out of 8019 collected).

All 37 failures are the exact same pre-existing, unrelated baseline
confirmed in Phase 0, Phase 1, and re-confirmed again here (catalog/pricing
form/brand-flow frontend-assertion tests predating a concurrent process's
nav-config refactor — see `PHASE_0_TEST_RESULTS.md` for the full list).
**0 new failures.**

New tests added this sprint:
`tests/test_phase1b_admin_setup_closure.py` — **9/9 passed**, covering:
- Roles list/detail endpoints exist
- All 10 required roles present
- Role mutations correctly return 501 (not fake success)
- Permissions list/grouped endpoints exist
- All endpoints require `super_admin`
- Permission-count consistency regression (list vs detail) fixed and guarded
- 500 test route is dev-only, auth-gated
- Login-events endpoint remains mounted per the keep decision

Total new tests across Phase 1 + Phase 1B this session:
`test_phase1_admin_setup_certification.py` (14) +
`test_phase1_admin_setup_certification_frontend.py` (8) +
`test_phase1_admin_setup_frontend_backend_certification.py` (4) +
`test_phase1b_admin_setup_closure.py` (9) = **35 tests, all passing.**

## No regressions in prior modules

Auth, Platform Settings, Engine Management, Vertical Configuration, and
Audit Logs test coverage from Phase 1 was not touched this sprint and
continues to pass (re-confirmed via the full suite run above).
