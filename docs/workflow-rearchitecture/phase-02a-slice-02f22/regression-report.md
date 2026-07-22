# Regression Report — Slice 2F-22

## Methodology (per Workstream 24)

Regression safety is established by **exact failing-node-ID identity
comparison**, not by grepping failure output for module keywords. That
keyword method is what allowed Slice 2F-20 to ship a real regression while
reporting "zero regressions"; it is not used here.

Both runs are full-repository, same command, same environment:
`python -m pytest tests/ -q --tb=no -rf`.

## Headline numbers

| | BEFORE (post-2F-21) | AFTER (post-2F-22) | Δ |
|---|---|---|---|
| passed | 11057 | **11108** | +51 |
| failed | 87 | **86** | −1 |
| errors | 111 | **111** | 0 |
| skipped | 14 | **14** | 0 |
| duration | 623.39s | 652.97s | — |

## Exact node-ID comparison

**Newly failing node IDs: ZERO.**

```
comm -13 <before-failures> <after-failures>   ->   (empty)
```

**Resolved node IDs: exactly one** — the stale 2F-20 baseline assertion
fixed during 2F-21:

```
tests/test_phase2f19_remaining_queue_reconciliation.py::
  TestCanonicalBaseline::test_226_total_200_protected_26_unprotected
```

**Unchanged pre-existing failures: 86**, byte-identical node IDs in both runs.

## The +51 passed reconciles exactly

- 50 new tests in
  `tests/test_phase2f22_tenant_package_purchase_authorization.py`
- 1 previously-failing test now passing (the resolved node above)

50 + 1 = 51. No unexplained movement in either direction.

## Targeted comparisons

| Scope | Before | After | Verdict |
|---|---|---|---|
| Directly affected (7 files, 356 tests) | 0 failed | 0 failed | IDENTICAL |
| Wider package/credit/payment/registration/finance (14 files, 757 tests) | 5 failed | 5 failed | IDENTICAL node IDs |
| New 2F-22 suite | n/a | 50 passed | PASS |

The 5 wider failures were individually confirmed to be pre-existing by
diffing their node IDs against the baseline run, and one of them
(`test_module_l5_30_package_purchase.py::TestPackagePurchaseLive::test_purchase_then_duplicate_is_rejected`)
was executed in isolation to confirm the cause is
`httpx.ConnectError: All connection attempts failed` — a live-server
dependency, not a behavioural change. It was checked specifically because it
exercises the very route this slice modified.

## Failure classification

- **Attributable to Slice 2F-22: 0.**
- **Pre-existing, unrelated: 86 failures + 111 errors.** Dominated by
  live-environment dependencies (`httpx.ConnectError`,
  `ConnectionRefusedError: [WinError 1225]`) across `test_module_l5_*`,
  `test_final_l5_*`, `test_p0_*`, `test_trust_quality_phase1.py`.
- **Live-environment exclusions:** all DB- and HTTP-backed tests. No claim in
  this slice depends on one of them.
- **Slice-2D canaries (2):** still failing, deliberately **not** rewritten per
  this slice's explicit prohibition.

## Statement

Zero regressions — and unlike prior slices, that statement is supported by
exact before/after failure-identity comparison rather than inference.
