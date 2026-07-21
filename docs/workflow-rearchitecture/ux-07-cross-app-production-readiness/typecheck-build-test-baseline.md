# Typecheck/Build/Test Baseline — Round 2 (Workstream 3)

All commands run in WSL against the freshly-installed copies described in
`dependency-install-report.md`.

## mobile/customer-app

- `npx tsc --noEmit`: **0 errors**.
- `npx jest --ci` (default parallel workers): 47/48 passed, 1 failed
  (`AuthContext.test.tsx`, "starts logged-out with no stored token" —
  `Exceeded timeout of 10000ms`).
- Reproduction: ran the same file in isolation (`npx jest
  src/context/__tests__/AuthContext.test.tsx --ci`) -> **4/4 passed**, fastest
  assertion took 590ms. Ran the full suite again with `--runInBand`
  (single worker, no parallel contention) -> **48/48 passed** in 2.6s total.
  **Conclusion: this is a real, reproducible parallel-worker resource-
  contention flake specific to this constrained WSL environment's default
  multi-worker Jest scheduling, not a logic defect in `AuthContext.tsx` or
  its test.** Not fixed by adding a retry (explicitly disallowed) — the
  correct fix would be tuning Jest's worker count or the test's own timeout
  margin, which was not done this round to avoid masking a real signal with
  an unverified tuning change; disclosed here instead.
- Build: not run (Expo app — no `next build` equivalent meaningfully
  distinct from install+typecheck+test for this app family; deferred).

## mobile/staff-app

- `npx tsc --noEmit`: **18 errors across 8 files** — ALL pre-existing
  (verified: no file in this list was touched in Round 1 or Round 2; this
  is baseline debt, not introduced this round). Breakdown:
  - `src/components/Skeleton.tsx` (3 errors): string-literal percentage
    values (`"50%"`, `"35%"`, `"60%"`) not assignable to a prop typed
    `number | "100%" | undefined`.
  - `src/components/SlaTimer.tsx` (1 error): imports a non-existent
    `getSlaStatus` from `../lib/transitions` — a real, dangling import
    (the function was apparently removed/renamed from `transitions.ts` at
    some point without updating this consumer). Out of this round's scope
    (SLA/status-transition certification is explicitly deferred per the
    brief) but flagged in `known-limitations.md`.
  - `src/navigation/AppNavigator.tsx` (3 errors): screen component prop
    typing mismatches (`{route}` destructured components not matching
    `ScreenComponentType`).
  - `src/screens/{ChatListScreen,HomeScreen,JobsListScreen,ux05/ScheduleScreen}.tsx`
    (4 errors): a `[never, never]` tuple-argument typing issue, likely from
    a shared hook's generic inference breaking under this exact
    TypeScript/React Navigation version combination.
  - `src/screens/{ChatRoomScreen,JobDetailScreen,NotificationsScreen,ux05/CurrentJobScreen}.tsx`
    (6 errors): a `(...args: unknown[])` vs specific-typed-callback mismatch,
    same likely root cause as above.
  - None of these are in files this round or Round 1 touched.
- `npx jest --ci --runInBand`: **56/56 passed**, 12 suites, no flakiness —
  the typecheck errors above do not correspond to any actually-broken
  runtime behavior the test suite exercises.

## frontend/tenant-portal

- `npx tsc --noEmit`: **13 errors before the `@testing-library/dom` fix**
  (all in `__tests__` files, all `Module '"@testing-library/react"' has no
  exported member 'screen'/'fireEvent'`) -> **0 errors after** the fix
  described in `dependency-install-report.md`/`frontend-corrections-report.md`.
- `npm test` (`vitest run`): before the fix, 12/16 suites failed outright
  (`Cannot find module '@testing-library/dom'`), 4/16 passed (20 tests).
  After the fix: **13/16 suites passed (42 tests), 3/16 still failed
  (11 tests)** — real, reproducible `Invalid hook call` errors in
  `PartsRequestList`/`PartsRequestSummary`/other `ux04` component tests.
  Root-caused to a genuine duplicate-React-instance problem: this npm
  workspace hoists `react@19.2.0` at the root (matching
  `frontend/super-admin`'s pin), but `frontend/tenant-portal/package.json`
  itself pins `react: 19.2.7`/`react-dom: 19.2.7` — a real version
  mismatch between the two workspace apps (both use the same
  `next: 16.2.9`, so this is not an obviously-required differing peer
  constraint) that prevents npm from deduplicating a single React copy,
  producing the exact same class of bug as the UX-05
  react-test-renderer-duplicate-instance incident recorded in this
  project's memory. **Not fixed this round**: changing either app's React
  pin without being able to fully rebuild+re-verify both apps' production
  builds against the new pin would risk introducing a real regression,
  which the brief explicitly prohibits ("do NOT ... alter package versions
  merely to make one local environment pass"). Documented as a real,
  precise, actionable finding for a future round instead.
- Build (`next build`): not run this round (time budget — typecheck+test
  were prioritized as higher-signal per the brief's ordering).

## frontend/super-admin

- `npx tsc --noEmit`: **0 errors**.
- `npm test`: **no `test` script exists** in `package.json` (only
  `dev`/`build`/`start`/`lint`) despite 4 real `*.test.tsx` files existing
  under `__tests__/`. Ran `npx vitest run` directly as a workaround ->
  2/4 files passed (13 tests, 5 passed/8 failed) — the 2 failing files
  errored with `ReferenceError: document is not defined`, because no
  `vitest.config` exists for this app to set `environment: "jsdom"` (unlike
  tenant-portal, which has one). **Real, pre-existing test-infrastructure
  gap**: super-admin's test suite was never fully wired up (missing both
  the `test` script and a jsdom-environment vitest config) — not fixed this
  round (a vitest config addition is arguably in-scope as a "missing
  loading state"-class frontend fix, but was judged lower priority than the
  tenant-portal fix given the time remaining this round; logged as a
  deferred enhancement).
- Build (`next build`): not run this round (same time-budget reasoning as
  tenant-portal).

## Summary table

| App | Typecheck | Unit/Component Tests | Build |
|---|---|---|---|
| customer-app | 0 errors | 47/48 (parallel) -> 48/48 (serial/isolated) — real flake, not a defect | not run |
| staff-app | 18 pre-existing errors (unrelated files) | 56/56 | not run |
| tenant-portal | 13 errors -> 0 after fix | 0/16 usable -> 13/16 passing (42 tests) after fix; 3/16 still blocked by a real React-version-duplication defect | not run |
| super-admin | 0 errors | no test script; ad hoc vitest run: 2/4 files, 5/13 tests (missing jsdom env) | not run |
