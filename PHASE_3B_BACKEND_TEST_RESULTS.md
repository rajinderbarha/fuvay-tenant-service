# Phase 3B — Backend Test Results

## Command

```bash
python -m pytest tests/ -q
```

## Result

**8022 passed, 37 failed, 1 skipped** (8060 collected, 438.95s).

All 37 failures are the exact same pre-existing, unrelated baseline confirmed
in every prior sprint this session (frontend-assertion tests predating a
concurrent process's nav-config refactor — `test_dynamic_pricing_form.py`,
`test_finance_package_pricing_fix.py`, `test_p0_provider_enterprise.py`,
`test_sprint34a_ui_foundation.py`, `test_sprint34c_master_data.py`,
`test_sprint38_universal_catalog.py`). **0 new failures introduced by Phase 3B.**

## New tests added this sprint

`tests/test_phase3b_backend_routing_certification.py` — **21/21 passed**,
covering:

1. Bargain summary endpoint + 8 KPI keys
2. Bargain list enrichment (names + price context)
3. Bargain detail endpoint exists
4. Duplicate active bargain rule rejection
5-6. Invalid floor (below min / above max) validation
7. Inactive-rule readiness warning string
8. Validate bargain rule endpoint + 5 checks
9. Bargain audit endpoint
10-11. Evaluate decision shape (rejected/accepted reasons)
12. Evaluate audit logging
13. Override summary endpoint + 8 KPI keys
14. Override list tenant_name resolution
15. Override list service context + platform bounds
16-18. Override validation error codes (`OVERRIDE_BELOW_PLATFORM_MIN`/`OVERRIDE_ABOVE_PLATFORM_MAX`) + context fields
17. Validate-preview endpoint exists
19. Duplicate active override rejection
20. Override audit endpoint
21. Permission constants + all new endpoints wired to `require_permission`
22. OpenAPI route declarations present + forbidden-label scan

## Fixed as part of this sprint

`tests/test_phase3_pricing_rules_certification.py::test_provider_override_enforces_platform_min_max`
was updated to assert the new `OVERRIDE_BELOW_PLATFORM_MIN`/`OVERRIDE_ABOVE_PLATFORM_MAX`
error codes instead of the old `OVERRIDE_BELOW_MIN`/`OVERRIDE_ABOVE_MAX` — this
was an intentional, ticket-required rename, not a regression. Full file:
18/18 passing after the update.

## Live end-to-end verification (real backend + real Postgres)

Performed directly via `curl` against a freshly restarted backend — see
`PHASE_3B_BACKEND_ROUTER_REPORT.md` for the full request/response evidence.
Summary: all 20 new/extended endpoints returned correct, real data; the
₹500/₹650 bargain evaluation and ₹500/₹1300 override validation scenarios
matched the ticket's exact expected JSON shapes field-for-field.

## Result: **PASS — 0 new regressions, all new backend tests green.**
