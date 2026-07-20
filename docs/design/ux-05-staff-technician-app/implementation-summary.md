# UX-05 Implementation Summary

Branch `design/ux-05-staff-technician-app`, based on UX-04B `7488335`. Target: `mobile/staff-app/` (Expo ~56,
React Native 0.85, React 19.2, React Navigation v7). Two rounds of work so far, both partial, both honestly
reported.

## Round 1 (commits `4bb1db9`..`afaf478`)
Fixed two real WSL npm-install blockers, produced the app's first lockfile, added a test/typecheck toolchain,
built the full typed view-model contract (with the real-evidence single-pipeline correction), fail-closed
role/permission helpers, 4 shared components, 1 showcase screen, 12 tests, and ~18 doc files.

## Round 2 (commits `33879ee`..`5d88935`, plus this doc-update commit) — this update
1. **Role-aware navigation, actually wired**: `TechnicianTabNavigator` (Home/My Work/Schedule/Notifications/
   Profile), `StaffTabNavigator` (Home/Work/Schedule/Notifications/More), `RoleAwareTabNavigator` (fail-closed),
   mounted into `AppNavigator` in place of the old single `TabNavigator`.
2. **Pure logic + tests**: `myWork.ts` (job grouping/classification/filtering, 7 tests),
   `checklist.ts` (progress/validation, 6 tests) — real, behavioral, not smoke-only.
3. **11 more shared components** (15 total): WorkItemCard, ScheduleCard, CustomerContactCard, AddressCard,
   NotificationCard, NetworkStatusBanner, ChecklistSection/ChecklistProgress, InspectionForm, JobNoteComposer,
   MediaCaptureGrid.
4. **New real screen**: `ScheduleScreen` (real `jobsApi` data, Today/Upcoming).
5. **New honestly-labeled MOCK_DESIGN_ONLY screens**: `StaffHomeScreen`, `StaffWorkQueueScreen`, `StaffMoreScreen`,
   `InspectionChecklistShowcaseScreen`, `JobNotesMediaShowcaseScreen`, `StaffPartsApprovalShowcaseScreen`
   (fail-closed-restricted for every current real user — no live role/permission data exists to unlock it).
6. **Real `JobDetailScreen` extended**: `CustomerContactCard`/`AddressCard`/`PipelineBadge` wired in using data
   already fetched, no new API call, no phone number fabricated (none exists on the real safe view).
7. **4 dev-only showcase routes** registered in `AppNavigator`, unreachable from production nav.
8. **Expo web**: `react-dom`/`react-native-web` installed; Metro dev server proven to start and respond HTTP 200
   in WSL; full bundle/Playwright verification not completed (disclosed boundary, not a silent skip).
9. **18 more tests (30 total)**, including this app's first RNTL component-render tests.
10. **Fresh re-verification this round** (not restated from memory): `npx jest` → 30/30 passing; `npx tsc --noEmit`
    → 15 errors, all pre-existing-pattern, zero new business-logic errors.
11. **~13 more doc files** (31 of 72 total).

## What's still deferred
See `deferred-items.md` and `known-limitations.md`: Home-screen recomposition, wiring `myWork.ts` into
`JobsListScreen`'s actual render, Current Job mode, Quote presentation, Availability control, Profile extension,
completing Expo-web/Playwright verification, ~41 remaining doc files, and the rest of the 30-showcase-screen
target (4 of ~30 built).

## Final status
**STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** — real, verified, committed partial progress across two rounds; not a
complete design phase. See `approval-gate.md`.
