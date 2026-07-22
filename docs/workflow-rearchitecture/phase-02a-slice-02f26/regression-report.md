# Regression Report — Slice 2F-26

## Baseline correction first

My pre-slice baseline run was **invalid** and is not used. I launched it in the
background and then ran the reconciler, which rewrites the canonical CSV, while
the suite was still executing. It read the file half-modified and reported 20
failures — 13 of them recount assertions on the CSV I was editing.

**The comparison input is Slice 2F-25A run 2**, measured under the same stable
environment with no concurrent modification:
**7 failed / 11460 passed / 22 skipped / 0 errors**.

Full account: `environment-test-evidence.md`.

## Double run

| | true baseline (2F-25A run 2) | run 1 | run 2 |
|---|---|---|---|
| passed | 11460 | **11503** | **11503** |
| failed | 7 | **7** | **7** |
| errors | 0 | **0** | **0** |
| skipped | 22 | **21** | **21** |
| duration | 639.80s | 585.72s | 565.16s |

`diff` of failing node IDs between run 1 and run 2: **identical**. Both runs
executed only after every write completed.

## Exact node-ID comparison

### Failures
```
comm -13 <baseline> <run1>  ->  (empty)   # NEW:      ZERO
comm -23 <baseline> <run1>  ->  (empty)   # RESOLVED: ZERO
```
7 unchanged, byte-identical.

### Errors
0 before, 0 after. Zero new, zero resolved.

## The +43 reconciles

- **+42** — the new suite `test_phase2f26_application_wide_inventory.py`.
- **+1** — `test_phase2f17a::test_every_canonical_row_is_mounted_at_runtime`.
  It was failing under the contaminated conditions because the mutation-only
  walker cannot see the two new mutating-GET rows; widening it to a
  GET-inclusive walk made it pass.

**−1 skipped**: the 2F-25A docs-guard test
(`test_docs_do_not_claim_application_wide_completeness`) skips only when its
slice docs directory is absent. It now runs and passes.

## Attribution

**Attributable to Slice 2F-26: 0 new failures, 0 new errors.**

No environment change occurred — all three services were reachable at slice
start, between runs, and after run 2 — so nothing is attributable to
infrastructure either.

## The 7 remaining failures — all pre-existing

| Node | Note |
|---|---|
| `test_phase2d_...::test_coverage_of_require_tenant_mutation_permission_is_still_narrow` | **Slice-2D canary — untouched.** This slice added no caller of that dependency, so its count is unchanged. |
| `test_final_l5_05t_...::test_pre_existing_allowlist_still_matches_reality_exactly` | pre-existing |
| `test_phase7_staff_app_certification.py::...` | pre-existing |
| `test_versions.py` × 4 | pre-existing SDK-version assertions |

## Behavioural invariants

Node-ID comparison alone is insufficient — 2F-25 proved it by shipping a
silently-swallowed regression with a clean diff. Six invariants assert
behaviour directly, including that the `field_ops` job-close review request is
still created. All pass: `behavioral-invariant-report.md`.
