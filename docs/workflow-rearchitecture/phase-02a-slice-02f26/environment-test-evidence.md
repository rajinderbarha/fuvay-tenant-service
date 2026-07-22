# Environment and Test Evidence — Slice 2F-26

## Service availability

| Point in time | API :8000 | PostgreSQL :5432 | Redis :6379 |
|---|---|---|---|
| Slice start (2026-07-19T08:52:38) | REACHABLE | REACHABLE | REACHABLE |
| Before final runs | REACHABLE | REACHABLE | REACHABLE |
| After final runs | REACHABLE | REACHABLE | REACHABLE |

Stable throughout. Nothing resolved or broke environmentally during this
slice, so no test movement is attributable to infrastructure.

## A contaminated baseline — my error, reported rather than used

I launched the pre-slice baseline run **in the background** and then, while it
was still executing, ran `reconcile_2f26.py`, which rewrites the canonical
CSV. The run therefore read the canonical file in a **half-modified state**.

Result: that "baseline" reports **20 failed**, of which **13 are recount
assertions** reading the CSV I was concurrently editing:

```
test_phase2f14a ... test_canonical_totals
test_phase2f17a ... test_global_numerator_denominator_match_2f17_baseline
test_phase2f19  ... test_226_total_200_protected_26_unprotected
test_phase2f21  ... (3 assertions)
test_phase2f23  ... (2 assertions)
test_phase2f25  ... (3 assertions)
test_phase2f25a ... test_current_canonical_arithmetic_unchanged_by_this_slice
```

**That measurement is invalid and is not used as the comparison input.**

### The true pre-slice baseline
Slice 2F-25A run 2, measured under the same stable environment with no
concurrent modification:

**7 failed / 11460 passed / 22 skipped / 0 errors**

### Methodology lesson
A background full-suite run is only a valid baseline if shared state stays
frozen for its entire duration. Mutating a file the suite asserts on — even a
documentation CSV — invalidates it. Both post-slice runs in this slice were
executed only **after** all writes were complete.

## Which test groups used which service

| Group | PostgreSQL | Redis | API server | Mocked |
|---|---|---|---|---|
| `test_phase2f26_*` (this slice, 42) | no | patched | no | yes — CSV/AST/session doubles |
| recount suites (2f14a/17a/19/21/23/25/25a) | no | no | no | yes — CSV reads + runtime route walk |
| `test_module_l5_*`, `test_final_l5_*`, `test_p0_*` | **yes** | yes | mixed | no |
| `test_customer_idor.py`, `test_phase11.py` | some | some | TestClient | mixed |

## What remains unavailable

Nothing was skipped for want of infrastructure. The residual limitation is by
design: this slice's own 42 tests are deterministic (CSV assertions, AST
inspection, runtime route introspection, session doubles) rather than live
integration tests. That is appropriate for an inventory slice — there is no
authorization behaviour to exercise, because none changed.
