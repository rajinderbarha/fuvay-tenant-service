# CUSTOMER-L5-02 — Baseline Verification

Re-ran `npx tsc --noEmit`, `npx eslint`, `npx prettier --check`, `npx jest`
against the current tree before starting.

## CUSTOMER-L5-00 Status

PARTIAL (as declared in its own final report) — architecture/design-system
baseline complete and gated; device-level a11y and native builds not
possible in this environment. No regressions found.

## CUSTOMER-L5-01 Status

Complete per this session's own work: startup orchestration, typed
navigation, remote-config, deep-linking, 7 system screens. 212/212 tests
passing at the end of that sprint, confirmed still passing now (re-run
below).

## Previous Defects Discovered

Carried into this sprint's scope: the pre-existing `src/lib/api.ts#authApi`
calls non-existent backend paths (`/v1/auth/customer/*`) — see
`CUSTOMER-L5-02-backend-contract-audit.md`. This was not previously
documented because CUSTOMER-L5-00/01 did not audit the auth backend
contract (out of scope for both).

## Previous Defects Fixed

None required — L5-00/L5-01 code is unaffected by this finding; it only
affects the pre-existing `LegacyApp` login screen, which this sprint does
not touch (see §"Migration" below).

## Unresolved Blockers

None.

## Existing Home / Discovery Implementation

Not relevant to this sprint (L5-02 scope is auth/session/profile only).

## Architecture Conflicts

None — `src/features/auth/` is a new, additive feature folder following
CUSTOMER-L5-00's documented feature-folder convention
(`architecture.md` §2). `AuthPlaceholderState` (defined in L5-01's
`route-guards.ts`) is now driven by a real session instead of a hardcoded
`"guest"` constant — this is the one integration point that changes L5-01
behavior, and it's additive (a new `useAuthSession()` hook feeds
`StartupProvider`, replacing the previous inline default).

## API Contract Gaps

See `CUSTOMER-L5-02-backend-contract-audit.md` — MFA, password reset, and
session management are real but unused this sprint; OTP hint dev-mode
exposure is guarded.

## Corrective Work Performed

None beyond what's listed above — this sprint adds new code rather than
fixing previous-sprint code.

## Validation Re-run

```
npx tsc --noEmit   → 0 errors outside pre-existing src/screens/*
npx eslint          → 0 errors, 37 warnings (pre-existing legacy screens)
npx jest             → 30 suites / 212 tests passing (pre-CUSTOMER-L5-02 baseline)
```
