# HS4B — Regression Test Results

## New test file
`tests/test_hs4b_bookability_refresh.py` — **22/22 passing**. Covers:
refresh-is-not-a-noop, DB update/insert paths, `last_evaluated_at`
update, real-table reads for every signal, all 5 hard-gate blockers
(service area, availability, usage credits, security deposit,
suspended tenant), the `is_bookable` conjunction logic, response shape
(`passed_checks`/`failed_checks`/`status`), frontend refresh-after-
publish wiring, bookable/not-bookable copy, and forbidden labels.

## Combined wizard regression
```
pytest tests/test_p0_tenant_service_setup_wizard.py tests/test_home_services_menu_and_price_range.py tests/test_tenant_menu_cleanup.py tests/test_tenant_home_services_service_setup_wizard.py tests/test_tenant_home_services_vertical_detection_fix.py tests/test_type_dependent_brand_pricing.py tests/test_hs4b_bookability_refresh.py -q
```
**164 passed, 0 failed** (142 pre-existing + 22 new).

## Broader provider/bookability sweep
```
pytest tests/ -k "provider_status or provider_portal or bookab or visibility" -q
```
**51 passed, 0 failed.**

## Full provider-portal regression
```
pytest tests/ -k "sprint12 or provider" -q
```
**349 passed, 6 failed** — all 6 confirmed pre-existing/unrelated
(admin provider onboarding pages, nav-config schema drift — none touch
`app/engines/provider_portal/router.py`, the only backend file modified
this sprint).

## TypeScript
`npx tsc --noEmit` (tenant-portal) — **0 errors**.

## Live verification
See `HS4B_LIVE_CURL_VERIFICATION_REPORT.md` — 6 distinct real scenarios,
all correct.

## Verdict
All HS4B-scoped and regression tests passing. Zero regressions
introduced by the fix (confirmed across 4 separate test sweeps totaling
586 test executions).
