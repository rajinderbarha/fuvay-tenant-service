# HS5B — Test Results

## New test file
`tests/test_hs5b_availability_exceptions_coverage.py` — **26/26 passing**.
Covers migration schema, break-time validation, exceptions CRUD,
booking-window validation, per-area coverage validation, and the
matching-input readiness function.

## Regression
```
pytest tests/test_hs5_service_areas_availability.py tests/test_hs4b_bookability_refresh.py tests/test_tenant_service_coverage_enterprise_ui.py -q
```
**82/82 passing.**

```
pytest tests/ -k "availability or service_area or serviceability or provider_status or bookab or hs5 or hs4b" -q
```
**202 passed, 0 failed.**

## TypeScript
0 errors (no frontend files modified this sprint).

## Live verification
See `HS5B_LIVE_CURL_VERIFICATION_REPORT.md` — all 12 required scenarios
passed, including one real bug found and fixed mid-sprint.

## Verdict
All HS5B tests passing, zero regressions across 310 total test
executions this sprint (26 new + 82 + 202 overlapping sweeps).
