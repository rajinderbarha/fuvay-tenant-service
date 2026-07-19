# Prerequisite Bug Fix Report

## Fix 1 & 2 (carried forward unchanged from UX-04A, kept exactly as-is)

1. `frontend/packages/design-system/src/components/Tooltip.tsx` —
   `TooltipProps.children` narrowed to accept `aria-describedby` for
   `React.cloneElement` type-checking. Not reverted, not broadened.
2. `frontend/tenant-portal/app/dev/ux-03/permission-editor/page.tsx` —
   added missing `"use client"` directive. Not reverted, not broadened.

## Fix 3 (new this pass)

- **Defect**: 4 pre-existing test files
  (`PermissionEditor.test.tsx` x2, `SetupWizard.test.tsx` x2) failed with
  `TypeError: Cannot read properties of null (reading 'useState')`.
- **Root cause**: exact-version pin mismatch (`react@19.2.0` pinned in
  `frontend/tenant-portal/package.json` vs. `react@19.2.7` resolved
  everywhere else in the workspace via design-system's unpinned peer
  range) caused npm to nest a second, separate React module instance
  local to `frontend/tenant-portal`, producing two live React module
  instances in the same test's module graph — a dual-package-instance
  hazard, not a component logic bug. Introduced at UX-01 commit `487ff92`.
  Full investigation in `four-failure-root-cause-report.md`.
- **Fix**: `frontend/tenant-portal/package.json` — `"react"`/`"react-dom"`
  changed from exact `"19.2.0"` to exact `"19.2.7"` (matching the
  version already resolved for every other consumer in the workspace, so
  npm's installer converges on one shared copy instead of nesting a
  second one). Also added `resolve.dedupe: ["react", "react-dom"]` to
  `vitest.config.ts` as defense-in-depth (harmless if already deduped,
  protective if a future dependency reintroduces a split).
- **Why backward-compatible**: 19.2.7 is a patch-level bump within the
  same minor (19.2.x) already used by every other package in this
  workspace and by React 19's own stable release line; no API used by
  tenant-portal code changed between 19.2.0 and 19.2.7. `npx tsc
  --noEmit` and `npx next build` both remained clean after the bump (see
  `typecheck-report.md`, `tenant-build-report.md`).
- **Tests**: no test assertions were changed, weakened, skipped, or
  disabled. The 4 previously-failing tests now pass with their original,
  unmodified assertions (one incidental fix was needed in a *new*
  UX-04B test, `FieldOpsJobDetail.test.tsx`, for an unrelated
  multiple-elements-matched query ambiguity — see
  `test-repair-report.md`).
- **Evidence**: `npx vitest run`, re-run 3 times post-fix, consistently
  reports 0 failures across all tracked test files (see
  `automated-test-report.md`).
