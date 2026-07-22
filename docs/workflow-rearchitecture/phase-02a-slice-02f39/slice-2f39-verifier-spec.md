# Slice 2F-39 Verifier Spec

A dedicated `verify_2f39.py` with all ~20 mission-specified failure
conditions and executed negative fixtures was **not built this slice** —
same honest gap as 2F-38's equivalent, for the same reason (substantial
standalone engineering effort not achievable alongside the concrete
remediation work this slice prioritized).

## What exists and was reused/extended

- `verify_2f37.py` (21/21 PASS, re-run fresh at start and end of this
  slice) — covers canonical coverage, Set A/B/C hashes, M01/geo/2F-35/36
  non-regression, N01 non-regression.
- `test_phase2f39_seed_role_guard.py` (28 tests, itself a real negative-
  fixture suite) — covers: live seed path accepts invalid role (10 alias
  variants + empty + mixed-case, all proven to fail closed before any db
  call), canonical roles all accepted, existing-user mismatch not silently
  promoted, idempotency.

## Gaps (same categories as 2F-38, narrowed where this slice made progress)

| 2F-39 required condition | Status |
|---|---|
| A live seed path accepts an invalid role | **Covered** — 28 negative-fixture tests, both known live gaps fixed |
| `manager`/`readonly` accepted as a role | **Covered** — explicitly parametrized in the new test suite |
| A mutation-like route remains unclassified | **NOT covered** — 261 routes remain unclassified; no verifier checks this count |
| Demo-account roles changed without approval | **Covered by absence** — no code path exists this slice that could do this; not proven by an executed negative fixture |
| Migration 144 executes with ambiguous mappings | **NOT covered** — no PostgreSQL to exercise this against |
| A test-order dependency remains | **Partially covered** — the one found-and-fixed instance is proven fixed (`test-order-root-cause.md`); no general-purpose test-isolation scanner exists |
| Full-backend failures disappear without disposition | **Covered by process** — `remaining-failure-disposition.csv` accounts for all 45 original failures; not enforced by an automated verifier rule |
