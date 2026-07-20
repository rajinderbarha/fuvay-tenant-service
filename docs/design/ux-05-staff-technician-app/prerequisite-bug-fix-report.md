# Prerequisite Bug-Fix Report

Real defects found and fixed during UX-05, in the order discovered. Each entry: symptom, root cause, fix,
verification.

## 1. `react`/`react-dom` version mismatch (Round 4)
**Symptom**: a real headless-browser `pageerror` — `Incompatible React versions: react 19.2.0, react-dom
19.2.3`. **Root cause**: Round 1 force-pinned `react@19.2.0` via `--legacy-peer-deps` over
`react-native@0.85.0`'s real `^19.2.3` peer requirement; Round 2's `expo install react-dom react-native-web`
separately resolved `react-dom@19.2.3` to satisfy its own peer, creating a real mismatch invisible to
`tsc`/`jest`/RNTL and only surfaced by an actual browser render. **Fix**: bumped `react`, `react-dom`, and
`react-test-renderer` to `19.2.3` in lockstep. **Verified**: `npm ls` clean tree, zero `invalid` warnings;
Playwright smoke check zero errors after the fix.

## 2. AsyncStorage-in-Jest failure after ThemeContext conversion (Round 5)
**Symptom**: `[@RNC/AsyncStorage]: NativeModule: AsyncStorage is null` when running tests for components newly
converted to require a `ThemeProvider` ancestor (which itself uses AsyncStorage for persistence). **Root
cause**: the community AsyncStorage Jest mock (`async-storage-mock.js`) is a plain exported object, not a
self-registering `jest.mock()` call — pointing `setupFiles` at it does nothing. **Fix**: used
`moduleNameMapper` to redirect the real import path to the mock file directly. **Verified**: all RNTL tests
requiring `ThemeProvider` pass.

## 3. `react-test-renderer` duplicate-instance bug from working-tree drift (Round 7 → Round 8 fix)
**Symptom** (reported via independent coordinator verification, not found by this agent's own re-verification):
a genuinely fresh `npm install` produced 13/43 test failures, all `"Unable to determine host component names"` /
`"Trying to detect host component names triggered the following error"` — the classic RNTL symptom of the test
renderer that actually rendered a tree being a different module instance than the one RNTL's assertions talk to.
`npm ls react-test-renderer` in that failing state showed `jest-expo@54.0.17` pulling its own nested
`react-test-renderer@19.1.0` against a root-pinned `react-test-renderer@19.2.0` — two real, distinct instances of
the same package, the same category of bug as fix #1 above, just for a different package.

**Root cause, confirmed by direct investigation**: this agent's own committed `mobile/staff-app/package.json` at
every relevant commit (checked via `git log`/`git diff` against `HEAD`) has always pinned
`jest-expo: "~56.0.0"` and `react-test-renderer: "19.2.3"` (matching fix #1's `react`/`react-dom` bump) — **not**
`~54.0.0`/`19.2.0`. The failing state the coordinator (correctly) caught existed only in the real, uncommitted
**working tree** at `G:\serviceos\mobile\staff-app\package.json` and `package-lock.json`, which had reverted to
older values (`expo: "~54.0.36"`, `react: "19.2.0"`, `jest-expo: "~54.0.0"`, `react-test-renderer: "19.2.0"`,
`react-dom: "19.2.0"`) not present in any commit on this branch. This was working-tree drift from outside this
agent's control (the same shared-working-directory class of issue documented in the Round 4→5 concurrent-process
branch incident elsewhere in this doc set) — not a defect introduced by any UX-05 commit. Confirmed by running
`git diff mobile/staff-app/package.json` against `HEAD` and observing the exact drifted values before restoring.

**Fix**:
1. `git checkout -- mobile/staff-app/package.json mobile/staff-app/package-lock.json` to restore the correct,
   already-committed pins.
2. Added a defensive `"overrides": {"react-test-renderer": "19.2.3"}` to `package.json` — cheap insurance so
   that even if a transitive dependency (like `jest-expo`) ever tries to pull a different
   `react-test-renderer` version, npm's overrides mechanism forces single-instance resolution regardless of
   resolution order. `npm ls` after this shows `react-test-renderer@19.2.3 overridden`.

**Verified** (twice, independently, both from a fully deleted `node_modules` + `package-lock.json`):
- `npm install --legacy-peer-deps` (fresh lockfile generation): 871 packages, `npm ls react-test-renderer` shows
  single deduped/overridden `19.2.3`, `npx jest` → 43/43 passing, `npx tsc --noEmit` → 19 errors (unchanged
  pre-existing pattern).
- `npm ci --legacy-peer-deps` (strict install from the committed lockfile, the most deterministic possible
  check): identical result — 43/43 passing.

**Process note for future rounds**: per the coordinator's instruction, every future round's final report must
be based on test/typecheck numbers obtained after a genuinely fresh install (`rm -rf node_modules` first, not a
reused `node_modules` from earlier in the session) — this incident is the concrete reason why.
