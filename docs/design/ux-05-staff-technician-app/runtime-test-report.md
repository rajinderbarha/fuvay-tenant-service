# Runtime Test Report (Round 4 — real headless-browser verification, unblocked; Round 5 re-verified)

## What changed from Round 3
Round 3 got the Expo web *build* pipeline proven (bundle serves, contains real compiled source) but the
Playwright *runtime* check (actually loading the app in a browser) was blocked: headless Chromium crashed with
`SIGSEGV` under the `admin` WSL user, and `sudo -n true` confirmed passwordless sudo wasn't available to install
the missing system libraries.

Per the coordinator's correct diagnosis: this project's WSL Debian instance has a **root** user (used for all
prior npm/apt installs across this whole project) that needs no `sudo` at all. Switching to
`wsl -d Debian -u root -- ...` for this one step unblocked it immediately — `npx playwright install --with-deps
chromium` found every required library (`libnss3`, `libatk*`, `libcups2`, `libdrm2`, `libxkbcommon0`, etc.)
**already installed system-wide**, so root simply had permission to confirm/use them where `admin` did not.

## Real browser smoke check — first attempt found a real bug
Launched headless Chromium (root, `--no-sandbox`) against the live Expo web bundle and navigated to it with
Playwright. First run surfaced a genuine `pageerror`:
```
Incompatible React versions: The "react" and "react-dom" packages must have the exact same version.
Instead got: react: 19.2.0, react-dom: 19.2.3
```
This was a real, previously-undetected bug: Round 2's `npx expo install react-dom react-native-web` pulled
`react-dom@19.2.3` (satisfying *its own* peer requirement) while `react` stayed pinned at the exact `19.2.0`
Round 1 had force-installed with `--legacy-peer-deps` over `react-native@0.85.0`'s real `^19.2.3` peer
requirement. The mismatch was latent (silently tolerated by `--legacy-peer-deps` at install time, invisible to
Jest/RNTL's virtual DOM, invisible to `tsc`) and only surfaced as an actual browser runtime error. **Fixed**:
bumped `react`, `react-dom`, and `react-test-renderer` all to `19.2.3` in lockstep — `npm ls` now shows a clean
dependency tree with zero `invalid` warnings, and `npx jest` (35/35) still passes after the fix.

## Real browser smoke check — after the fix
Re-ran the same smoke check against the fixed build:
```
TITLE: Login
BODY: "S / Fuvay Staff / Field Operations App / Sign In / Phone Number / Password / Sign In / ..."
ERRORS: []
```
Zero page errors, zero console errors. Repeated with the browser context's `colorScheme` set to both `'light'`
and `'dark'` — zero errors in either (see `light-dark-theme-report.md` for why the *visual* result is identical
in both, since there's no dark palette to switch to — this check only proves nothing *crashes* under either OS
setting).

## Round 4 re-verification (after NetworkStatusBanner wiring, a11y fixes, new System States showcase)
Re-ran the smoke check a final time against the Round 4 build (real network-status banner mounted in
`AppNavigator`, new nested `View` wrapper structure, 8 accessibility-attribute additions, new
`SystemStatesShowcaseScreen` registered): **zero errors**, same clean Login-screen render — confirms none of
this round's structural/component changes broke the app.

## Round 5 re-verification (after dark-theme mechanism, NetInfo, draft persistence, 2 more showcases)
Re-ran the same one-shot Metro-start + Playwright smoke check against the Round 5 build (new `ThemeProvider`
wrapping `App.tsx`, `AppNavigator`'s `NavigationContainer` now driven by a reactive `theme` prop, 5 components
converted to `useAppTheme()`, new `@react-native-community/netinfo` dependency, new `usePersistedDraft` hook,
2 new showcase screens registered): **zero page/console errors**, same clean Login-screen render. This is a
meaningful check specifically for this round because the `ThemeProvider`/`ThemeContext` change touches the
app's root render tree (every screen is now inside a new context provider) — a mistake there would plausibly
crash the whole app, and it didn't.

## What was NOT tested
- Deep-linking directly to an authenticated route (e.g. a specific dev showcase) via URL was not attempted —
  `AppNavigator`'s `NavigationContainer` has no `linking` config, so there is no URL-to-route mapping to test
  against; reaching an authenticated screen requires a real login, which requires a real backend session this
  environment doesn't have. The Login screen (the one screen reachable without auth) is what was verified.
- No interaction testing (typing into the phone/password fields, tapping Sign In) was performed — this was a
  load-and-observe-errors smoke check, not a full interaction E2E test.
- No visual/screenshot comparison was performed.

## Process-lifecycle note (for future rounds)
Every real Metro-start-then-Playwright-check sequence had to run as **one single `wsl` invocation** ( `... & ;
sleep N; curl...; node smoke.js` all in one `bash -c` string). A backgrounded Metro process does NOT survive
between two *separate* `wsl.exe` tool calls in this environment, even with `nohup`/`disown` — confirmed
repeatedly across both Round 3 and Round 4 attempts. This is a hard constraint on how future rounds must
structure any live-server verification here.
