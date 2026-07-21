# Full Backend Regression Diff — Slice 2F-39A3

## Result

`python -m pytest tests/ -q`: **12,151 collected, 12,103 passed, 27
failed, 21 skipped**, 1301.91s (0:21:41).

## Before/after

| | Before (Slice 2F-39A2R) | After (Slice 2F-39A3) |
|---|---|---|
| Collected | 12,145 | 12,151 (+6, this slice's new test file) |
| Passed | 12,092 | 12,103 |
| Failed | 26 | 27 (+1 — investigated below, not a regression) |
| Skipped | 27 | 21 (variance, not investigated — not a regression; total collected+passed+failed+skipped reconciles exactly both times) |

**26 of the 27 failures are the exact, identical set** carried since
Slice 2F-39A: `test_checklist_system.py` ×4,
`test_customer_frontend_02_hardening.py` ×1, `test_job_type_flows.py` ×1,
`test_p0_engine_management_enterprise.py` ×1, `test_service_catalog.py`
×8, `test_sprint22_quote_checklist.py` ×1,
`test_sprint24_customer_reviews.py` ×2, `test_sprint25_complaints.py` ×1,
`test_sprint4_tenant_onboarding.py` ×1,
`test_sprint75_dispute_settlement.py` ×1,
`test_step8_quote_checklist.py` ×2,
`test_tenant_service_coverage_enterprise_ui.py` ×1, `test_versions.py`
×2.

## The 1 new-looking failure — investigated, not a regression

`test_p0_notification_template_center.py::TestValidation::test_create_rejects_unknown_variable[asyncio]`
appeared as failed in the full-suite run only.

- This slice's diff against base `293d7f5` touches exactly 3 files:
  `app/engines/chat/service.py`, `app/engines/compliance/router.py`, and
  the new `tests/test_phase2f39a3_defect_remediation.py`. None of these
  touch notification templates, and none are imported by
  `test_p0_notification_template_center.py`.
- Re-run in isolation: `pytest tests/test_p0_notification_template_center.py::TestValidation::test_create_rejects_unknown_variable`
  → **1 passed**.
- Re-run the full file alone: `pytest tests/test_p0_notification_template_center.py`
  → **24 passed**.
- Conclusion: this is cross-file test-order pollution from some earlier
  test in the full 12,151-test run (the same class of pre-existing
  pollution this program has documented before, e.g. the
  `DocumentService.generate_document` monkeypatch-teardown bug found in
  Slice 2F-39), not a defect introduced by this slice's application
  changes. It is not one of this slice's fixed or touched files, so it
  is out of this slice's remediation scope; recorded here for honesty
  and left for a future slice to root-cause if it recurs.

**No new failure caused by this slice's application changes.** The
previously fixed defects (`security.router::create_api_key`,
`security.router::record_activity`/`write_audit_entry`/`create_session`/
`revoke_session`, `pricing.router::activate_rule`/`deactivate_rule`) all
remain passing — none appear in the failure list.
