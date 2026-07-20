# CUSTOMER-L5-04 — Baseline Verification

Verified against actual repository state and, where possible, actual runtime
behavior — not against prior sprints' final reports.

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 | Complete | Confirmed | Architecture/design-system baseline intact; no regressions found. |
| CUSTOMER-L5-01 | Complete | Confirmed | Startup state machine, route registry, remote-config, deep-link pipeline all present and exercised by 312 pre-existing passing tests. |
| CUSTOMER-L5-02 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Auth/OTP/session/refresh-coordinator/logout-all all real and working against unit tests; live runtime certification still not performed (unchanged constraint, see this sprint's own runtime-evidence.md). |
| CUSTOMER-L5-03 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | Home loads real `/v1/customer/categories` data; module-registry/visibility-evaluator architecture present; category press was a toast stub prior to this sprint (`toastService.info(...)`) — now replaced with real navigation. |

## What Was Actually Found in the Repository

- **Category navigation**: none. `HomeScreen.tsx`'s `handleCategoryPress` called `toastService.info("<name> — details coming soon")`. No `CategoryDetail` route, screen, or query existed.
- **Service navigation**: none. `serviceDetails` was a placeholder route (`access: "module-enabled"`, `productionEnabled: false`, gated behind a remote-config module key `"service-discovery"` that is not defined in any remote-config fixture or default — meaning the route was permanently unreachable even if wired up, since `evaluateModule` fails closed on an unknown module key).
- **Search implementation**: none. `search` was a placeholder route (`productionEnabled: false`), no screen, no query, no API client.
- **Placeholder behavior found and corrected**: `home-api.ts` had a dead, unused `listOfferings` method that was never called by any screen — removed and replaced by `features/category/api/category-api.ts` (single source of truth for the offering endpoints, avoiding a duplicate-implementation situation).
- **Contract mismatches found**: `serviceDetails`'s `access: "module-enabled"` + `featureKey: "service-discovery"` gate meant the route could never become reachable via remote config alone (see repository findings above) — this was a genuine pre-existing configuration bug, not a deliberate gate. Corrected this sprint: `serviceDetails` and `search` are now `access: "authenticated"` (matching `home`'s own precedent), since service discovery is core, always-on functionality, not a remote-toggleable experimental module.
- **Blockers**: none preventing implementation. The real backend contract (see contract-matrix.md) is materially smaller than the sprint spec's aspirational feature list (no subcategories, no search suggestions, no popular searches, no related services, no supported brands, no included/excluded items) — these are documented as MISSING_BACKEND, not built as fakes.
- **Corrective work completed**: fixed the unreachable-route bug (`service-discovery` module-gate), removed the dead `listOfferings` duplicate, added `categoryId` deep-link segment requirement to the `serviceDetails` param type (the real offering-detail endpoint is category-scoped server-side and cannot resolve a service by ID alone).
- **Deferred issues**: see `CUSTOMER-L5-04-known-gaps.md`.

## Runtime Checks (Non-Live)

Startup, auth, Home real-data load, stable category/service IDs, typed
navigation, tenant/locale query-key scoping, cross-customer cache clearing on
logout, locale switching (Accept-Language header fix from CUSTOMER-L5-03),
error normalization, and redacted logging were all re-confirmed by reading
the actual current source and by the 312 pre-existing tests continuing to
pass unmodified after this sprint's changes. No production Home mocks were
found. Live backend runtime proof was not possible in this sandboxed
environment — see `CUSTOMER-L5-04-runtime-evidence.md`.

## Git State

Working tree at the start of this sprint had uncommitted changes in
unrelated engines (`serviceability`, `tenant_engine`) and admin/portal
frontends from other, parallel work streams — none of those files were
touched by this sprint's changes.
