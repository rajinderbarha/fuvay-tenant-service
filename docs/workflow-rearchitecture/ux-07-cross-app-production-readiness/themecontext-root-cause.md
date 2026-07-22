# ThemeContext Test Flake — Root Cause

**Classification: Mock lifecycle leakage (test-only), not a ThemeContext
production race, not test-order dependency, not an AsyncStorage hydration
race.**

## Why each other candidate was ruled out

- **AsyncStorage cleanup**: `beforeEach` already calls `await
  AsyncStorage.clear()` before every test; `AsyncStorage.getItem` mock
  behavior was consistent across all 25+10+5 repeated runs performed for
  this pass with no AsyncStorage-related failures observed.
- **Appearance.getColorScheme mocking**: was already correctly mocked with
  `jest.spyOn(...).mockReturnValue("light")` in `beforeEach`, and restored
  via `jest.restoreAllMocks()` in `afterEach`. Not the source.
- **Appearance listener registration** (the actual cause): `addChangeListener`
  was never mocked, leaving the component subscribed to the real
  environment's live color-scheme signal for the full duration of the
  `render()` call in every test.
- **Provider hydration timing / React state-update timing**: the
  `isLoaded` gate and `waitFor` on it worked correctly in every repeated
  run; the race was specifically in `systemScheme`, a value gated by
  nothing (it's read synchronously at mount and can change any time
  afterward via the listener).
- **act()/waitFor() usage**: correct in all cases; the flake was not a
  `console.error` "not wrapped in act()" warning, it was a genuine
  assertion-value mismatch.
- **Fake vs. real timers**: the suite uses real timers throughout; no
  fake-timer interaction was involved in the failure.
- **Module cache / test ordering**: the 10x full-`ThemeContext.test.tsx`
  and 5x full-customer-suite repeated runs (which include other test files
  running before/after this one, in varying orders across parallel jest
  workers) all passed after the fix, and the original failure was isolated
  to this single test regardless of ordering — ruling out cross-test state
  leakage as the cause.
- **Mock restoration**: `jest.restoreAllMocks()` in `afterEach` correctly
  restores every `jest.spyOn` mock; the issue was a spy that was never
  created in the first place for `addChangeListener`, not one that leaked
  between tests.

## The fix

Added `jest.spyOn(Appearance, "addChangeListener").mockImplementation(() =>
({ remove: () => {} }))` to the same `beforeEach` block that already mocks
`getColorScheme`, restored automatically by the existing
`jest.restoreAllMocks()` in `afterEach`. This removes the uncontrolled
external signal without touching `ThemeContext.tsx` itself, without adding
timeouts/retries/sleeps, and without weakening any assertion.
