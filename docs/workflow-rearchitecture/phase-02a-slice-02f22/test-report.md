# Test Report — Slice 2F-22

## New suite
`tests/test_phase2f22_tenant_package_purchase_authorization.py` — **50 passed**

| Class | Tests | Covers |
|---|---|---|
| `TestRouteAuthorizationWiring` | 4 | WS4/WS19 — persona, mutation scope, read-only denial |
| `TestRequestFieldAuthority` | 21 | WS7 — 18 parametrized dangerous fields rejected, not ignored |
| `TestMarkPaidRemoved` | 4 | WS8 — no client path to paid state |
| `TestServiceLayerPaymentAuthority` | 7 | WS16 — service-layer gate; fail-closed with `db=None` |
| `TestLegitimateCallersPreserved` | 4 | WS15 — both authoritative callers intact; signature precedes paid assignment |
| `TestServerPriceAuthority` | 3 | WS9 — all financial fields package-derived |
| `TestNoActivationOrCreditIssuanceOnPurchase` | 3 | WS12 — no activation/credits at purchase; idempotent at activation |
| `TestDuplicatePurchaseGuard` | 2 | WS13 — duplicate rejection, tenant+package scoped |
| `TestTenantAuthority` | 3 | WS5 — server-derived tenant |

Three tests deliberately construct the service with `db=None` so that a guard
firing after any DB interaction would surface as `AttributeError` rather than
the expected domain error — making them double as no-partial-persistence
proof.

## Recount and prior-slice suites
`test_phase2f14a` + `test_phase2f17a` + `test_phase2f19` + `test_phase2f20` +
`test_phase2f21` + `test_phase2f5c` + `test_sprint5_packages` —
**406 passed, 0 failed**.

## Wider payment/package/registration/finance
14 files — **752 passed, 5 failed**. All 5 are pre-existing live-environment
failures with node IDs byte-identical to the baseline
(`regression-report.md`).

## Full repository
**11108 passed, 86 failed, 111 errors, 14 skipped** (652.97s).
Zero newly-failing node IDs; one resolved.

## Reporting breakdown

| Category | Count |
|---|---|
| Passing | 11108 |
| Skipped | 14 |
| **Failures attributable to this slice** | **0** |
| Pre-existing unrelated failures | 86 |
| Errors (collection/setup, live-env) | 111 |
| Live-environment exclusions | all DB/HTTP-backed tests |

## Environment exclusions stated plainly

No database or live HTTP server exists here. Every new test is a
deterministic source, schema, or signature assertion. Live two-session
concurrency behaviour and end-to-end HTTP authorization were **not** verified
and are not claimed — see `known-limitations.md` items 2 and 3.
