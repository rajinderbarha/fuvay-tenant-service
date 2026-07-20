# Deferred Items — explicit accounting against the 38-workstream brief

## Done (real, committed, verified)
1. Discovery (Step 0) — package.json, src/ tree, screens, AuthContext, api.ts, transitions.ts read in full.
2. WSL verification setup — npm install succeeded (850 packages), lockfile generated and committed, two real
   install-blocking bugs found and fixed (ERESOLVE peer conflict, dead `@types/react-native` target).
3. Typed view-model contract (`src/types/ux05.ts`) covering all 20 named view models from workstream 25 (as
   TypeScript interfaces; not all have live adapters/screens yet).
4. Canonical role derivation + StaffPermission presentation helpers (workstreams 2/3 groundwork), fail-closed.
5. Four shared components (workstream 27, partial: PipelineBadge, PermissionRestrictedState, NextActionBar,
   PartsRequestStatusCard of the ~22 named).
6. One dev-only showcase screen (Parts Request creation+tracking) exercising the parts-request rules
   (workstreams 14/15/32, partial).
7. Unit tests (workstream 33, partial): 12 real, passing, behavioral assertions — role fail-closed default,
   explicit-deny-overrides-grant, tenant scoping, provenance non-collapse, parts-request technician-action type
   restriction. Not the full role/pipeline/parts/offline/UI test matrix the brief describes.
8. Typecheck run in WSL (workstream 36, partial) — real, found pre-existing unrelated errors, zero errors in
   UX-05 code.
9. Non-change verification (workstream 37) — `git diff --stat` confirms zero changes outside `mobile/staff-app`.
10. This documentation subset (~12 of 72 files).

## Not done (explicit gaps, not silently dropped)
- Navigation/IA rebuild (workstream 2), Home/My Work/Schedule/Work Queue screens (4–7), full pipeline-aware Job
  Detail + Current Job mode (8–9), status transition UI beyond what JobDetailScreen already had pre-UX-05
  (10), customer/address UI (11), inspection/checklist workflows (12–13), Staff Parts Approval screen (16),
  quote presentation (17), job notes/media UI (18–19), notifications/availability/profile rebuilds (20–22),
  offline UI states beyond the documented matrix (23), remaining ~18 shared components (27), remaining ~29
  showcase screens (32), remaining test coverage (33), runtime/Expo-web/Playwright testing (34–35), lint run
  (36 partial — `eslint` script exists but was not executed this pass), most non-regression/build reports (36),
  ~60 of the 72 doc files (38).

## Why the cut was made here, not elsewhere
Given the real budget available in this run, the highest-value order was: get a real WSL toolchain working (a
hard blocker for everything downstream), establish the typed domain-model layer other work depends on, prove the
domain rules with real tests, and document the two most consequential real-evidence findings (no live
pipeline split, no live role/permission field) so a follow-on pass does not have to re-derive them. This is a
partial delivery, not a complete one — reported honestly as `STAFF_TECHNICIAN_APP_DESIGN_PARTIAL`.
