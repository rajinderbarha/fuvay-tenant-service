# Full Customer Suite Stability Report

Environment: same fresh WSL install as `targeted-stability-report.md`.

## Full customer-app suite — 5 consecutive runs

Command per iteration: `npx jest`

Each run required (and got) `Tests: 58 passed, 58 total` across all 7 test
suites (`chatBookingState.test.ts`, `api.test.ts`,
`bookingContract.test.ts`, `theme.test.ts`, `noInternalJargon.test.ts`,
`AuthContext.test.tsx`, `ThemeContext.test.tsx`).

Result: **5/5 runs, 58/58 tests each**, 0 failures, no retries used.

## Typecheck

`npx tsc --noEmit` → 0 output lines, 0 errors.
