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

**Round 3 (this update):**
21. **HomeScreen recomposed for real** on top of `groupJobs()` — Active Job / Needs Your Action (new section,
    real `assigned`/`quote_required` group) / Today's Schedule all now use the same classification `JobsListScreen`
    uses, closing the "Home and My Work could disagree" gap. Pending-parts/checklist-progress shown as an
    honest `MOCK_DESIGN_ONLY` placeholder (no aggregation endpoint exists).
22. **`myWork.ts` wired into `JobsListScreen`'s actual render** — tabs changed from the old ad-hoc
    `All/Assigned/Active/Completed/Cancelled` to `All/Current/Today/Upcoming/Needs Action/Completed`, filtering
    now calls `groupJobs()` directly instead of a separate inline filter.
23. **Current Job mode** (`CurrentJobScreen`, new) — focused single-job view, sticky `NextActionBar`, real
    customer-contact/address, reuses the real transitions state machine (redirects to `JobDetailScreen`'s modal
    for the two actions needing extra input rather than reimplementing them).
24. **Quote presentation** (`QuoteShowcaseScreen`, new) — confirmed via full re-read of `lib/api.ts` that no
    quote endpoint exists anywhere; built as a view-only `MOCK_DESIGN_ONLY` fixture with no approve/finalize
    affordance at all (enforced by omission from the view model, not a runtime check).
25. **Availability control** (`AvailabilityControl`, new component) — confirmed no live work-status endpoint
    exists; renders 4 selectable statuses as local state, with account-status and job-status shown as visibly
    distinct fields. Wired into the extended `ProfileScreen`.
26. **Profile screen extended** — role/designation tag, real Assigned Services (from `StaffUser.specialisations`,
    already-fetched data), honestly-labeled `MOCK_DESIGN_ONLY` areas/certifications/recent-activity sections,
    `AvailabilityControl`.
27. **2 more dev showcases**: `QuoteShowcaseScreen`, `OfflineStatesShowcaseScreen` (6 offline/sync scenarios using
    the real `NetworkStatusBanner` + `PermissionRestrictedState` components, not one-off mockups) — 7 of ~30
    original showcase targets now built (up from 4).
28. **Expo web bundle build proven real, end-to-end**: HTTP 200 + 3.1MB bundle verified to contain this round's
    actual compiled source. Playwright headless-runtime check attempted with a specific, diagnosed, reproducible
    blocker found (missing sudo access to install Chromium's system dependencies) rather than an ambiguous
    failure — see `execution-environment.md` and `staff-technician-build-report.md`.
29. **5 more tests (35 total)**: `AvailabilityControl` chip-press behavior + distinct-field rendering,
    `NetworkStatusBanner` online-idle-silent / offline-message / sync-pending-count.
30. Fresh re-verification at the end of Round 3: `npx jest` (35/35) and `npx tsc --noEmit` (19 errors, all
    pre-existing pattern, zero new business-logic errors) both re-run from a clean sync.
31. 6 more documentation files this round (see below).

## Not done (explicit gaps, not silently dropped)
- `NotificationsScreen` is not wired to `NotificationCard` (still uses its own inline row renderer).
- `NextActionBar` is not wired into `JobDetailScreen` (which retains its own inline action-button grid) — it IS
  wired into the new `CurrentJobScreen`.
- `StaffHomeScreen`/`StaffWorkQueueScreen` remain honest placeholders (no live staff work-queue endpoint exists
  to populate real content — this cannot be closed without a backend contract, not a frontend gap).
- Offline UI states now have a showcase (`OfflineStatesShowcaseScreen`) but `NetworkStatusBanner` still isn't
  wired into any *production* screen (only shown in the dev showcase).
- Light/dark theme audit, accessibility audit, localization testing (workstreams 29–31) — not attempted.
- Lint run — `eslint` script exists, still not executed (no config exists, confirmed `NOT_CONFIGURED` in Round 1).
- Most non-regression/build reports for other apps (workstream 36) beyond the backend/frontend allow-list check.
- Playwright *runtime* smoke test — build pipeline proven, actual browser-load check blocked by a specific
  diagnosed environment issue (see above), not completed.
- ~35 of the 72 doc files remain unwritten (37 of 72 done as of this round).
- Still not built at all: ~23 of the original ~30 showcase-screen targets, most a11y/theme/localization work,
  session-expired/tenant-suspended dedicated screens (only referenced conceptually in the offline showcase).

**Round 4 (this update, likely final for now):**
32. **Chromium/Playwright runtime blocker resolved** — switched to the WSL Debian root user (needs no sudo),
    installed Chromium's system deps successfully, and ran a real headless-browser smoke check. Found and fixed
    a genuine, previously-undetected bug (`react`/`react-dom` version mismatch causing a real page error) —
    exactly the kind of defect no other verification layer (typecheck, unit tests) in this project could catch.
    Re-confirmed zero errors after the fix, in both light and dark browser color schemes, and again after this
    round's further changes. See `runtime-test-report.md`.
33. **Real accessibility pass** (not a plan): fixed 4 sub-44pt touch targets (`Button` "sm", `AddressCard`,
    `CustomerContactCard`, `JobNoteComposer` action buttons), added `accessibilityRole`/`accessibilityLabel` to
    8 components, improved `NotificationCard`'s unread-status to be conveyed beyond color alone, hid
    `PermissionRestrictedState`'s decorative icon from screen readers. See `accessibility-report.md`.
34. **Real theme pass**: found and fixed 2 hardcoded `#fff` color literals (should have used
    `theme.colors.textInverse`) in `JobNoteComposer`/`NextActionBar`. Confirmed via grep that every other
    UX-05-authored file already uses theme tokens exclusively. **Honest finding**: this app has no dark theme
    at all (verified — `theme.ts` is a single fixed palette, zero `useColorScheme`/`Appearance` usage anywhere)
    — this predates UX-05 and is a real, separate, sizable future workstream, not something "spot-checked" into
    existence. See `light-dark-theme-report.md`.
35. **`NetworkStatusBanner` wired into production** — new `useNetworkStatus` hook (real on Expo web via
    `navigator.onLine`/online-offline events, honestly documented as always-online on native until a NetInfo
    dependency is added) mounted once in `AppNavigator` above every screen, not just shown in the dev showcase.
36. **1 more dev showcase**: `SystemStatesShowcaseScreen` (Session Expired, Tenant Suspended, Read-only,
    Restricted) — 8 of ~30 original showcase targets now built.
37. Fresh re-verification at the end of Round 4: `npx jest` (35/35) and `npx tsc --noEmit` (19 errors, unchanged
    pre-existing pattern, zero new errors from this round's changes) both re-run from a clean sync.
38. 4 more documentation files this round (`accessibility-report.md`, `light-dark-theme-report.md`,
    `runtime-test-report.md`, plus updates to `execution-environment.md`/`staff-technician-build-report.md`).

## Why the cut was made here, not elsewhere (Round 4)
Followed the coordinator's priority order exactly: finish the in-progress theme-fix work first (don't lose
uncommitted changes), unblock Chromium via the root user (the single highest-value remaining verification gap,
and it paid off immediately by catching a real bug), do a real accessibility/theme pass rather than more
documentation, wire the one component that had been "built but not connected to anything real"
(`NetworkStatusBanner`), and add one more showcase for breadth. This remains a partial delivery, and per the
coordinator's framing this is intended as the last round for now — see `known-limitations.md` and
`approval-gate.md` for the honest final accounting for a potential future UX-05B pass.

## Why the cut was made here, not elsewhere (Round 3, historical)
Followed the coordinator's explicit priority order: close the two flagged "logic built but not wired" gaps first
(Home, My Work) since those are the screens a real technician actually opens most; build Current Job mode next
since it was the most-requested missing screen; cover Quote/Availability/Profile since they were fully
unaddressed; retry Expo web/Playwright properly (continuous backgrounded session) since Round 2 left that
ambiguous, and this round got a real, specific, diagnosed answer instead. This remains a partial delivery —
reported as `STAFF_TECHNICIAN_APP_DESIGN_PARTIAL`.
