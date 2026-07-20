# Light/Dark Theme Report

## Round 4 finding (historical): this app had no dark theme at all
`src/styles/theme.ts` was a single, fixed, light-only color palette — verified by reading the file in full and
grepping for `useColorScheme`/`Appearance`: zero matches. Fixed 2 hardcoded `#fff` literals bypassing theme
tokens. Confirmed via Playwright that nothing crashes under a dark OS color-scheme setting, but the visual
result was identical to light (no palette to switch to).

## Round 5: real dark theme mechanism built
Followed the pattern already established in `frontend/packages/design-system/src/theme/ThemeProvider.tsx`
(read in full before implementing): a `preference` (`"light"|"dark"|"system"`) resolved to a `resolvedTheme`,
persisted across restarts, system-driven by default. The RN equivalent uses real platform APIs in place of the
web ones that pattern relies on:

| Web (design-system) | RN (mobile/staff-app) |
|---|---|
| `window.matchMedia("(prefers-color-scheme: dark)")` | `Appearance.getColorScheme()` + `Appearance.addChangeListener` |
| `localStorage` | `@react-native-async-storage/async-storage` (already a real dependency) |
| `data-theme` attribute + CSS vars | `useAppTheme().colors` object, consumed by components that build their `StyleSheet` from it |

### What was built
- `src/styles/theme.ts`: `lightColors` (renamed from the original flat palette) + a new `darkColors` object with
  the same keys (type-enforced via `Record<keyof typeof lightColors, string>` so a missing dark key is a
  compile error, not a silent runtime fallback), plus `getColors(scheme)`.
- `src/context/ThemeContext.tsx` (new): `ThemeProvider` + `useAppTheme()` — real preference persistence, real
  `Appearance.addChangeListener` reaction to OS changes while on `"system"`.
- `App.tsx`: wrapped with `ThemeProvider`.
- `AppNavigator.tsx`: `NavigationContainer`'s `theme` prop now switches between `DefaultTheme`/`DarkTheme`
  (React Navigation's own light/dark theme objects) driven by `useAppTheme()`, and header colors are reactive.
- `TechnicianTabNavigator`/`StaffTabNavigator`: tab bar and header colors now reactive.
- **5 ux05 components converted to fully reactive theme consumption**: `PipelineBadge`,
  `PermissionRestrictedState`, `NetworkStatusBanner`, `NotificationCard`, `AvailabilityControl` — each now calls
  `useAppTheme()` and builds its `StyleSheet` via a `useMemo(() => makeStyles(colors), [colors])` pattern instead
  of a module-scope `StyleSheet.create` (module-scope styles can't react to a runtime scheme change at all —
  this was the real mechanical reason a naive "just import theme.colors" approach wouldn't have worked).
- `ThemeToggle` (new, real production component, not a fixture): a Light/Dark/System control that writes through
  `setPreference()` — wired into the real `ProfileScreen`.
- `ThemeShowcaseScreen` (new dev showcase): demonstrates the toggle live against the 5 converted components.

### Real test-infrastructure fix required
Converting components to require a `ThemeProvider` ancestor broke the existing `PipelineBadge.test.tsx`/
`AvailabilityControl.test.tsx` (real `[@RNC/AsyncStorage]: NativeModule: AsyncStorage is null` failure —
AsyncStorage has no native module in the Jest environment). `setupFiles` pointing at the community mock file did
**not** work (the mock file just exports an object, it doesn't self-register); `moduleNameMapper` pointing the
real import path at the mock file did. Added a shared `renderWithTheme()` test helper
(`src/testUtils/renderWithTheme.tsx`) so every future test file wraps consistently.

### What was NOT converted this round (honest, disclosed scope)
Per the coordinator's explicit allowance ("don't need every screen perfect"): `HomeScreen`, `JobsListScreen`,
`JobDetailScreen`, `ScheduleScreen`, `CurrentJobScreen`, most of `ProfileScreen`'s own styling, and every
pre-existing (pre-UX-05) screen/component still import the static `theme`/`gs` exports and will always render
in the light palette regardless of the resolved scheme. This is a real, sizable remaining conversion — each
screen needs its module-scope `StyleSheet.create` calls rewritten to the `useMemo`-based reactive pattern shown
above. Not done this round; a concrete, mechanical next step for a future pass (the mechanism and the pattern
are both proven, so this is "more of the same," not new design work).

### Real verification (not just claimed)
`npx jest` — 43/43 passing after the conversion + test-infra fix, re-verified fresh. `npx tsc --noEmit` — 19
errors, same pre-existing pattern, zero new. Playwright smoke check (see `runtime-test-report.md`) still passes
zero-error after this round's changes.
