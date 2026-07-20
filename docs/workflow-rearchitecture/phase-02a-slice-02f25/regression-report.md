# Regression Report — Slice 2F-25

## READ THIS FIRST: the environment changed during this slice

The API server (`:8000`), PostgreSQL (`:5432`) and Redis (`:6379`) became
**reachable** during this slice. They were unreachable for every prior slice
in this initiative — which is what produced the long-standing
"live-environment exclusion" caveat.

**Slice 2F-25 did not fix 79 failures and 111 errors. The stack came up.**
Verified directly by socket probe, not inferred. Reporting those as this
slice's achievement would be the single most misleading claim available in
this dataset, so it is stated first.

## Headline numbers

| | BEFORE (2F-24) | AFTER (2F-25) | Δ |
|---|---|---|---|
| passed | 11192 | **11424** | +232 |
| failed | 86 | **7** | −79 |
| errors | 111 | **0** | −111 |
| skipped | 14 | **21** | +7 |
| duration | 686.56s | 966.93s | +280s |

## Exact node-ID comparison

### Failures
```
comm -13 <before> <after>  ->  (empty)   # NEW failing:  ZERO
comm -23 <before> <after>  ->  79 nodes  # resolved
```
**Zero new failing node IDs.** The 7 remaining are a strict subset of the
prior 86.

### Errors
```
new error node IDs:      ZERO
resolved error node IDs: 111  (all of them)
```

## Attribution — every number accounted for

| Movement | Cause |
|---|---|
| +49 passed | this slice's new tests |
| +183 passed | previously failing/erroring tests that now execute against the live stack |
| −79 failed | environmental (`httpx.ConnectError` / `ConnectionRefusedError` gone) |
| −111 errors | environmental (DB fixture setup now succeeds) |
| +7 skipped | tests that skip when a real database is present |

Arithmetic: 79 + 111 = 190 tests changed state; 190 − 7 newly skipped = 183
now passing; 183 + 49 new = **232 = 11424 − 11192**. Reconciles exactly.

**Attributable to Slice 2F-25: 0 new failures, 0 new errors.**

## The 7 remaining failures — all pre-existing

| Node | Note |
|---|---|
| `test_phase2d_...::test_coverage_of_require_tenant_mutation_permission_is_still_narrow` | **Slice-2D canary — untouched.** Its file count moved 8 → 9 because this slice adopted the existing scope-aware dependency. It was already failing and still fails with the same node ID: no state change, not rewritten. |
| `test_final_l5_05t_...::test_pre_existing_allowlist_still_matches_reality_exactly` | pre-existing |
| `test_phase7_staff_app_certification.py::test_staff_jobs_router_scopes_to_staff_and_technician_roles_only` | pre-existing |
| `test_versions.py` × 4 | pre-existing SDK-version assertions |

Note the **second** Slice-2D canary
(`test_disable_requires_corresponding_mapping_entry`) now **passes** — it
required a database. That resolution is environmental, not a rewrite.

## What this materially improves

Every prior slice in this initiative — including this one's own
implementation work — proved its security claims by source inspection and
session doubles, with live verification recorded as an environment exclusion.
That exclusion has now partially lifted, and the live suite exercised the
changed code paths:

- `test_module_l5_13_reviews.py::TestBookingRatingEndToEnd` — **erroring for
  the entire initiative**, now runs end-to-end against the live database and
  **passes**.
- Review-related suites re-run against the live stack: **142 passed, 1
  skipped, 0 failed**.

So the review-engine changes are now backed by live execution as well as
static assertion. That is a genuine strengthening — but it is a consequence of
the environment, and the credit belongs there.

## Caveat for the next slice

The baseline has shifted permanently (assuming the stack stays up). The next
slice's comparison input is **11424 passed / 7 failed / 0 errors / 21
skipped**, not the old figures. If the stack goes down again the old
failure/error population will return; that would be environmental too and
must not be read as a regression.
