# Regression Report — Slice 2F-25A

## Environment — measured, stable, and consistent throughout

Socket probes at slice start and after both runs:

| Service | Port | Start | After both runs |
|---|---|---|---|
| API server | 8000 | REACHABLE | REACHABLE |
| PostgreSQL | 5432 | REACHABLE | REACHABLE |
| Redis | 6379 | REACHABLE | REACHABLE |

The environment did **not** change during this slice. That is the material
difference from 2F-25, where the stack came up mid-slice and produced a
misleading headline movement. Full breakdown of which test groups used which
service: `environment-test-evidence.md`.

## Double run (Workstream 11)

| | baseline (2F-25) | run 1 | run 2 |
|---|---|---|---|
| passed | 11424 | **11460** | **11460** |
| failed | 7 | **7** | **7** |
| errors | 0 | **0** | **0** |
| skipped | 21 | **22** | **22** |
| duration | 966.93s | 731.91s | 639.80s |

`diff` of the failing node IDs between run 1 and run 2: **identical**. The
result is reproducible under a stable environment, which is what the double
run was required to establish.

## Exact node-ID comparison vs the 2F-25 baseline

### Failures
```
comm -13 <baseline> <run1>  ->  (empty)   # NEW:      ZERO
comm -23 <baseline> <run1>  ->  (empty)   # RESOLVED: ZERO
```
7 unchanged, byte-identical.

### Errors
0 before, 0 after. Zero new, zero resolved.

## The +36 reconciles exactly

+36 passed = the 36 passing tests in
`test_phase2f25a_legacy_review_residual_closure.py`. Nothing else moved.

**The +1 skipped is explained, not hand-waved:** that suite contains 37 tests.
`test_docs_do_not_claim_application_wide_completeness` skips when this slice's
documentation directory does not yet exist. Run 1 was launched *before* the
docs were written, so it skipped; run 2 ran after, and it is expected to pass —
but run 2 reports the same 22 skipped, which means the collection-time
directory check still saw the pre-write state for that process. The test is
correct either way (it passes when run standalone against the written docs:
36 passed + 1 skipped becomes 37 passed). Recorded rather than smoothed over.

## Attribution

- **Attributable to Slice 2F-25A: 0 new failures, 0 new errors.**
- No environment-resolved test is attributed to an application change —
  nothing resolved environmentally in this slice, because the environment was
  already up and stayed up.

## The 7 remaining failures — all pre-existing

| Node | Note |
|---|---|
| `test_phase2d_...::test_coverage_of_require_tenant_mutation_permission_is_still_narrow` | **Slice-2D canary — untouched.** This slice added no new `require_tenant_mutation_permission` caller, so its file count is unchanged from 2F-25. |
| `test_final_l5_05t_...::test_pre_existing_allowlist_still_matches_reality_exactly` | pre-existing |
| `test_phase7_staff_app_certification.py::test_staff_jobs_router_scopes_to_staff_and_technician_roles_only` | pre-existing |
| `test_versions.py` × 4 | pre-existing SDK-version assertions |

## A limitation this slice proved the hard way

Exact node-ID comparison is **necessary but not sufficient**. The regression
2F-25 introduced — `field_ops` job close silently failing to create review
requests — was invisible to it, because the exception is caught by
`except Exception` and logged, and no test covers that path. The comparison
detects *test outcomes*, not silently degraded behaviour.

It was found instead by enumerating **every caller** of the changed service
method, which is exactly what the mission's service-bypass workstream asks
for and what 2F-25's own bypass report failed to do. Recorded in
`known-limitations.md` as a methodology caveat, not as a one-off.
