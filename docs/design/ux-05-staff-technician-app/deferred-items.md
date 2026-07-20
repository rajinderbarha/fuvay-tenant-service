# Deferred Items — explicit accounting against the 38-workstream brief

## Done (real, committed, verified) — Round 1 + Round 2

**Round 1:**
1. Discovery (Step 0) — package.json, src/ tree, screens, AuthContext, api.ts, transitions.ts read in full.
2. WSL verification setup — npm install succeeded (850 packages), lockfile generated and committed, two real
   install-blocking bugs found and fixed (ERESOLVE peer conflict, dead `@types/react-native` target).
3. Typed view-model contract (`src/types/ux05.ts`) covering all 20 named view models from workstream 25.
4. Canonical role derivation + StaffPermission presentation helpers, fail-closed.
5. Four shared components (PipelineBadge, PermissionRestrictedState, NextActionBar, PartsRequestStatusCard).
6. One dev-only showcase screen (Parts Request creation+tracking).
7. 12 unit tests.
8. Typecheck run in WSL — zero errors in UX-05 code.
9. Non-change verification.

**Round 2 (this update):**
10. **Role-aware navigation, wired for real**: `TechnicianTabNavigator` (Home/My Work/Schedule/Notifications/
    Profile), `StaffTabNavigator` (Home/Work/Schedule/Notifications/More), `RoleAwareTabNavigator` (fail-closed
    selector using `deriveRole`), and `AppNavigator` updated to mount it in place of the old single `TabNavigator`.
11. **Pure grouping/validation logic + tests**: `myWork.ts` (`classifyJob`/`groupJobs`/`filterJobs`, 7 tests) and
    `checklist.ts` (`computeProgress`/`isItemComplete`/`missingRequiredItems`/`canComplete`, 6 tests) — both real,
    unit-tested, not yet fully wired into every consuming screen (see `known-limitations.md`).
12. **6 more shared components**: WorkItemCard, ScheduleCard, CustomerContactCard, AddressCard, NotificationCard,
    NetworkStatusBanner — plus ChecklistSection/ChecklistProgress, InspectionForm, JobNoteComposer,
    MediaCaptureGrid (5 more) = 11 new this round, 15 total.
13. **New real screen**: `ScheduleScreen`, wired to the real `jobsApi.myJobs()`, Today/Upcoming grouping.
14. **New MOCK_DESIGN_ONLY screens** (honestly labeled, no live backend): `StaffHomeScreen`,
    `StaffWorkQueueScreen`, `StaffMoreScreen` (permission-gated entry list), `InspectionChecklistShowcaseScreen`
    (real progress/validation logic wired to real UI), `JobNotesMediaShowcaseScreen`,
    `StaffPartsApprovalShowcaseScreen` (fail-closed restricted for every current real user).
15. **Job Detail extended for real**: `CustomerContactCard`, `AddressCard`, `PipelineBadge` wired into the live
    `JobDetailScreen` using data already fetched (no new API call).
16. **4 dev-only showcase routes registered** in `AppNavigator` (not linked from production nav/tabs).
17. **Expo web dependency install attempted and partially verified**: `react-dom`/`react-native-web` installed,
    Metro dev server confirmed to start and respond HTTP 200; full bundle/Playwright smoke test not completed
    (see `execution-environment.md` for the exact boundary hit).
18. **18 more unit/component tests** (30 total): My Work classification, checklist progress/validation, and the
    first real RNTL component-render tests in this app (`PipelineBadge`, `PermissionRestrictedState`).
19. Fresh re-verification at the end of Round 2: `npx jest` (30/30) and `npx tsc --noEmit` (15 pre-existing-pattern
    errors, zero new business-logic errors) both re-run from a clean sync, not restated from memory.
20. ~13 more documentation files this round (see below) — 31 of 72 total.

## Not done (explicit gaps, not silently dropped)
- Home screens (Technician `HomeScreen` / `StaffHomeScreen`) are not yet recomposed to the priorities described
  in workstream 4 (current/next job, checklist progress, pending parts counts for technician;
  action-queue/SLA-risk for staff) — `HomeScreen` is unchanged from pre-UX-05, `StaffHomeScreen` is a placeholder.
- `JobsListScreen` (My Work) is not wired to `myWork.ts`'s grouping logic yet — the logic is real and tested, the
  screen still uses its old flat status-tab filter.
- `NotificationsScreen` is not wired to `NotificationCard` (still uses its own inline row renderer).
- `NextActionBar` is built but not wired into `JobDetailScreen` (which retains its own inline action-button grid).
- Current Job mode (a distinct focused single-job screen, workstream 9) was not built — `JobDetailScreen` remains
  the only job-focused screen.
- Quote presentation (workstream 17) — no component or screen built (no backend endpoint at all).
- Availability control (workstream 21) — `AvailabilityView` is typed, no component/screen built.
- Profile screen not extended with role/designation display (workstream 22).
- Offline UI states beyond the documented matrix + `NetworkStatusBanner` component (built but not wired into
  any screen) — workstream 23 not substantially advanced this round.
- Light/dark theme audit, accessibility audit, localization testing (workstreams 29–31) — not attempted.
- Lint run — `eslint` script exists, still not executed (no config exists, confirmed `NOT_CONFIGURED` in Round 1).
- Most non-regression/build reports for other apps (workstream 36) beyond the backend/frontend allow-list check.
- ~41 of the 72 doc files remain unwritten.

## Why the cut was made here, not elsewhere (Round 2)
Given the coordinator's priority order, the highest-value additions this round were: (1) make the role-aware
navigation *actually load* (not just typed), since every other screen's reachability depends on it; (2) prove
the two most complex pieces of new business logic (My Work grouping, checklist validation) with real tests
rather than only UI; (3) extend the *real* Job Detail screen (not just showcases) since it's the one screen a
real technician actually uses daily; (4) attempt Expo web honestly rather than skip it, even though it wasn't
completed end-to-end. This remains a partial delivery — reported as `STAFF_TECHNICIAN_APP_DESIGN_PARTIAL`.
