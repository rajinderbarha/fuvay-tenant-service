# Slice 2F-32 — Post-N01 Queue Reconciliation and Next Authorization Module Selection

**Final status:** `NEXT_AUTHORIZATION_MODULE_SELECTED`

## What this slice did

Pure reconciliation/risk-assessment/scope-freeze — **no application file
was touched** (confirmed by mtime evidence, see
[behavioral-invariant-report.md](behavioral-invariant-report.md)).

1. **Reconciled the live 24-route canonical unprotected queue** directly
   from the canonical CSV (238/262 protected, 24 unprotected), with full
   per-route detail in
   [authoritative-unprotected-route-inventory.csv](authoritative-unprotected-route-inventory.csv).
   Proof: [post-n01-queue-reconciliation.md](post-n01-queue-reconciliation.md).
2. **Reconciled the 59-route held registry** from
   `docs/workflow-rearchitecture/phase-02a-slice-02f27a/
   unauthorized-candidate-hold-registry.csv` by exact route-key match
   against the canonical CSV: 3 N01 routes resolved
   (`RESOLVED_ADDED_CANONICALLY`), **56 pending** — matching the mission's
   expected value exactly. Proof:
   [held-candidate-arithmetic.md](held-candidate-arithmetic.md).
3. **Corrected the test count**: 2290 (baseline) − 1 (a genuine 3→2 test
   collapse inside Slice 2F-31A's own primary closure work, not the later
   rebaseline) + 30 (new WS10 tests) = **2319**, matching the live
   collected count exactly. Proof:
   [test-count-correction.md](test-count-correction.md).
4. **Recomputed 11 coherent implementation modules** for the 24 routes by
   shared router/service/permission/ownership boundary (not URL prefix
   alone), summing to exactly 24. See
   [implementation-module-boundaries.csv](implementation-module-boundaries.csv).
5. **Rescored risk from direct source evidence**, explicitly marking
   `UNKNOWN` where the underlying service was not read (never inferring
   ownership from route guards alone). Found that `geo_zone_management`'s
   single route has **zero tenant predicate anywhere** — the worst
   ownership gap of the 24, independently re-derived from source this
   slice. See [updated-risk-scoring-model.md](updated-risk-scoring-model.md).
6. **Selected exactly one module: `geo_zone_management`**
   (`DELETE /v1/geo/zones/{zone_id}`), compared against the next two
   highest-severity candidates (webhook, platform_commerce_deposit). See
   [module-selection-decision.md](module-selection-decision.md).
7. **Froze and hashed Set A/B/C** — see
   [selected-scope-hash-evidence.md](selected-scope-hash-evidence.md).
8. **Drafted (not executed) a complete future implementation contract** —
   see [selected-module-implementation-contract.md](selected-module-implementation-contract.md).
9. **Kept the N01 domain-integrity backlog separate** from this
   authorization queue, per WS7 — see
   [n01-domain-integrity-backlog.csv](n01-domain-integrity-backlog.csv).

## Coverage (unchanged by this slice)

- Protected: 238, Denominator: 262, Unprotected: 24
- Canonical hash: `1f7891798eb8382f` (unchanged)
- Matrix hash: `abac4ae72e8ab1d4` (unchanged)

## Regression

Full `tests/test_phase2f*.py` suite: see
[regression-comparison.csv](regression-comparison.csv) and
[test-report.md](test-report.md) — zero new failures, zero application
behavior change.

## Scope discipline

No authorization change implemented. No canonical row modified. No held
candidate added. The N01 `confirm_upload` integrity blocker was not
remediated. No application file was touched. Exactly one module selected.
Stopping at the Slice 2F-32 approval gate.
