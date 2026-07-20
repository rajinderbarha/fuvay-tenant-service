# Slice 2F-38 Verifier Spec

A dedicated `verify_2f38.py` implementing all ~25 failure conditions listed
in this slice's mission, each with an executed negative fixture, was
**not built this slice** — that is a substantial standalone engineering
effort (comparable to `verify_2f37.py`'s own build, which took a full
slice) and was not achievable within this run's scope alongside the
recovery/certification investigation work.

## What exists and was reused as-is

`scripts/workflow_rearchitecture/verify_2f37.py`, 21 rules (R01-R21), each
with its own inline assertion against live introspected state (not a
static assumption) — see `verifier-reexecution-report.md` /
`targeted-test-report.md`. These 21 rules cover the following required
2F-38 failure conditions directly:

| 2F-38 required condition | Covered by |
|---|---|
| Canonical coverage is not 313/313 | R13, R19, R20 |
| A canonical row is stale or duplicated / Set A/B/C hash mismatch | R01 |
| A held candidate remains pending / Set B undispositioned | R03 |
| A Set C route is newly protected (mis-tracked) | R16 |
| M01/geo/2F-35/2F-36 sample regression | R15 |
| N01 falsely declared domain-integrity closed | R17, R21 |
| Document overclaims application-wide closure | R18 |

## What is NOT covered by any existing negative fixture (gap)

- Baseline-is-not-01e6ee4 (this slice's own guard covers worktree/branch
  identity, not this specific commit hash as a verifier rule)
- A mounted mutation remains UNKNOWN (no existing rule checks the full
  2,320-route census; `mutation-disposition-census.md` documents 261
  UNVERIFIED routes as an open gap, not a passing/failing check)
- Platform-admin/customer/internal-callback boundary violations
- Unknown role/scope admission (no existing rule directly tests this;
  `canonical-role-certification.md`'s live introspection is evidence, not
  an executable negative-fixture test)
- Migration 144 apply/rollback/reapply (blocked entirely — no PostgreSQL)
- StaffPermission cross-tenant grant success (existing mocked tests cover
  this at the unit level, not via this verifier script)
- Secret/storage-key leak, full-repository scan

This spec documents the gap honestly rather than claiming a verifier that
does not exist. See `slice-2f38-verification-report.md` for the combined
result (existing verifier + manual findings) and
`verifier-negative-fixture-report.md` for exactly which of the 21 existing
rules were reconfirmed to fire correctly when broken (inherited from
2F-37's own self-test, not re-derived from scratch this slice).
