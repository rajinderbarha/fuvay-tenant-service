# HS4 — Test Results

## Combined wizard-scoped regression
```
pytest tests/test_p0_tenant_service_setup_wizard.py tests/test_home_services_menu_and_price_range.py tests/test_tenant_menu_cleanup.py tests/test_tenant_home_services_service_setup_wizard.py tests/test_tenant_home_services_vertical_detection_fix.py tests/test_type_dependent_brand_pricing.py -q
```
**142 passed, 0 failed.**

## TypeScript
`npx tsc --noEmit` (tenant-portal) — **0 errors**.

## Live backend verification (real server, real DB, this sprint)
- Provider price below admin min → **422
  `TENANT_PRICE_BELOW_ADMIN_MIN`**, correct message, `request_id`
  present. ✅
- Provider price above admin max → **422
  `TENANT_PRICE_ABOVE_ADMIN_MAX`**, correct message, `request_id`
  present. ✅
- Publish (all required checks satisfied) → **200,
  `setup_status: "published"`, `published_at` set.** ✅
- `GET /v1/provider/status` + `POST /v1/provider/status/refresh` after a
  real publish → **`is_visible`/`is_bookable` remained `false`,
  `last_evaluated_at` remained `null`** — real bug found (see Remaining
  Blockers), not a test failure but a live-discovered defect.

## No new tests added this sprint
This sprint's work was verification + one real bug discovery (status/
readiness not updating after publish), not new frontend/backend code —
existing test coverage (142 tests across 6 files) was re-run and
confirmed still passing; no regressions introduced since no code was
changed.

## Verdict
All existing wizard-scoped tests passing. TypeScript clean. One new
real bug found via live testing (documented, not test-covered yet).
