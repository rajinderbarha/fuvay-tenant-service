# CUSTOMER-L5-02 — Test Evidence

```
npx jest
Test Suites: 42 passed, 42 total
Tests:       291 passed, 291 total
```

(267 carried over from CUSTOMER-L5-00/01/03 [note: L5-03 was implemented
in the same session, after the first CUSTOMER-L5-02 pass — see
`CUSTOMER-L5-03-*` docs], 24 new/changed in this deepened CUSTOMER-L5-02
pass.)

## New/Changed Test Files (this pass)

| File | Count | Covers |
|---|---|---|
| `api/__tests__/api-client.test.ts` | 4 | 401→refresh→retry-once, no-retry-on-second-401, propagation when refresh fails, `skipAuth` requests never invoke the handler |
| `features/auth/state/__tests__/auth-refresh-coordinator.test.ts` | 4 | handler registration, successful refresh+persist, failed-refresh session clearing, single-flight concurrent-call sharing |
| `features/auth/state/__tests__/session-bootstrap.test.ts` (rewritten) | 3 | guest-with-no-tokens, authenticated-with-valid-tokens, transient-failure resilience (401-handling test moved to the coordinator's own suite, where that responsibility now lives) |
| `features/auth/state/__tests__/session-store.test.ts` (+1) | 7 | added: secure-storage write failure still marks the session authenticated in-memory (with a warning logged) |
| `features/auth/domain/__tests__/session-summary-schema.test.ts` | 4 | valid session, nullable device fields, missing-field rejection, non-boolean rejection |
| `features/auth/domain/__tests__/auth-state.test.ts` | 9 | full `deriveAuthState` priority ordering across all derived states |
| `features/auth/hooks/__tests__/use-logout-all.test.tsx` | 2 | success + server-failure paths, both confirming local session clearing |

## Contract/Schema Test Fixtures

`session-summary-schema.test.ts`'s fixtures and `session-bootstrap.test.ts`/
`auth-refresh-coordinator.test.ts`'s mocked `AuthUserProfile` objects are
built field-for-field from the real backend's
`_user_to_profile`/`list_sessions` return shapes (read from
`app/engines/auth/service.py`), not invented.

## Not Covered This Pass

- No component tests for `SessionsScreen`/`ProfileScreen`/`OtpLoginScreen`
  — same rationale as every previous sprint (pure logic + integration-
  boundary logic prioritized over component rendering tests).
- No true integration test against a real HTTP server (see
  `CUSTOMER-L5-02-runtime-evidence.md` — no backend was reachable in this
  environment).
- No multi-tenant/cross-marketplace isolation test — UNVERIFIED per the
  security review (single-marketplace test environment).
- No device-level test of secure-storage persistence surviving an app kill.
- No performance measurement (CUSTOMER-L5-02 §60) — no profiling tooling
  was run; no numeric claims are made anywhere in this sprint's docs.

## Regression Confirmation

All 267 tests from CUSTOMER-L5-00/01/03 (as they stood before this pass)
continue to pass unchanged — `startup-route-resolver.test.ts`,
`route-guards.test.ts`, `remote-config-*`, `deep-link-*`, and the L5-03
`home` tests were re-run as part of every `npx jest` invocation in this
pass and never needed modification (except the one pre-existing
`route-guards.test.ts` line already adjusted when `home.productionEnabled`
flipped to `true` in the CUSTOMER-L5-03 pass, which is unrelated to this
CUSTOMER-L5-02 hardening pass).
