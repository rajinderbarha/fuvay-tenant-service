# Round 4, Pass 2 — Approval Gate

**Final status: UX07_INTEGRATION_PARTIAL**

## Gate checklist

| Item | Status |
|---|---|
| Real ThemeContext (System/Light/Dark, persisted, no flash-of-wrong-theme) | ✅ DONE |
| Real dark palette with genuine surface hierarchy (not pure black) | ✅ DONE |
| Shared components (Card/Button/JobStatusBadge/BookingCard/StarRating/Skeleton) dark-mode migrated | ✅ DONE |
| App root / navigation (headers, tab bar, StatusBar, NavigationContainer theme) dark-mode migrated | ✅ DONE |
| Login, Home, SmartBot (DeepSeekChatScreen) fully dark-mode migrated | ✅ DONE |
| Settings has a real System/Light/Dark selector | ✅ DONE |
| Remaining 14 screens dark-mode migrated | ❌ NOT DONE (Pass 3) |
| Responsive width matrix (320/360/390/430/768/1024) measured | ❌ NOT DONE |
| 320px certification document with real evidence | ❌ NOT DONE |
| Language content stress test (long Hindi/Punjabi, wrapping verified) | ❌ NOT DONE |
| Accessibility semantic audit (CSV, all screens) | ❌ NOT DONE (partial, ad hoc, touched files only) |
| Keyboard/focus audit | ❌ NOT DONE |
| Touch-target audit (CSV) | ❌ NOT DONE (partial — 44px minimums applied to touched files only) |
| Contrast audit (CSV) | ❌ NOT DONE |
| Text-scaling report | ❌ NOT DONE |
| Reduced-motion report | ❌ NOT DONE (partial — Skeleton only) |
| Loading/empty/error-state audit (CSV) | ❌ NOT DONE |
| Playwright/Expo-web visual run + evidence | ❌ NOT DONE |
| Typecheck: 0 errors | ✅ VERIFIED (WSL clean install) |
| Tests: all passing, no regression | ✅ VERIFIED — 58/58 (48 baseline + 10 new) |
| Source-change boundary respected (customer-app only) | ✅ VERIFIED (`git diff --stat` against backend/other-apps returns empty) |
| Incremental commits | ✅ 4 commits this pass |

## Recommendation for whoever picks up Pass 3
The pattern to repeat per remaining screen is exactly what was done for
LoginScreen/HomeScreen/DeepSeekChatScreen: replace `import { theme } from
"../styles/theme"` with `import { useTheme } from "../context/ThemeContext"`,
call `const { theme } = useTheme()` (and `mode` if a screen needs mode-specific
branching like HomeScreen's category grid), and convert the trailing
`StyleSheet.create({...})` into `function makeStyles(theme: Theme) { return
StyleSheet.create({...}) }` called inside the component. This compiles cleanly
against the same `Theme` type exported from `styles/theme.ts` and needs no
further foundation work — the foundation is done.

## Real commit hashes this pass
See `round-4-pass-2-status-rationale.md` and the final report for the exact
commit hash sequence (theme foundation → Login/Home/SmartBot migration → new
tests).
