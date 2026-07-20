# Approval Gate

Status: **STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** (Round 5)

This phase does NOT certify the full UX-05 brief (~38 workstreams, ~72 docs, full runtime/offline/a11y test
matrix, 30 showcase screens) as complete. Through five rounds it certifies, with real evidence:

- A working WSL dependency-install pipeline for `mobile/staff-app`, including Expo-web dependencies, Playwright,
  and NetInfo.
- A typed domain-model foundation reflecting real backend evidence (single live pipeline, real status literals).
- A fail-closed role/permission presentation layer, unit-tested.
- Role-aware navigation actually mounted and reachable.
- Both flagged "logic built but not wired" gaps from Round 2 closed (`HomeScreen`/`JobsListScreen` share one
  real, tested `groupJobs()` classification).
- Current Job mode, Quote presentation, Availability control, extended Profile — all built, all honestly labeled
  `MOCK_DESIGN_ONLY` where no backend support exists (verified by re-reading `lib/api.ts`, not assumed).
- **The full verification stack works end-to-end, including the browser layer**, re-confirmed after Round 5's
  changes: install → typecheck → unit/component tests → Expo web bundle build → headless-browser runtime load,
  zero page/console errors.
- **A genuine bug was found and fixed via real browser verification** (Round 4): a `react`/`react-dom` version
  mismatch invisible to every other verification layer.
- **A real accessibility pass** (Round 4) and **a real theme pass** (Rounds 4–5): Round 4 found the app had no
  dark theme at all; **Round 5 built the actual mechanism** — a type-safe dark palette, a `ThemeContext` mirroring
  the web design-system's real `ThemeProvider` pattern (`Appearance` API + AsyncStorage instead of `matchMedia` +
  `localStorage`), wired into the app shell, both tab navigators, and 5 components, with a real production
  `ThemeToggle` control.
- **`NetworkStatusBanner` wired into production**, now backed by real `@react-native-community/netinfo`
  (investigated and added this round — permissive peer deps, real native+web coverage, not deferred by default).
- **Real draft persistence** (AsyncStorage-backed `usePersistedDraft`, tested with a genuine restart simulation)
  wired into one showcase.
- **A real localization spot-check** with genuine long Hindi/Punjabi sentences across 4 components — no
  accidental truncation found, one intentional truncation correctly distinguished.
- 10 of ~30 dev showcase screens built. ~46 of 72 doc files written.
- 43/43 tests passing, 19 typecheck errors (all pre-existing pattern, zero new), zero changes outside
  `mobile/staff-app/` and this doc directory — all re-verified fresh this round, on the correct branch.

See `deferred-items.md` and `known-limitations.md` for the full accounting of what remains before a
`DESIGN_COMPLETE` gate could be claimed: `StaffHomeScreen`/`StaffWorkQueueScreen` need a real backend endpoint
(a genuine contract gap, not closeable from the frontend alone), broader dark-theme coverage across the
remaining screens (mechanical, proven pattern, real remaining work), draft persistence in the remaining two
showcases, the remaining ~20 showcase screens, ~26 more doc files, and a systematic a11y/localization audit
beyond this round's targeted checks.

## Recommendation for a future UX-05B pass
Mirroring how UX-04 → UX-04A → UX-04B worked: this phase's foundation (typed view models, fail-closed role/
permission layer, working WSL+Playwright verification pipeline, real dark-theme mechanism, real component
library) is solid and proven across five rounds. A follow-on UX-05B pass should prioritize, in order:
(1) flagging the two real backend-contract gaps (staff work-queue-summary endpoint, StaffPermission-fetch
endpoint) to unblock `StaffHomeScreen`/`StaffWorkQueueScreen` for real, (2) converting the remaining screens to
the proven reactive-theme pattern, (3) wiring draft persistence into the remaining showcases, (4) the remaining
showcase/doc breadth, (5) a native-device or emulator verification pass if one becomes available in this
environment.
