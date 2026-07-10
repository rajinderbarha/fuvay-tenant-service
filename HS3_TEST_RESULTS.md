# HS3 — Test Results

## New test file
`tests/test_hs3_admin_tier_pricing.py` — **15/15 passing**. Covers:
table column order (Type before Brand), backend brand-requires-type
validation, frontend mirror validation, backend duplicate-rule
rejection (including the NULL-tier edge case), backend admin range/
deduction validation, the symmetric price formula against the ticket's
exact example, low/high-includes-fee hard gates, provider boundary
enforcement (tenant side), forbidden labels, and payment-mode wording.

## Regression fix required and applied
Adding the new duplicate-check query to `create_pricing_rule` broke one
pre-existing unit test (`test_sprint3_catalog.py::
test_create_pricing_rule_success`) that used a fixed-length mocked
`db.execute()` call sequence. Fixed by extending the test's mock helper
(`db_seq`) to support `.scalars().first()` and queuing one additional
empty-result mock call — **not** by weakening the new duplicate check.
Verified: `tests/test_sprint3_catalog.py` now 64/64 passing (was 63/64
immediately after the change, before this fix).

## Broader regression sweep
```
pytest tests/ -k "pricing_rule or pricing_rules or type_dependent_brand" -q
```
**56 passed, 0 failed.**

```
pytest tests/ -k "home_services or catalog" -q
```
**640 passed, 11 failed** — all 11 confirmed pre-existing/unrelated
(same 11 documented in the HS2B sprint: `test_brand_flow_improvements.py`
testing an untouched page, plus `AdminLayout.tsx` nav-href assertions).

```
pytest tests/ -k "admin_catalog or catalog_enterprise or master_service or sprint3" -q
```
**1893 passed, 15 failed** — all 15 confirmed pre-existing/unrelated
(same class: `AdminLayout.tsx` nav hrefs, `sprint34a`/`34c` UI-shell
drift, `sprint34k` nav-config schema drift — none touch
`admin_catalog/service.py` or the pricing-rules page).

## TypeScript
`npx tsc --noEmit` — **0 errors**, both frontends.

## Live backend verification (real running server, real DB)
- Brand-without-type on type-based service → `422
  SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING` ✅
- Duplicate Window AC + LG rule → `409
  DUPLICATE_TYPE_BRAND_PRICING_RULE` ✅
- New valid combo (Split AC + Samsung) → `201 Created` ✅
- Migration/cleanup script re-run: found and deprecated 1 new invalid
  global-brand rule created during this session's own testing activity.

## Verdict
All HS3-scoped and regression tests passing. TypeScript clean. Two real
backend gaps found and fixed, live-verified against the real system.
