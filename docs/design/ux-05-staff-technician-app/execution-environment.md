# UX-05 Execution Environment

## Branch / baseline
- Branch: `design/ux-05-staff-technician-app`, based on UX-04B final commit `7488335`.
- `git diff --stat 7488335...HEAD -- frontend/tenant-portal frontend/super-admin frontend/customer-app mobile/customer-app app/` returns empty at every checkpoint in this pass — zero out-of-scope changes.
- The ~230 modified backend files present in the working tree at session start (per gitStatus) are pre-existing uncommitted changes from parallel authorization work and were never touched, staged, or committed by this phase.

## Target app: mobile/staff-app
Verified by reading `package.json` directly (not assumed):
- Expo `~56.0.12`, React Native `0.85.0`, React `19.2.0`.
- Navigation: `@react-navigation/native` v7, `native-stack` v7, `bottom-tabs` v7.
- `@react-native-async-storage/async-storage`, `expo-location`, `expo-notifications`, `expo-status-bar`, `react-native-maps`, `@expo/vector-icons`.
- No test framework was present before this phase (only `eslint` in `devDependencies`/scripts). No lockfile existed.
- No `@types/react-native` install target exists for RN 0.85 (that package's last usable major predates RN's bundled types) — it was a stale devDependency; removed.

## mobile/staff-app has no shared design-system dependency
`frontend/packages/design-system` (UX-01, web/CSS-vars based) is not imported anywhere in `mobile/staff-app`. The app has its own plain-object theme at `src/styles/theme.ts` (colors/spacing/font/radius/shadow) plus shared `StyleSheet.create` globals (`gs`) reused across every screen. UX-05 extends this existing pattern (`src/components/ux05/*`, `src/types/ux05.ts`, `src/lib/ux05/*`) rather than importing the web package, which would not run in React Native. No design-system package changes were made or needed.

## WSL verification setup
- WSL distro: Debian, user `admin` (not root — `sudo` available), Node `v20.20.2`, npm `10.8.2` — matches the memory note's expected toolchain except the user is `admin`, not `root`; used `/home/admin/serviceos-ux05/mobile/staff-app` (native ext4, not `/mnt/g/...`) instead of a `/root/...` path.
- Copied `mobile/staff-app` via `rsync -a --exclude node_modules --exclude .expo` into the WSL native path.
- `npm install` initially failed twice:
  1. `ERESOLVE`: `react-native@0.85.0` peers `react@^19.2.3`, but `react@19.2.0` was pinned exactly. Resolved with `--legacy-peer-deps` (documented, not silently forced without record).
  2. `ETARGET`: `@types/react-native@^0.74.0` does not exist (deprecated package; RN 0.85 ships its own types). Removed the stale devDependency from `package.json`.
- After both fixes: `npm install --legacy-peer-deps` succeeded, 850 packages installed. `package-lock.json` generated in WSL and copied back into the real git repo (`mobile/staff-app/package-lock.json`), then committed for real from `G:\serviceos`.
- Added `jest`, `jest-expo`, `react-test-renderer`, `@testing-library/react-native`, `@react-native/jest-preset` (RN 0.85+ moved this out of `jest-expo`'s bundled preset — jest failed with `Validation Error` until installed explicitly), and `@types/jest` as devDependencies, plus `typecheck`/`test`/`web` npm scripts (none existed before).

## What was actually run and verified in WSL
- `npm install --legacy-peer-deps` — real, succeeded, 850 packages (see `staff-technician-build-report.md`).
- `npx tsc --noEmit` — real, ran to completion; found pre-existing type errors in files this phase did not author (see `typecheck-report.md`) and confirmed zero errors in every UX-05-authored file.
- `npx jest src/lib/ux05 src/types/__tests__` — real, 12/12 passing (see `unit-component-test-report.md`).

## Not attempted / explicit boundary
- `expo start --web` and Playwright browser verification were not reached in this pass (see `deferred-items.md`) — WSL setup, dependency resolution, view-model layer, and a first batch of components/screens/tests took priority given the session's realistic budget. This is an honest scope boundary, not a claim that Expo web is nonviable — it has not yet been attempted.
- Native emulator/simulator: not available in this WSL setup (no GUI/emulator), consistent with the brief's expectation.
