# Known Limitations (through Round 4 — intended as the last round for now)

- **`StaffHomeScreen`/`StaffWorkQueueScreen` remain honest placeholders.** No live staff work-queue-summary
  endpoint exists (confirmed across all four rounds) — a genuine backend-contract gap, not a frontend omission.
- **`NextActionBar` is wired into `CurrentJobScreen` but not `JobDetailScreen`** (kept as its own inline action
  grid, unchanged, to avoid touching the one screen with the real, money-touching `complete` action more than
  necessary). `NotificationCard` is built but `NotificationsScreen` keeps its own pre-existing renderer.
- **This app has no dark theme at all** — a real, pre-existing (not UX-05-introduced) characteristic, confirmed
  by direct inspection (`theme.ts` is one fixed palette; zero `useColorScheme`/`Appearance` usage anywhere).
  UX-05's own components don't hardcode colors that would fight a future dark palette (2 real violations found
  and fixed this round), but building an actual second palette + OS-theme wiring is a real, separate,
  not-yet-started workstream for a future pass.
- **`useNetworkStatus` (new this round) is real on Expo web, not on native.** `navigator.onLine` +
  `online`/`offline` window events work in a real browser (verified via Playwright); React Native on iOS/Android
  has neither — the hook will always report "online" on a native build until a
  `@react-native-community/netinfo` (or `expo-network`) dependency is added, a real dependency decision not made
  this round.
- **Draft persistence remains unimplemented** everywhere it's mentioned (Inspection/Checklist, Notes/Media,
  Quote) — all `useState`-only, lost on unmount.
- **No focus-order audit, no text-scaling stress test, no live screen-reader session** were performed — the
  accessibility pass fixed concrete, verifiable gaps (touch targets, missing labels/roles, color-only status)
  but did not attempt these harder-to-verify-without-a-device checks. See `accessibility-report.md`.
- **Pre-existing type errors remain unfixed** (19 total — 14 pre-existing before UX-05, 5 new occurrences of the
  identical existing `useCallback`/`useAction`/screen-prop-typing pattern reused verbatim in new files across
  Rounds 2–3; Round 4 added zero new occurrences). Fixing the shared `hooks/useApi.ts` generic-inference root
  cause remains out of scope.
- **Most of the 72-file documentation set remains unwritten** (~41 of 72 done through Round 4).
- **~22 of the original ~30 dev-showcase-screen targets remain unbuilt** (8 built: Parts Request, Inspection &
  Checklist, Notes & Media, Staff Parts Approval, Quote, Offline States, System States, plus Current Job as a
  semi-production screen). Light/dark-theme-examples and large-text/accessibility dedicated showcases were not
  built as separate screens.
- **Lint** — `eslint` script exists, still not executed (no config exists, confirmed `NOT_CONFIGURED` since Round 1).
- **Deep-linking into authenticated routes was never verified in-browser** — no `linking` config exists in
  `NavigationContainer`; only the unauthenticated Login screen was confirmed to render error-free via Playwright.
- **Staff Work Queue / More / Parts Approval remain correctly restricted, showing almost nothing** — intentional
  (fail-closed `deriveRole()` + no live StaffPermission endpoint), not a half-built feature.
