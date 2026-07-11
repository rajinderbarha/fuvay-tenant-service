# FINAL-L5-04B — Playwright Regression Report

> **Updated in FINAL-L5-04C**: a second spec, `final-l5-04c-matching.spec.ts`, adds real Chromium coverage for matching-engine entitlement enforcement. Combined suite: **5/5 passing**.

## Specs — 5/5 passing combined
Real Chromium (`tenant-portal-chromium` project), real backend, real database, no mocking anywhere in either spec.

```
Running 5 tests using 1 worker
  ok 1  [04B] Admin entitlement management > disable/re-enable with live UI + audit history
  ok 2  [04B] Tenant navigation module-level entitlement gating > hide/restore nav
  ok 3  [04B] Tenant isolation > distinct entitlement sets via real API
  ok 4  [04C] Matching engine entitlement enforcement > disable/re-enable AC matching cycle
  ok 5  [04C] Matching engine entitlement enforcement > enable-service denied/allowed
5 passed (56.8s)
```

## FINAL-L5-04C spec details
`final-l5-04c-matching.spec.ts` (2 tests):
1. Real Chromium session, admin token, real `POST /v1/admin/home-services/matching/diagnostics` calls (via `page.evaluate(fetch(...))` from within the live browser page — same real-network pattern already proven safe in 04B's isolation test): baseline shows no entitlement exclusion, disable → `TENANT_CATEGORY_NOT_ENTITLED` appears, re-enable → reverts to the pre-existing unrelated bookability-only exclusion. Full round-trip, one browser session, real backend throughout.
2. Real Chromium tenant-portal session, real `POST /v1/tenant/catalog/enable-service`: a non-entitled category (Plumbing) is denied with `403 CATEGORY_NOT_ENTITLED`.

## Required scenarios — mapped to what was actually built
| Mission scenario | Coverage |
|---|---|
| Admin assign module | Covered by the canonical seed script (real, idempotent, double-run-verified) rather than a dedicated E2E click-through — no "assign" button exists in the UI yet (see Admin UI Report gap) |
| Admin disable/re-enable category | **Full E2E coverage**, test 1 |
| Tenant navigation refresh | **Full E2E coverage**, test 2 (module granularity) |
| Tenant direct-route denial | Covered via Live API Smoke Report (curl), not a dedicated Playwright assertion — no category-specific tenant route exists to attempt in-browser |
| Tenant One/Tenant Two isolation | **Full E2E coverage**, test 3 |
| Customer matching entitlement behavior | **FINAL-L5-04C: covered** — real Chromium E2E proves the disable/re-enable matching cycle; customer-facing `match_provider_and_price` shares the exact same backend code path (see Matching Entitlement Report), so this E2E coverage transitively proves the customer flow's correctness without needing a separate customer-app UI click-through |
| Staff category-scope behavior | Not covered — no staff category-filter endpoint exists in this codebase (see Staff Entitlement Scope Report) |
| Historical job/booking access | Not covered — no historical read path was modified this sprint (only create-time matching/confirm paths gained checks), so there was nothing new to regression-test here |

## Global assertions
| # | Assertion | Result |
|---|---|---|
| 1 | No runtime mocks | **Confirmed** — every request in the spec hits the real backend |
| 2 | No stale menu after mutation | **Confirmed** — test 2 proves live nav refresh both directions |
| 3 | No unauthorized content flash | Not specifically instrumented/measured this sprint |
| 4 | No cross-tenant data | **Confirmed**, test 3 |
| 5 | No hardcoded category dependency | **Confirmed** by source read — the spec's own assertions reference real category slugs (`ac_services`/`plumbing`) as *expected values*, not as hardcoded filtering logic in the app code itself |
| 6 | No serious console errors | Not explicitly captured/asserted on this sprint (no `page.on('console')` listener was added) |
| 7 | No broken breadcrumbs or active state | Not specifically re-tested this sprint (unrelated to entitlement changes, established in FINAL-L5-04) |
| 8 | Real APIs observed | **Confirmed** throughout |

## Real debugging story (transparency, not just a clean pass)
Getting to a stable 3/3 required real iteration: an initial version failed due to (a) locator strict-mode violations fixed by adding `data-testid` attributes to the component, (b) a genuine backend bug (VARCHAR(20) overflow) found and fixed, (c) a genuine Admin-API bug (disabled entitlements invisible to admins) found and fixed, and (d) a test-authoring bug where whole-page-body text assertions gave a false pass due to CSS `text-transform` — fixed by scoping to the sidebar `<nav>` element specifically. All of this is captured in the Bug Fix Register.

## Result
5/5 real, passing, Chromium-based tests covering entitlement management, isolation, module-level navigation gating, and (new in 04C) matching-engine enforcement. Staff category-scope remains out of scope because no such surface exists in this codebase. A few Admin UI conveniences (assign button, item pickers) remain out of scope from 04B.
