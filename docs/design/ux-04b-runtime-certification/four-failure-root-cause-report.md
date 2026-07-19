# Four-Failure Root-Cause Report

## Symptom (identical on every run, verified fresh 3 times this pass)

`components/ux03/__tests__/PermissionEditor.test.tsx` (2 tests) and
`components/ux03/__tests__/SetupWizard.test.tsx` (2 tests) failed with:

```
TypeError: Cannot read properties of null (reading 'useState')
 ❯ Proxy.process.env.NODE_ENV.exports.useState node_modules/react/cjs/react.development.js:1263:33
 ❯ SetupWizard components/ux03/patterns/SetupWizard.tsx:35:29
 ❯ react-dom-client.development.js renderWithHooks / updateFunctionComponent / beginWork
```

## Investigation

1. Both failing files render a component that (a) calls `useState`
   directly, and (b) imports something from `@serviceos/design-system`
   (`SetupWizard` imports `PageHeader`; `PermissionEditor` imports `Card`).
   Every UX-04/UX-04A test file that passed either doesn't call a hook at
   all, or doesn't import design-system — this was the first clue.
2. `find /root/.../frontend/tenant-portal -maxdepth 3 -type d -name react`
   showed a **second, physically separate** `react` package nested inside
   `frontend/tenant-portal/node_modules/react`, distinct from the hoisted
   `node_modules/react` at the workspace root.
3. Version check: root hoisted copy was `react@19.2.7`; the nested
   tenant-portal-local copy was `react@19.2.0`.
4. `npm explain react --workspace=frontend/tenant-portal` confirmed:
   tenant-portal's own `package.json` pinned `"react": "19.2.0"` and
   `"react-dom": "19.2.0"` as **exact versions** (no `^`/`~`), while
   `@serviceos/design-system`'s only constraint is a peerDependency
   `"react": ">=19.0.0"` — an unpinned range that let npm resolve/hoist
   the newer `19.2.7` at the root for every OTHER consumer
   (`@testing-library/react`, `next`, `recharts`, etc.), leaving
   tenant-portal's own exact `19.2.0` pin unsatisfiable by the hoisted
   copy, forcing npm to nest a second physical copy just for
   tenant-portal.
5. Result: when a tenant-portal file (`SetupWizard.tsx`) calls `useState`
   from its own nested `react@19.2.0`, but `react-dom`'s render loop (also
   nested at `19.2.0` — consistent with itself) invokes rendering through
   a fiber/dispatcher chain that, for reasons tied to how Vitest/Vite's
   module graph resolves the `@serviceos/design-system` cross-package
   import (a TS source file outside `node_modules`, resolved via a
   `tsconfig.json` path alias), ends up loading a *different* module
   instance of `react` than the direct import — two React module
   instances = two internal dispatcher singletons = the internal
   dispatcher `useState` calls into is `null` for whichever instance
   wasn't the one `react-dom` initialized.
6. `git blame`/`git log --follow -p -- frontend/tenant-portal/package.json`
   confirms the exact `"react": "19.2.0"` pin was introduced at **UX-01
   commit `487ff92`** ("UX-01: add shared design-system foundation for
   super-admin + tenant-portal") — long before UX-04/04A/04B, and before
   any test runner even existed for this workspace (UX-04A added the
   first vitest config, which is why this defect was never observed
   until now).

## Classification

**PRE_EXISTING_SOURCE_DEFECT**, introduced at UX-01 (`487ff92`), never
previously observable because no test runner existed for
`frontend/tenant-portal` before UX-04A. Not a UX04A_REGRESSION (UX-04A
didn't create the version mismatch, only surfaced it by finally running a
test that exercises `useState` + a design-system import together). Not
`INVALID_TEST_ASSUMPTION` — the tests' expectations about component
behavior were correct; the environment beneath them was broken.

## Fix (smallest correct change, verified)

Changed `frontend/tenant-portal/package.json`'s `"react"`/`"react-dom"`
from the exact pin `"19.2.0"` to the exact pin `"19.2.7"` — matching the
version already resolved everywhere else in the workspace. (A caret range
`"^19.2.0"` was tried first and did NOT fix it, because the already-tracked
`frontend/tenant-portal/package-lock.json` — a stray committed nested
lockfile, present since the same UX-01 commit — still satisfied the range
with the stale `19.2.0` resolution and npm had no reason to re-resolve.
Only pinning the exact version that's already resolved elsewhere, forcing
npm's installer to converge, worked.) Verified: after this change +
reinstall, `require.resolve('react', {paths:['.../tenant-portal']})`
returns the **hoisted root path**, not a nested one — zero duplicate React
module instances remain. Re-ran the full suite 3 times after the fix:
**all 4 previously-failing tests now pass consistently, and no other test
regressed.**

See `prerequisite-bug-fix-report.md` for the full defect/root-cause/fix/
tests/evidence record in the standard format.
