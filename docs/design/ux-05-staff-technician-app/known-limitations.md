# Known Limitations (this pass)

- **Navigation/IA was not yet extended.** `TabNavigator`/`AppNavigator` still reflect the pre-existing single
  undifferentiated tab set (Home/Jobs/Chat/Earnings/Profile). The role-aware nav (Technician 5-tab / Staff 5-tab
  with "More") described in the IA workstream is designed in `src/types/ux05.ts` (`role`, `StaffHomeView` vs
  `TechnicianHomeView`) but not wired into a live navigator in this pass.
- **Home/My Work/Schedule/Staff Work Queue screens were not rebuilt.** The typed view models, permission helpers,
  and shared components (`PipelineBadge`, `NextActionBar`, `PermissionRestrictedState`,
  `PartsRequestStatusCard`) exist and are tested/typechecked, but only one showcase screen
  (`PartsRequestShowcaseScreen`) was built consuming them.
- **Inspection / checklist / quote workflows** have no live backend endpoint (see
  `backend-contract-blockers.md`) and no showcase screen was built for them this pass — only their view-model
  types exist.
- **Expo web + Playwright verification was not attempted.** Verification in this pass was `tsc --noEmit` +
  `jest` only.
- **Most of the 72-file documentation set was not written.** This pass produced the highest-leverage subset
  (execution environment, real-evidence corrections, role/permission contracts, offline matrix, readiness
  registry, blockers, this file, and the closing reports). See `deferred-items.md` for the explicit list of
  what remains.
- **Pre-existing type errors** (see `typecheck-report.md`) in files this phase did not author were found but not
  fixed — fixing them was judged out of this pass's scope (they predate UX-05 and are unrelated to the mobile
  role/pipeline/parts work requested), but they are now visible for the first time because `typecheck` was not a
  configured script before this pass.
