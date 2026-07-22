# ThemeContext Flake Reproduction

## Observed failure

During independent verification of Pass 3b (fresh WSL install,
`/root/serviceos-ux07-verify-p3b/customer-app`), 4 of 5 consecutive
`npx jest` runs gave `58 passed, 58 total`. One run gave:

```
Test Suites: 2 failed, 5 passed, 7 total
Tests:       2 failed, 56 passed, 58 total
```

with the failure located in
`src/context/__tests__/ThemeContext.test.tsx`, at the assertion inside
`it("defaults to system preference and resolves to the current system
scheme", ...)` (line 33), asserting `mode === "light"` after `waitFor(loaded
=== "true")`.

## Root-cause investigation

Inspected `mobile/customer-app/src/context/ThemeContext.tsx`:

- `systemScheme` state is seeded from `Appearance.getColorScheme()` at
  mount (correctly mocked to `"light"` in the test's `beforeEach`).
- A second `useEffect` registers `Appearance.addChangeListener(({colorScheme})
  => setSystemScheme(colorScheme))` — **this was never mocked** in the test
  file. Only `getColorScheme` had a `jest.spyOn` mock.

On a machine/CI runner whose actual OS or (for `react-native-web`/jsdom test
environment) browser `prefers-color-scheme` is `dark`, the real listener
fires asynchronously shortly after mount and updates `systemScheme` away
from the mocked `"light"` value, flipping the resolved `mode` before or
during the test's assertions — an intermittent race whose timing depends on
the host environment's actual color-scheme preference and event-loop
scheduling, not on anything deterministic in the test itself.

## Classification

**Mock lifecycle leakage** (a missing mock, not a ThemeContext production
race): `getColorScheme` was mocked but the live-update `addChangeListener`
subscription was left wired to the real implementation, letting an
uncontrolled external signal reach component state during the test.

This is not a production defect — real users legitimately want the
`Appearance.addChangeListener` behavior; the problem was solely in the test
harness's incomplete mock setup.
