# Known Limitations (through Round 8, + UX-05B finalization)

- **UX-05B scope closure — items 3 and 4 (bulk showcase-screen breadth, remaining ~27 doc files) were not
  substantially advanced this phase.** UX-05B's bounded scope prioritized correctness (product-review fixes),
  the one named high-risk deferred item (`JobDetailScreen` theme conversion + its money-modal regression
  coverage), a formal typecheck classification, closing the two production-reachable Staff-screen jargon leaks,
  an accessibility reconciliation, a definitive screen inventory, and a final fresh-install/browser verification
  pass — all done and evidenced in this phase's commits. Given the time actually available, pushing the
  showcase-screen count further (item 3) and writing the remaining ~27 of 72 doc files (item 4) were not
  reached. This is an honest, disclosed gap, not silently dropped: the showcase count remains ~12 of ~30, and
  documentation remains ~47 of 72 files (45 through Round 8 + `typecheck-error-classification.md` +
  `accessibility-reconciliation.md` + `screen-route-inventory.md` this phase).
- **UX-05B FIX 3 investigation: the "Today" filter-tab pointer-event-interception report was a confirmed false
  alarm, not a real layout bug.** A manual review claimed clicking the "Today" tab on `JobsListScreen` ("My
  Work") failed in Playwright with "element intercepts pointer events" at a 390px viewport. Investigated live
  with a real headless-Chromium Playwright session (logged in as `tech2@demo-ac-services.local` against the
  real backend, real job data). Root cause of the *original* failure: React Navigation's tab navigator keeps
  the previously-active tab screen (`HomeScreen`) mounted in the DOM (`position:absolute`) underneath the
  active one, and `HomeScreen` has its own unrelated "Today" stat-card label ("Today · 0 jobs assigned"). A
  bare `page.getByText("Today", { exact: true })` matches that hidden label *first* in DOM order, before the
  real, visible `JobsListScreen` tab — so a naive Playwright test clicks the wrong (buried) element and gets an
  interception error, while a real user's tap (or `page.getByText(...).nth(1)`, confirmed to correctly resolve
  to the visible tab) lands on the correct, fully-functional tab every time. Re-tested against the exact
  pre-UX-05B `JobsListScreen.tsx` (`git show a48bb44:...`, no changes): clicking the correctly-disambiguated
  "Today" tab succeeds with zero interception and correctly filters the job list (a job dated `2026-08-01`
  disappears from the "Today" view as expected). No code change was made to `JobsListScreen.tsx` — the tab row
  has no real overlap, z-index, or overflow bug; the "flex:1 six tabs on 390px" layout renders correctly. This
  is a documented test-methodology finding, not a shipped fix, per the "don't blindly fix nothing that's
  actually broken" instruction for this task.
- **Working-tree dependency drift caused a real, independently-caught test-failure incident (Round 7→8).** A
  genuinely fresh `npm install` against the real `G:\serviceos` working tree at one point reproduced 13/43 test
  failures (`react-test-renderer` duplicate-instance bug) because `package.json`/`package-lock.json` had
  reverted, uncommitted, to older pre-Round-4 versions outside this agent's commits. Root-caused, fixed (restored
  from HEAD + added a defensive `overrides` pin), and re-verified with two independent from-scratch installs —
  see `prerequisite-bug-fix-report.md` entry #3 for the full account. Going forward, every round's final report
  is based on genuinely fresh-install test numbers, not a possibly-stale local `node_modules`.
- **`StaffHomeScreen`/`StaffWorkQueueScreen` remain honest placeholders.** No live staff work-queue-summary
  endpoint exists (confirmed across all five rounds) — a genuine backend-contract gap, not a frontend omission.
- **`NextActionBar` is wired into `CurrentJobScreen` but not `JobDetailScreen`** (kept as its own inline action
  grid, unchanged, to avoid touching the one screen with the real, money-touching `complete` action more than
  necessary). `NotificationCard` is theme-reactive but `NotificationsScreen` keeps its own pre-existing renderer.
- **The dark theme mechanism is real but its coverage is partial.** 5 ux05 components + both tab navigators +
  `AppNavigator`'s chrome + the new `ThemeToggle`/`ThemeShowcaseScreen` are fully reactive. Every pre-existing
  (pre-UX-05) screen/component and most other UX-05 screens (`HomeScreen`, `JobsListScreen`, `JobDetailScreen`,
  `ScheduleScreen`, `CurrentJobScreen`, most of `ProfileScreen`) still import the static light-only `theme`/`gs`
  exports and will always render light regardless of the resolved scheme. Converting them is mechanical (the
  pattern is proven) but real, remaining work — not attempted broadly this round per the coordinator's explicit
  "don't need every screen perfect" allowance. See `light-dark-theme-report.md`.
- **`useNetworkStatus` now uses real NetInfo** (native + web) as of this round — the "native always reports
  online" gap from Round 4 is closed. `networkState:"slow"` is still not derived (would need platform-specific
  connection-quality parsing not verified this round).
- **Draft persistence is real but only wired into one showcase.** `usePersistedDraft` (AsyncStorage-backed) is
  built and tested (including a genuine unmount/remount restart simulation), wired into
  `InspectionChecklistShowcaseScreen` only. `JobNotesMediaShowcaseScreen` and `QuoteShowcaseScreen` still use
  `useState`-only drafts, lost on unmount — a real, disclosed remaining gap.
- **Localization is `NOT_APPLICABLE` per a Round 6 product correction** — Super Admin/Tenant/Staff/Technician
  apps (including this one) are single-language (English) by design; multilingual behavior belongs only to the
  DeepSeek customer-chat assistant, a different app. No i18n infrastructure should be built here. The Round 5
  Hindi/Punjabi spot-check (4 components, 4 tests) was kept as harmless defensive-layout verification but is
  not an open workstream — see `localization-readiness-report.md`.
- **No focus-order audit, no text-scaling stress test, no live screen-reader session** were performed — the
  accessibility pass (Round 4) fixed concrete, verifiable gaps but did not attempt these harder-to-verify-
  without-a-device checks.
- **Pre-existing type errors remain unfixed** (19 total — 14 pre-existing before UX-05, 5 new occurrences of the
  identical existing `useCallback`/`useAction`/screen-prop-typing pattern reused verbatim in new files across
  Rounds 2–3; Rounds 4–5 added zero new occurrences). Fixing the shared `hooks/useApi.ts` generic-inference root
  cause remains out of scope.
- **Most of the 72-file documentation set remains unwritten** (~46 of 72 done through Round 5).
- **~20 of the original ~30 dev-showcase-screen targets remain unbuilt** (10 built through Round 5). Large-text/
  accessibility dedicated showcase was not built as a separate screen.
- **Lint** — `eslint` script exists, still not executed (no config exists, confirmed `NOT_CONFIGURED` since Round 1).
- **Deep-linking into authenticated routes was never verified in-browser** — no `linking` config exists in
  `NavigationContainer`; only the unauthenticated Login screen was confirmed to render error-free via Playwright,
  re-confirmed after every round's changes including Round 5's.
- **Staff Work Queue / More / Parts Approval remain correctly restricted, showing almost nothing** — intentional
  (fail-closed `deriveRole()` + no live StaffPermission endpoint), not a half-built feature.
