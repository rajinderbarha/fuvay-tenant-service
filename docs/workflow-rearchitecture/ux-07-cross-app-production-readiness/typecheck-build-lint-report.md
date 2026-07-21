# Round 4 Pass 2 — Typecheck/Build/Lint Report

Ran in WSL Debian against a clean copy (`~/uxc7/customer-app`) synced from the
worktree and freshly `npm install`-ed (866 packages).

| Check | Command (from package.json) | Result |
|---|---|---|
| Typecheck | `npx tsc --noEmit` | **0 errors** (both before and after this pass's edits) |
| Tests | `npx jest` | 48/48 before -> **58/58 after** |
| Lint | `npm run lint` (`eslint src --ext .ts,.tsx`) | **Not run this session** — deferred, see below |
| Build/export | none defined beyond `expo start`/`run:android`/`run:ios` | No `expo export`/web build script exists in package.json; this repo's "build" step for customer-app is the Expo dev-client/native build, not a static export. Not run this session (would require Expo CLI + device/simulator or `expo export` which is not wired as an npm script here). |

## Honest gaps
- ESLint was not run this session due to time budget; no claim is made about lint
  cleanliness of the new/changed files beyond what `tsc` catches.
- No Playwright/web build was produced or run (see customer-test-report.md).

## Errors found and fixed during this pass (before reaching 0)
1. `ThemeContext.tsx`: `Appearance.getColorScheme()` returns `ColorSchemeName | null`,
   which isn't assignable to the `useState<ColorSchemeName>` initializer type — fixed
   with `?? "light"`.
2. `styles/theme.ts`: `darkColors: typeof lightColors` forced `statusBarStyle` to the
   literal type inferred from `lightColors` (`"dark"`), so assigning `"light"` in
   `darkColors` failed — fixed by widening both to `"dark" | "light"`.
3. `HomeScreen.tsx`: during the useTheme() rewrite, the `grid` StyleSheet key was
   accidentally dropped from `makeStyles`, causing `Property 'grid' does not exist`
   — restored.

All three were caught and fixed via the WSL `npx tsc --noEmit` loop before committing;
final state is 0 errors.
