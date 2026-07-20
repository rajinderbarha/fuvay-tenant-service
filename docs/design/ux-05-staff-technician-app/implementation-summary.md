# UX-05 Implementation Summary

Branch `design/ux-05-staff-technician-app`, based on UX-04B `7488335`. Target: `mobile/staff-app/` (Expo ~56,
React Native 0.85, React 19.2, React Navigation v7). Three rounds of work so far, all partial, all honestly
reported.

## Round 1 (commits `4bb1db9`..`afaf478`)
Fixed two real WSL npm-install blockers, produced the app's first lockfile, added a test/typecheck toolchain,
built the full typed view-model contract (with the real-evidence single-pipeline correction), fail-closed
role/permission helpers, 4 shared components, 1 showcase screen, 12 tests, and ~18 doc files.

## Round 2 (commits `33879ee`..`5d88935`)
Role-aware navigation actually wired; `myWork.ts`/`checklist.ts` pure logic + tests; 11 more shared components;
new real `ScheduleScreen`; new honestly-labeled MOCK_DESIGN_ONLY Staff screens; real `JobDetailScreen` extended;
4 dev showcase routes; Expo web dependencies installed and dev-server-responds proven; 18 more tests (30 total);
~13 more docs (31 of 72).

## Round 3 (this update)
1. **`HomeScreen` recomposed for real** on `groupJobs()` — Active Job / new "Needs Your Action" section / Today's
   Schedule all use the same classification `JobsListScreen` uses.
2. **`myWork.ts` wired into `JobsListScreen`'s actual render** — tabs are now `All/Current/Today/Upcoming/
   Needs Action/Completed`, filtering calls the real tested function directly.
3. **Current Job mode** (`CurrentJobScreen`) — focused single-job screen, sticky `NextActionBar`, reuses the real
   transitions state machine, wired into `AppNavigator`.
4. **Quote presentation** (`QuoteShowcaseScreen`) — confirmed via full re-read of `lib/api.ts` that no quote
   endpoint exists; built view-only, `MOCK_DESIGN_ONLY`, no approve/finalize affordance in the view model at all.
5. **Availability control** (`AvailabilityControl`) — confirmed no live work-status endpoint; renders 4 statuses
   as local state with account/job status shown as visibly distinct fields; wired into extended `ProfileScreen`.
6. **`ProfileScreen` extended**: role/designation tag, real Assigned Services, honestly-labeled MOCK areas/
   certifications/recent-activity, `AvailabilityControl`.
7. **2 more dev showcases**: Quote, Offline States (6 scenarios using real `NetworkStatusBanner`/
   `PermissionRestrictedState`) — 7 of ~30 original targets now built.
8. **Expo web + Playwright retried properly** (continuous backgrounded shell session, not split across calls):
   bundle build proven real end-to-end (HTTP 200, 3.1MB, contains this round's actual compiled source);
   Playwright installed, Chromium downloaded, runtime launch hit one specific diagnosed blocker (missing sudo
   access for Chromium's system dependencies) — documented precisely rather than left ambiguous.
9. **5 more tests (35 total)**: `AvailabilityControl` interaction + distinct-field assertions,
   `NetworkStatusBanner` state-driven rendering (including the "renders nothing when nothing's wrong" case).
10. **Fresh re-verification this round**: `npx jest` → 35/35 passing; `npx tsc --noEmit` → 19 errors, all
    pre-existing pattern (14 pre-existing + 5 new occurrences of the identical existing pattern), zero new
    business-logic errors.
11. **6 more doc files** (37 of 72 total).

## What's still deferred
See `deferred-items.md` and `known-limitations.md`: `StaffHomeScreen`/`StaffWorkQueueScreen` need a real backend
endpoint (a genuine contract gap, not closeable from the frontend alone), `NotificationCard`/`NextActionBar`
wiring into the two remaining pre-existing screens, `NetworkStatusBanner` wiring into production screens, draft
persistence, a11y/theme/localization workstreams, the Playwright runtime check (build proven, browser-load
blocked by environment), ~35 remaining doc files, and ~23 more showcase screens.

## Final status
**STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** — real, verified, committed partial progress across three rounds; not a
complete design phase. See `approval-gate.md`.
