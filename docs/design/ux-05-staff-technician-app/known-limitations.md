# Known Limitations (through Round 2)

- **Home screens are not yet recomposed.** `HomeScreen` (technician) is unchanged from before UX-05.
  `StaffHomeScreen` (new) is an honest MOCK_DESIGN_ONLY placeholder — no live staff work-queue-summary endpoint
  exists to populate the real priorities workstream 4 describes (action queue, unassigned jobs, SLA risks, etc.).
- **My Work grouping logic exists and is tested but is not wired into the UI yet.** `src/lib/ux05/myWork.ts`
  (`classifyJob`/`groupJobs`/`filterJobs`) is real and has 7 passing tests; `JobsListScreen` still uses its
  original flat status-tab filter rather than these groupings. `WorkItemCard` (built) is the intended row
  component once this wiring happens.
- **Staff Work Queue / More / Parts Approval are all correctly restricted, but that also means they show almost
  nothing today.** This is intentional (fail-closed `deriveRole()` defaults every real account to `technician`,
  and no live StaffPermission endpoint exists), not a half-built feature — see `staff-parts-approval.md` and
  `staffpermission-presentation.md`.
- **Quote presentation and Availability control were not built at all this round** — typed in `types/ux05.ts`
  from Round 1, no component or screen exists yet.
- **NextActionBar and NotificationCard exist but are unused** — `JobDetailScreen` and `NotificationsScreen`
  retain their own pre-existing inline rendering rather than being refactored onto the new shared components,
  to keep the diff to those two real, live screens smaller and lower-risk this round.
- **Expo web verification is real but incomplete.** The Metro dev server was proven to start and respond HTTP
  200 in WSL; a full JS-bundle-serves + Playwright smoke check was not completed due to a background-process
  lifecycle limitation in this tool environment (see `execution-environment.md` for the exact detail) — not a
  claim that Expo web is broken, just that the check wasn't finished.
- **Draft persistence (offline-draft-safe) is not implemented anywhere** — `InspectionChecklistShowcaseScreen`
  and `JobNotesMediaShowcaseScreen` hold state in `useState` only; a real app restart loses all draft progress.
  This is disclosed, not silently implied as solved by the "draft_only" category in `offline-operation-matrix.csv`
  (that CSV documents the *intended* offline category, not a claim that persistence is built).
- **Pre-existing type errors** (see `typecheck-report.md`) remain unfixed — 14 predate this phase, 1 new
  occurrence in `ScheduleScreen.tsx` reuses an existing codebase pattern verbatim rather than introducing a new
  bug class. Fixing the shared `useApi`/`useAction` generic-inference root cause was judged out of scope (touches
  a hook every existing screen depends on, no dedicated regression coverage exists for it).
- **Most of the 72-file documentation set remains unwritten** (31 of 72 done through Round 2) — see
  `deferred-items.md` for the itemized list.
