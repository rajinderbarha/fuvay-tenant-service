# CUSTOMER-L5-03 — Test Evidence (Deepened Pass)

```
npx jest
Test Suites: 46 passed, 46 total
Tests:       312 passed, 312 total
```

(291 carried over from the CUSTOMER-L5-00/01/02/03-first-pass baseline, 21
new this deepened pass.)

## New Test Files (this pass)

| File | Count | Covers |
|---|---|---|
| `features/home/domain/__tests__/module-visibility.test.ts` | 8 | all reachable `ModuleVisibilityOutcome`s, `filterVisibleModules` ordering/filtering |
| `features/home/domain/__tests__/module-registry.test.ts` | 3 | known-type recognition, unknown-type safe skip, empty-string edge case |
| `features/home/queries/__tests__/home-query-keys.test.ts` | 4 | locale/tenant key scoping, distinctness, stable placeholder for absent tenant |
| `api/__tests__/request-context.test.ts` | 5 | locale default, locale mutation, header reflects locale, tenant default, header reflects tenant |

## Regression Confirmation

All 291 tests from before this pass (CUSTOMER-L5-00 through the first
CUSTOMER-L5-03 pass and the deepened CUSTOMER-L5-02 pass) continue passing
unmodified, including `route-guards.test.ts`, `startup-route-resolver.test.ts`,
and every `remote-config`/`deep-link`/`auth` suite — none needed adjustment
for this pass's changes (locale-header fix, query-key scoping,
module-registry addition).

## Not Covered This Pass

- No component tests for `HomeScreen`/`CategoryGrid`/`CategoryCard` —
  consistent with every previous sprint's identical, explicitly-stated
  deprioritization in favor of pure-logic coverage.
- No true integration test against a real/mocked HTTP server for the full
  `resolveModuleRenderer` → `evaluateModuleVisibility` →
  `useHomeCategories` chain end-to-end within a rendered `HomeScreen`.
- No live runtime proof — see `CUSTOMER-L5-03-runtime-evidence.md`.
- No tenant-isolation test with real data (single-tenant environment).
