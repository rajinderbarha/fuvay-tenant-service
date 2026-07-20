# Runtime Verifier Hardening — Slice 2F-25A

## The problem being fixed

Slice 2F-25's `runtime-verification-report.md` stated "Runtime verification
exits zero" while three mounted read routes were **knowingly** unscoped and
`create_request` had no parent-ownership proof. There was no verifier script
at all; the claim rested on a test suite that did not test those conditions.

A verifier that cannot fail launders an incomplete result as a clean one. That
is worse than having none.

## What now exists

`scripts/workflow_rearchitecture/verify_legacy_review.py` — runnable, exits
non-zero on any failure, prints PASS/FAIL per check.

### Checks (25)

| Group | Checks |
|---|---|
| Mutation authorization | `submit_reply`/`flag_review` use the scoped lookup and contain no primary-key-only lookup (4) |
| Route personas | the three tenant mutations use the scope-aware permission; `resolve_flag` stays super-admin (4) |
| **Read scoping** | all three 2F-25 residuals + `get_review` are scoped (4) |
| Tenant authority | all five tenant-taking methods pin the tenant (5) |
| create_request parentage | Job resolved, tenant-scoped, customer derived, mismatch rejected, no pipeline adaptation, ownership before duplicate check (6) |
| Internal caller | `field_ops` passes tenant context and marks itself trusted (2) |
| Legacy retirement | 410 preserved; no mounted route calls `create_review` (2) |
| Documentation honesty | no application-wide-completeness label present; coverage labelled `CURRENT_CANONICAL_COVERAGE` (2) |

### Docstring stripping

`_code()` removes docstrings and comments before matching. Both 2F-24 and this
slice wrote assertions satisfied by **prose** rather than code:

- 2F-24 matched `Depends(get_current_user)` inside a comment describing its
  removal.
- 2F-25A matched `ServiceJob` inside a docstring saying it is NOT used.

A verifier check that a comment can satisfy is not a check.

### The documentation-honesty checks

Two checks read this slice's own markdown and fail if it claims application-
wide completeness or omits the `CURRENT_CANONICAL_COVERAGE` label. The
verifier polices the report, not just the code — directly addressing the
mission's requirement that documentation must not narrow "privacy closure" to
dodge a known mounted route.

## Proof it is not vacuous

`TestVerifierIsNotVacuous` (3 tests):
- it passes on the current tree;
- feeding it a failing condition produces a recorded failure;
- a function whose **docstring** mentions a required token but whose body does
  not is correctly seen as NOT containing it.

## Current result
All checks PASS; exit code 0. That statement is now worth something.
