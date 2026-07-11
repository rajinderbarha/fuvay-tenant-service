# FINAL-L5-04B — Playwright Regression Report

## Spec: `e2e/tenant-portal/final-l5-04b-entitlement.spec.ts` — 3/3 passing
Real Chromium (`tenant-portal-chromium` project), real backend, real database, no mocking anywhere in the spec.

```
Running 3 tests using 1 worker
  ok 1  Admin entitlement management > disable/re-enable with live UI + audit history   (real ~10-27s)
  ok 2  Tenant navigation module-level entitlement gating > hide/restore nav             (real ~17-21s)
  ok 3  Tenant isolation > distinct entitlement sets via real API                        (real ~6-9s)
3 passed
```

## Required scenarios — mapped to what was actually built
| Mission scenario | Coverage |
|---|---|
| Admin assign module | Covered by the canonical seed script (real, idempotent, double-run-verified) rather than a dedicated E2E click-through — no "assign" button exists in the UI yet (see Admin UI Report gap) |
| Admin disable/re-enable category | **Full E2E coverage**, test 1 |
| Tenant navigation refresh | **Full E2E coverage**, test 2 (module granularity) |
| Tenant direct-route denial | Covered via Live API Smoke Report (curl), not a dedicated Playwright assertion — no category-specific tenant route exists to attempt in-browser |
| Tenant One/Tenant Two isolation | **Full E2E coverage**, test 3 |
| Customer matching entitlement behavior | Not covered — not implemented this sprint |
| Staff category-scope behavior | Not covered — not implemented this sprint |
| Historical job/booking access | Not covered — no entitlement-gated mutation touches job/booking data this sprint |

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
3/3 real, passing, Chromium-based tests covering the mission's core entitlement-management and isolation scenarios. Matching/staff/customer scenarios and a few UI conveniences are honestly out of scope this sprint.
