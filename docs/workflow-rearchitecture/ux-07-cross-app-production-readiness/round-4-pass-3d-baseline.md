# UX-07 Round 4 Pass 3d — Baseline

Worktree: `G:/serviceos-ux07-cross-app`, branch `design/ux-07-cross-app-production-readiness`.
Starting HEAD: `8a78724` ("UX-07 Round 4 Pass 3c docs: flake reproduction, root
cause, fix report, repeated-run stability proof").

## Pre-flight checks

- `git status`: clean except the two expected untracked entries
  (`mobile/customer-app/.expo/`, `mobile/customer-app/package-lock.json`) —
  no concurrent-worktree interference detected.
- `git diff --stat mobile/customer-app/app.json mobile/customer-app/package.json`:
  empty (no drift from HEAD) both before this pass's changes and re-verified
  after every install/typecheck/test run below.

## Baseline test count

Before this pass's changes: **58/58** tests passing across 7 suites (matches
the count quoted in the brief; re-confirmed directly rather than assumed):

```
Test Suites: 7 passed, 7 total
Tests:       58 passed, 58 total
```

(Existing suites: `api.test.ts`, `AuthContext.test.tsx`,
`bookingContract.test.ts`, `chatBookingState.test.ts`,
`noInternalJargon.test.ts`, `theme.test.ts`, `ThemeContext.test.tsx`.)

## Baseline typecheck

`npx tsc --noEmit`: 0 errors before this pass's changes.

## Environment

WSL Debian, `~/work/customer-app` (rsynced copy of
`mobile/customer-app`, excluding `node_modules`/`.expo`), one
`npm install --legacy-peer-deps --no-audit --no-fund`, then iterated with
`npx tsc --noEmit` / `npx jest` against that copy.
