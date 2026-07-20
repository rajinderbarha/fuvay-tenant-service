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

## Playwright headless-browser runtime check (Round 3 — blocked; Round 4 — unblocked, real bug found and fixed)
Round 3: installed Playwright 1.61.1 and downloaded Chromium (177 MiB) successfully under the `admin` WSL user.
Launching headless Chromium against the live bundle failed with `SIGSEGV` — `sudo -n true` confirmed
passwordless sudo wasn't available to install the missing OS shared libraries, a concrete diagnosed blocker.

Round 4: switched to the WSL Debian instance's **root** user (`wsl -d Debian -u root`), which needs no `sudo` at
all. `npx playwright install --with-deps chromium` as root found every required library already installed
system-wide. Headless Chromium launched successfully. The **first real run found a genuine bug**: a page error —
`Incompatible React versions: react 19.2.0, react-dom 19.2.3` — caused by Round 1's forced `react@19.2.0`
(via `--legacy-peer-deps`, overriding `react-native@0.85.0`'s real `^19.2.3` peer requirement) never actually
matching the `react-dom@19.2.3` Round 2 installed. This was invisible to `tsc`/`jest`/RNTL and only surfaced as
a real browser runtime error — exactly the kind of defect headless-browser verification exists to catch.
**Fixed**: bumped `react`/`react-dom`/`react-test-renderer` to `19.2.3` in lockstep. Re-ran the smoke check:
**zero page/console errors**, Login screen renders correctly, confirmed in both light and dark browser
color-scheme contexts, and again after this round's further changes (NetworkStatusBanner wiring, a11y fixes,
new showcase). See `runtime-test-report.md` for the full account.

## Native runtime (emulator/simulator)
Not available in this WSL setup (no GUI/emulator), consistent with the brief's expectation. Not attempted.

## Overall
Dependency resolution, typecheck, unit/component tests, the Expo-web bundle build, AND the headless-browser
runtime load are now all proven real and working end-to-end in WSL against the current source — including
catching and fixing one genuine bug (`react`/`react-dom` version mismatch) that no other verification layer in
this project (typecheck, unit tests) was capable of catching.
