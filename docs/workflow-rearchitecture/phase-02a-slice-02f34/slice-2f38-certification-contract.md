# Slice 2F-38 Certification Contract

**Not executed in Slice 2F-34.** Executes AFTER Slice 2F-37 completes.

## Mission

Final reconciliation and certification only — no new canonical route
implementation. Verify and certify the cumulative output of Slices
2F-35, 2F-36, and 2F-37; perform final program-wide cleanup (role
constraints, Migration 144 readiness, readonly@ disposition).

## Preconditions (must all hold before starting; else stop with `AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`)

- Slices 2F-35, 2F-36, and 2F-37 have all reached their own approval
  gates with a recorded final status (any of the 6 allowed statuses,
  not necessarily full closure — mixed/blocked statuses are acceptable
  inputs to 2F-38, which certifies honestly rather than requiring prior
  perfection).
- Every one of the original 59 held candidates has a disposition other
  than `PENDING_MODULE_ADJUDICATION` (resolved, excluded, deprecated, or
  `PRODUCT_DECISION_REQUIRED` — the last is acceptable as a terminal
  state, since it remains visible in the product-decision registry).

## Workstreams

1. **Final mounted mutation inventory** — re-enumerate every mutation
   route in the live application from scratch (not a diff against prior
   slices' inventories) to catch anything the incremental process might
   have missed.
2. **Canonical zero-gap or exact-blocker proof** — either 100% of
   canonical rows are `VERIFIED`, or an exact, named list of the
   remaining unprotected rows and why (e.g. `PRODUCT_DECISION_REQUIRED`,
   `DEPRECATED`).
3. **Held-registry final reconciliation** — confirm zero
   `PENDING_MODULE_ADJUDICATION` rows remain.
4. **Security-observation final disposition** — every observation
   raised across 2F-32 through 2F-37 is closed or explicitly deferred
   with a named reason and owner slice/product-decision entry.
5. **Migration 144 readiness** — see
   [migration-144-readiness-contract.md](migration-144-readiness-contract.md).
   Apply ONLY if all 5 readiness conditions hold; otherwise report
   readiness status honestly without applying.
6. **Invalid-role account remediation** — audit every user account's
   `role` against the canonical 10-role list; remediate any alias/invalid
   role to its canonical equivalent, with full audit trail.
7. **`readonly@demo-ac-services.local` disposition** — see
   [readonly-account-remediation-contract.md](readonly-account-remediation-contract.md).
8. **Active-session handling** — any account whose role is remediated
   must have its existing sessions explicitly handled (revoked or
   re-validated), not silently left stale.
9. **Read-only mutation-enforcement proof** — application-wide sweep
   confirming every mutation-capable route rejects `TENANT_READONLY_
   ACCESS_SCOPES` (not just the routes closed across 2F-31A–2F-37).
10. **Final role constraint application** — only if #6 and #8 are both
    clean.
11. **Final canonical/matrix recount** — with hash evidence.
12. **Application-wide authorization certification** — must state
    exactly what was reviewed and what was not; must NOT claim
    100%-of-application security review if any route was out of this
    program's scope.
13. **Final deterministic regression** — full suite, twice.
14. **Final unresolved product-policy registry** — every
    `PRODUCT_DECISION_REQUIRED` item across the whole program (2F-32
    through 2F-37), carried forward, not dropped.

## Migration 144 gate (hard requirement, restated)

May be applied ONLY when:
- Zero invalid canonical roles remain.
- Existing invalid sessions are resolved.
- Read-only enforcement is proven application-wide.
- Rollback is tested.
- All seed/fixture data uses canonical roles.
- Full regression remains green.

## readonly@ gate (hard requirement, restated)

Must not be silently changed. Record: original role/status, active
sessions, chosen canonical remediation, authorization effect,
session-revocation effect, audit evidence, rollback evidence.

## Allowed final statuses

A 2F-38-specific status set (not reused from 2F-35/36/37) should be
defined by that slice's own mission — this contract does not prescribe
one string, since 2F-38's outcome space (certification, not module
closure) differs qualitatively; it must, at minimum, distinguish
"fully certified" from "certified with named exceptions" and must never
claim closure of anything not actually verified in that slice.

## Approval gate / stop condition

This is the terminal slice of the current authorization program. Stop
at its own approval gate. Do not select a new module — the mission ends
here unless a new phase is separately authorized.
