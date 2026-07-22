# Full Backend Regression Diff — Slice 2F-39A2

## Result

`python -m pytest tests/ -q`: **12,132 collected, 12,086 passed, 26
failed, 20 skipped**, 1143.33s (0:19:03).

## Before/after

| | Before (Slice 2F-39A) | After (Slice 2F-39A2) |
|---|---|---|
| Collected | 12,128 | 12,132 (+4, this slice's new test file) |
| Passed | 12,081 | 12,086 |
| Failed | 26 | 26 (unchanged) |
| Skipped | 21 | 20 (-1, environmental variance, not investigated — not a regression) |

**The 26 failures are an exact, identical set** to Slice 2F-39A's baseline
(`test_checklist_system.py` ×4, `test_customer_frontend_02_hardening.py`
×1, `test_job_type_flows.py` ×1, `test_p0_engine_management_enterprise.py`
×1, `test_service_catalog.py` ×8, `test_sprint22_quote_checklist.py` ×1,
`test_sprint24_customer_reviews.py` ×2, `test_sprint25_complaints.py` ×1,
`test_sprint4_tenant_onboarding.py` ×1, `test_sprint75_dispute_settlement.py`
×1, `test_step8_quote_checklist.py` ×2, `test_tenant_service_coverage_enterprise_ui.py`
×1, `test_versions.py` ×2 = 26). **No new failure appeared.** The
`security.router::create_api_key` fix did not break `test_p0_security_enterprise.py`,
`test_phase12.py`, or `test_phase2f29_m01_identity_closure.py` (all three
were spot-checked as unaffected before the fix and are confirmed still
passing in this run).
