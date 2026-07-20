# CUSTOMER-L5-01 — Testing Evidence

## Automated Test Run

```
npx jest
Test Suites: 30 passed, 30 total
Tests:       212 passed, 212 total
```

(88 tests carried over from CUSTOMER-L5-00, 124 new this sprint.)

## New Test Files (CUSTOMER-L5-01)

| File | Count | Covers |
|---|---|---|
| `remote-config/__tests__/version-policy.test.ts` | 15 | semver comparison, all `VersionPolicyOutcome`s, grace period, platform store URL selection |
| `remote-config/__tests__/maintenance-policy.test.ts` | 7 | none/scheduled/active/expired, blocking vs read-only, retryAllowed passthrough |
| `remote-config/__tests__/remote-config-schema.test.ts` | 11 | valid envelope, unsupported schema version, duplicate module key, unknown/cyclic dependency, insecure URL, expiry ordering, maintenance window validity, fallback-route consistency |
| `remote-config/__tests__/remote-config-evaluator.test.ts` | 9 | all `ModuleEvaluation` outcomes including dependency chains and maintenance override |
| `remote-config/__tests__/remote-config-cache.test.ts` | 7 | environment/marketplace binding, expiry, max-age, stale-permitted |
| `remote-config/__tests__/config-integrity.test.ts` | 5 | environment mismatch, marketplace mismatch, untrusted origin, unverified-but-trusted-origin, local→development binding |
| `app/startup/__tests__/startup-machine.test.ts` | 8 | reducer purity, phase recording, retry-after-failure phase history, terminal states |
| `app/startup/__tests__/startup-route-resolver.test.ts` | 11 | full priority order incl. "deep link cannot bypass maintenance/mandatory-update" |
| `navigation/deep-links/__tests__/deep-link-parser.test.ts` | 6 | custom-scheme parsing, query extraction, trusted/untrusted host classification, oversized/malformed rejection |
| `navigation/deep-links/__tests__/deep-link-validator.test.ts` | 10 | valid routes, all rejection reasons (unknown scheme/host/path, malformed param, unexpected/token-like query, nested redirect, expired, cross-marketplace) |
| `navigation/deep-links/__tests__/pending-deep-link-store.test.ts` | 4 | consume-once, peek non-destructive, TTL expiry, explicit clear |
| `navigation/__tests__/route-guards.test.ts` | 12 | full guard precedence order |
| `navigation/__tests__/notification-intent.test.ts` | 6 | allowlist enforcement, expiry, malformed params, consume-once dedup |
| `navigation/__tests__/navigation-service.test.ts` | 3 | not-ready state, unknown-route rejection, safe queuing |

## What Is Not Covered

- No React component tests for the new system screens
  (`StartupScreen`/`MaintenanceScreen`/etc.) — these require mocking
  `useStartup()`'s context, which was deprioritized this sprint in favor of
  the pure-logic layer (state machine, resolver, validators, policies),
  which carries materially higher defect-catching value per test written.
  Tracked in `known-gaps.md`.
- No integration test exercising `startup-service.ts#runStartup` end-to-end
  against a mocked `fetch` (the individual pieces it orchestrates —
  cache, client, resolver, machine — are each tested in isolation, but the
  orchestration glue itself is only exercised manually/by inspection).
- No E2E test (no Detox/Maestro in this repository — same gap noted in
  CUSTOMER-L5-00).
- No device-level test of the custom-scheme deep link actually opening the
  app (requires a physical device/simulator, unavailable in this
  environment).
