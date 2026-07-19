# Frontend Test Plan

All tests are written in `frontend/super-admin/__tests__/ux02/` against the vitest +
@testing-library/react API already used by `frontend/packages/design-system`. NOT executed (MODE
B) — see `frontend-test-report.md`.

| Test file | Covers |
|---|---|
| `nav-ia.test.ts` | Only canonical roles referenced; unique nav item ids; every item has a readiness state. |
| `fixtures.test.ts` | Fixture shape/data sanity (see file for exact assertions). |
| `enterprise-list-page.test.tsx` | Search filtering, bulk-action impact-preview confirmation (never fires a real mutation), filter chip apply/clear. |
| `patterns.test.tsx` | RoleDashboard per-role widget visibility (finance/security); EnterpriseDetailPage section switching + mobile section-jump select; ReviewApprovalWorkspace reason-gated Reject button + confirm-before-deciding flow. |

## Not yet written (deferred, see `deferred-items.md`)
- Light/dark rendering snapshot tests (would need a themed test harness).
- Explicit keyboard-navigation/focus-order test (tab order across list/detail pages).
- Long/translated-label overflow regression test (currently only demonstrated visually in the
  states gallery, not asserted in a test).
- Audit Explorer JSON-viewer expand/collapse test.

## Commands a future engineer should run once unblocked
```
cd frontend/super-admin
npm install --no-audit --no-fund
npm run test   # if/once a vitest script + config is added to package.json (see below)
```
Note: `frontend/super-admin/package.json` does not currently define a `test` script or vitest
devDependency (only `frontend/packages/design-system` does) — adding both is a prerequisite to
actually running these files, called out in `frontend-test-report.md`.
