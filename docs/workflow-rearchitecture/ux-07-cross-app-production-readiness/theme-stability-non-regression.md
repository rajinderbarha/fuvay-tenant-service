# Theme Stability Non-Regression Check — UX-07 Pass 3d

Re-running Pass 3c's stability proof to confirm this pass's changes did not
regress it (Home/SmartBot/nav changes touch zero files under
`src/context/` or `src/styles/`).

## Targeted runs

`npx jest src/context/__tests__/ThemeContext.test.tsx` × 10 consecutive
runs, in WSL Debian against the rsynced + freshly `npm install`-ed copy:

```
Run 1:  Tests: 5 passed, 5 total
Run 2:  Tests: 5 passed, 5 total
Run 3:  Tests: 5 passed, 5 total
Run 4:  Tests: 5 passed, 5 total
Run 5:  Tests: 5 passed, 5 total
Run 6:  Tests: 5 passed, 5 total
Run 7:  Tests: 5 passed, 5 total
Run 8:  Tests: 5 passed, 5 total
Run 9:  Tests: 5 passed, 5 total
Run 10: Tests: 5 passed, 5 total
```

10/10 — matches Pass 3c's proof, no regression.

## Full-suite repeat runs

`npx jest` (whole suite, all 10 suites including the 3 new ones added this
pass) × 5 consecutive runs:

```
Run 1: Test Suites: 10 passed, 10 total | Tests: 69 passed, 69 total
Run 2: Test Suites: 10 passed, 10 total | Tests: 69 passed, 69 total
Run 3: Test Suites: 10 passed, 10 total | Tests: 69 passed, 69 total
Run 4: Test Suites: 10 passed, 10 total | Tests: 69 passed, 69 total
Run 5: Test Suites: 10 passed, 10 total | Tests: 69 passed, 69 total
```

5/5 — no flakiness introduced by this pass's new tests or source changes.

## What was and wasn't touched

- `src/context/ThemeContext.tsx`, `src/styles/theme.ts`: untouched, per the
  explicit instruction not to touch the working ThemeContext.
- New test-file-local workarounds (`jest.mock` of `Skeleton`,
  `jest.spyOn(Animated, "timing")`) exist only in the 3 new test files
  added this pass (`HomeScreen.test.tsx`, `TabNavigator.test.tsx`,
  `DeepSeekChatScreen.handoff.test.tsx`) and do not touch
  `ThemeContext.test.tsx` or any of Pass 3c's fixed test infrastructure.

## Pass 3f addendum (accessibility remediation)

- `ThemeContext.tsx` and `theme.ts` were **not touched** this pass (no
  diff).
- Targeted `ThemeContext.test.tsx` re-run **5 times consecutively** in a
  fresh WSL install: **5/5 tests passing every run**, 0 flakes.
- Full suite (76/76, up from baseline 73/73 — see
  `customer-test-report.md`) run 3 consecutive times with 0 failures,
  which also exercises `ThemeProvider` indirectly through every screen
  test.
- No regression in dark-mode rendering: the new Playwright screenshots
  (`screenshots/default-light.png`, `screenshots/default-dark.png`) show
  the theme system correctly switching the LoginScreen's sign-in card
  between light/dark surfaces in an actual browser render.
