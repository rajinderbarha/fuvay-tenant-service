# Staff/Technician Build Report

## npm install (WSL)
`npm install --legacy-peer-deps` in `/home/admin/serviceos-ux05/mobile/staff-app`: **succeeded**, 850 packages
(Round 1) + 19 for `react-dom`/`react-native-web` (Round 2). `package-lock.json` generated and committed to the
real repo both times.

## Expo web bundle build (Round 3 — real, verified)
`CI=1 npx expo start --web --port 8082` started Metro successfully. Verified for real, within one continuous
backgrounded shell session:
- `curl http://localhost:8082` → **HTTP 200**.
- `curl 'http://localhost:8082/index.bundle?platform=web&dev=true'` → **HTTP 200**, **3,117,007 bytes**.
- Confirmed the bundle contains this round's actual compiled UX-05 source (grepped for and found the compiled
  `NetworkStatusBanner` component, including its `StyleSheet.create` object and Fast Refresh registration) — not
  just the pre-existing app code.

This proves the Expo web **build/bundle pipeline works end-to-end** for the current state of the app, including
everything built across all three UX-05 rounds.

## Playwright headless-browser runtime check (Round 3 — attempted, specific blocker found)
Installed Playwright 1.61.1 and downloaded Chromium (177 MiB) successfully. Launching headless Chromium against
the live bundle failed with `SIGSEGV`. Root cause: the OS-level shared-library dependencies headless Chrome
needs are not installed in this WSL image, and installing them
(`npx playwright install-deps` / equivalent `apt-get`) requires `sudo`; `sudo -n true` returns
`sudo: a password is required` in this environment, i.e. passwordless sudo is not configured here. This is a
concrete, reproducible, diagnosed environment limitation — not a code defect, and not an ambiguous "it didn't
work." The runtime smoke check (loading the page in a real browser and checking for console errors) could not
be completed; the build step it depends on is proven to work.

## Native runtime (emulator/simulator)
Not available in this WSL setup (no GUI/emulator), consistent with the brief's expectation. Not attempted.

## Overall
Dependency resolution, typecheck, unit/component tests, and the Expo-web bundle build are all proven real and
working end-to-end in WSL against this round's actual source. The one verification step not completed is the
final headless-browser runtime load, blocked by a specific, diagnosed, non-code environment issue (missing sudo
access to install Chromium's system dependencies).
