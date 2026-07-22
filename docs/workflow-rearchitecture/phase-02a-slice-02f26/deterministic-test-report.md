# Deterministic Test Report — Slice 2F-26

`tests/test_phase2f26_application_wide_inventory.py` — **42 passed**

| Class | Tests | Purpose |
|---|---|---|
| `TestCanonicalArithmetic` | 6 | 257 / 214 / 43; no duplicates; no forbidden status |
| `TestGenericPrefixBlindSpot` | 10 | the discovered routes now have canonical rows; the mutating GET really does lazily create |
| `TestSweepArtifacts` | 17 | every artifact exists and is populated; every route has a behaviour; every mutation a persona; queue sums to 43; **every addition carries two-source evidence**; nothing removed |
| `TestVerifierDiscrimination` | 4 | negative fixtures (see `verifier-negative-fixture-report.md`) |
| `TestBehaviouralInvariants` | 3 | job-close review request still created; swallowed-exception block still documented |
| `TestNoAuthorizationChange` | 3 | prior closures intact; legacy 410 intact; scoped lookups intact |

## Anti-vacuity

- `test_every_addition_carries_two_source_evidence` asserts the evidence string
  contains **both** a tenant expression and a mutation expression, and that the
  tenant field is non-empty — a row cannot enter the denominator on one signal.
- `test_deposit_get_really_does_lazily_create` reads
  `CommerceService.get_deposit_status` and asserts `_get_or_create_deposit` is
  present, rather than trusting the classifier's label.
- `test_canonical_rows_exist_outside_tenant_prefixes` requires >= 60 such rows:
  a sweep that finds none has not looked.

## Recount suites re-run
`test_phase2f14a`, `2f17a`, `2f19`, `2f21`, `2f23`, `2f25`, `2f25a` —
**202 passed** after the 257/214 update.
