# HS9 — Test Results

## Targeted backend sweep
```
pytest tests/ -k "assignment or execution or sprint20 or sprint21 or home_service_booking or hs7 or hs8 or tenant_engine or provider_portal" -q
```
**295 passed, 0 failed** — includes all HS8/HS8B tests plus this pass's
`tenant_engine`/`provider_portal` additions, no new test file added this
pass (no dedicated `test_hs9_*.py` was written — see Remaining Blockers).

## TypeScript / build / lint / frontend tests
Not run — no frontend code was touched this pass (see
`HS9_TENANT_FINANCE_IMPACT_REPORT.md` / `HS9_ADMIN_FINANCE_VISIBILITY_REPORT.md`
for the documented UI gaps).

## Verdict
Backend: clean, 295/295 passing, zero regressions from HS9's changes
(deduction wiring, new ledger table/endpoints, one job-transition-graph
bug fix).
