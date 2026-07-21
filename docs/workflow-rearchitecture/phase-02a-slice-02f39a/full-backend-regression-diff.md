# Full Backend Regression Diff — Slice 2F-39A

## Result

`python -m pytest tests/ -q`: **12,128 collected, 12,081 passed, 26
failed, 21 skipped**, 966.18s (0:16:06).

## Before/after

| | Before (Slice 2F-39) | After (Slice 2F-39A) |
|---|---|---|
| Collected | 12,124 | 12,128 (+4, this slice's new test file) |
| Passed | 12,075 | 12,081 |
| Failed | 28 | 26 |
| Skipped | 21 | 21 (unchanged) |

**Both `test_sprint27_notifications.py` failures are gone** — confirmed
resolved, not merely absent from this particular run (both runs of the
Phase-2F suite also show that file's 44/44 passing).

## Remaining 26 failures

Identical set to Slice 2F-39's `remaining-failure-disposition.csv` minus
the 2 notification tests — no new failure appeared, no previously-passing
test broke:

`test_checklist_system.py` (4), `test_customer_frontend_02_hardening.py`
(1), `test_job_type_flows.py` (1), `test_p0_engine_management_enterprise.py`
(1), `test_service_catalog.py` (8), `test_sprint22_quote_checklist.py` (1),
`test_sprint24_customer_reviews.py` (2), `test_sprint25_complaints.py` (1),
`test_sprint4_tenant_onboarding.py` (1), `test_sprint75_dispute_settlement.py`
(1), `test_step8_quote_checklist.py` (2), `test_tenant_service_coverage_enterprise_ui.py`
(1), `test_versions.py` (2) = 26.

All 26 are exactly the pre-existing domain-logic/frontend-version-pin/
TypeScript-compile failures Slice 2F-39 already dispositioned as
`PRE_EXISTING_VERIFIED_NON_AUTHORIZATION`, `DOMAIN_REMEDIATION_REQUIRED`,
or `ENVIRONMENT_REQUIRED` — none are new, none are authorization-relevant,
and none are this slice's scope to resolve (route census + the 2
notification tests were this slice's exclusive ownership).

## No new unexplained failure

Confirmed: the 26 remaining node IDs are a strict subset of the 28
Slice 2F-39 already accounted for. Nothing else regressed.
