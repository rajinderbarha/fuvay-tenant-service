# UX-05 Implementation Summary

Branch `design/ux-05-staff-technician-app`, based on UX-04B `7488335`. Target: `mobile/staff-app/` (Expo ~56,
React Native 0.85, React 19.2, React Navigation v7).

## What this pass built
1. Fixed two real WSL npm-install blockers and produced the app's first-ever `package-lock.json`.
2. Added `typecheck`/`test`/`web` scripts and a jest-expo + RNTL test toolchain (previously no test framework
   existed at all).
3. `src/types/ux05.ts` — the full typed view-model contract from workstream 25, with one significant
   real-evidence correction over the brief's illustrative example: this app's job surface is already
   single-pipeline (`service_jobs` only; `field_ops.Job` has zero rows platform-wide per MODULE-L5-36), so no
   dual-pipeline union was modeled. Real status literals from `src/lib/transitions.ts` used throughout.
4. `src/lib/ux05/permissions.ts` — fail-closed canonical role derivation + StaffPermission presentation, with
   explicit-deny-overrides-grant enforced and unit-tested.
5. Four shared components (`PipelineBadge`, `PermissionRestrictedState`, `NextActionBar`,
   `PartsRequestStatusCard`) extending the app's existing plain-theme/StyleSheet conventions.
6. One dev-only showcase screen (`PartsRequestShowcaseScreen`) demonstrating the ServiceJob-only,
   technician-never-approves parts-request rule against local fixture state (no live endpoint exists).
7. 12 real, passing, behavioral unit/type-level tests (`npx jest` run in WSL).
8. Real `tsc --noEmit` run — zero errors in UX-05 code, 15 pre-existing errors in untouched files disclosed.
9. A documentation subset covering execution environment, the two key real-evidence corrections
   (pipeline, role), StaffPermission presentation, offline operation matrix, readiness registry, backend
   contract blockers, and honest non-change/gap accounting.

## What's deferred
See `deferred-items.md` and `known-limitations.md` for the full accounting: navigation/IA, the Home/My
Work/Schedule/Work Queue/Job Detail screen rebuilds, inspection/checklist/quote workflows, most of the shared
component/showcase-screen inventory, Expo-web/Playwright runtime verification, and roughly 60 of the 72
requested doc files.

## Final status
**STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** — real, verified, committed partial progress; not a complete design
phase. See `approval-gate.md`.
