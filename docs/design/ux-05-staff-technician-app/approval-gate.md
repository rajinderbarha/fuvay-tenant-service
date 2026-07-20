# Approval Gate

Status: **STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** (Round 4 — intended as the last round for now)

This phase does NOT certify the full UX-05 brief (~38 workstreams, ~72 docs, full runtime/offline/a11y test
matrix, 30 showcase screens) as complete. Through four rounds it certifies, with real evidence:

- A working WSL dependency-install pipeline for `mobile/staff-app`, including Expo-web dependencies and Playwright.
- A typed domain-model foundation reflecting real backend evidence (single live pipeline, real status literals).
- A fail-closed role/permission presentation layer, unit-tested.
- Role-aware navigation actually mounted and reachable.
- Both flagged "logic built but not wired" gaps from Round 2 closed (`HomeScreen`/`JobsListScreen` share one
  real, tested `groupJobs()` classification).
- Current Job mode, Quote presentation, Availability control, extended Profile — all built, all honestly labeled
  `MOCK_DESIGN_ONLY` where no backend support exists (verified by re-reading `lib/api.ts`, not assumed).
- **The full verification stack now works end-to-end, including the browser layer**: install → typecheck →
  unit/component tests → Expo web bundle build → headless-browser runtime load, all proven real in WSL.
- **A genuine bug was found and fixed via real browser verification**: a `react`/`react-dom` version mismatch
  that caused an actual page error, invisible to every other verification layer in this project. This is direct
  evidence the runtime-verification investment was worth making, not just a checklist item.
- **A real accessibility pass**: 4 touch-target fixes, 8 components given proper `accessibilityRole`/
  `accessibilityLabel`, one color-only-status gap closed.
- **A real theme pass**: 2 hardcoded color literals found and fixed; an honest, verified finding that this app
  has no dark theme at all (a real pre-existing gap, not fabricated as solved).
- `NetworkStatusBanner` wired into the real production app shell (not just the dev showcase), backed by a new
  `useNetworkStatus` hook that is real on Expo web and honestly documented as native-incomplete.
- 8 of ~30 dev showcase screens built. ~41 of 72 doc files written.
- 35/35 tests passing, 19 typecheck errors (all pre-existing pattern, zero new), zero changes outside
  `mobile/staff-app/` and this doc directory — all re-verified fresh this round.

See `deferred-items.md` and `known-limitations.md` for the full accounting of what remains before a
`DESIGN_COMPLETE` gate could be claimed: `StaffHomeScreen`/`StaffWorkQueueScreen` need a real backend endpoint
(a genuine contract gap, not closeable from the frontend alone), a real dark theme (a real, separate, sizable
workstream), native network detection (needs a NetInfo dependency decision), draft persistence, the remaining
~22 showcase screens, ~31 more doc files, and a systematic a11y/localization audit beyond this round's targeted
fixes.

## Recommendation for a future UX-05B pass
Mirroring how UX-04 → UX-04A → UX-04B worked: this phase's foundation (typed view models, fail-closed role/
permission layer, working WSL+Playwright verification pipeline, real component library) is solid and proven.
A follow-on UX-05B pass should prioritize, in order: (1) flagging the two real backend-contract gaps
(staff work-queue-summary endpoint, StaffPermission-fetch endpoint) to unblock `StaffHomeScreen`/
`StaffWorkQueueScreen` for real, (2) a genuine dark-theme implementation (palette + `useColorScheme` wiring),
(3) the remaining showcase/doc breadth, (4) a native-device or emulator verification pass if one becomes
available in this environment.
