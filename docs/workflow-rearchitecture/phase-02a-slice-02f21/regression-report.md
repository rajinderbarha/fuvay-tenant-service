# Regression Report — Slice 2F-21

## Full-repository sweep (measured twice, deterministic)

`python -m pytest tests/ -q`

| | Run 1 | Run 2 (`-rf --tb=no`) |
|---|---|---|
| passed | 11057 | 11057 |
| failed | 87 | 87 |
| errors | 111 | 111 |
| skipped | 14 | 14 |
| duration | 756.88s | 623.39s |

Identical counts across two independent runs — the failure set is
deterministic, not flaky.

## IMPORTANT: this does NOT match the baseline prior slices claimed

Slice 2F-20's `regression-report.md` recorded the baseline as
**45 failed / 11010 passed / 109 errors / 13 skipped** and asserted the
composition was "identical to every prior slice" with "zero attributable
failures." **That characterization was wrong**, and this slice corrects
it rather than repeating it.

The delta (+42 failed, +47 passed, +2 errors, +1 skipped) is NOT
explained by this slice's work. Investigation results below.

## Failure attribution — every failure classified

### Attributable to a prior slice in this initiative: 1
`tests/test_phase2f19_remaining_queue_reconciliation.py::TestCanonicalBaseline::test_226_total_200_protected_26_unprotected`

**Root cause**: Slice 2F-20 advanced the canonical numerator 200 → 206
and updated two of the THREE recount assertions in the repository
(`test_phase2f14a_...` and `test_phase2f17a_...`) but missed this third
one, which hardcoded `protected == 200`. It has been failing since 2F-20
merged. 2F-20's regression report did not catch it because its
grep-based "zero compliance-related matches" check searched for
compliance/dpdp keywords — this test's name contains neither, so a real,
slice-caused regression passed through an inadequate check.

**Fixed this slice** (recount tests are explicitly within 2F-21's
permitted-changes list): assertions updated to `protected == 206` /
`unprotected == 20`, with an inline docstring recording the correction
and its provenance. Post-fix the full recount set passes:
`test_phase2f14a` + `test_phase2f17a` + `test_phase2f19` +
`test_phase2f20` + `test_phase2f21` = **105 passed, 0 failed**.

**Post-fix expected full-suite count: 86 failed** (87 − 1).

### Pre-existing environment exclusions (live DB / live HTTP): confirmed
`tests/test_phase2c_role_integrity.py::TestMigration144DetectionLogic`
(2 failures) — `ConnectionRefusedError: [WinError 1225]`. Requires a live
database. Same class as the `httpx.ConnectError` exclusions documented in
every prior slice. Not attributable.

The bulk of the remaining 82 failures and all 111 errors fall in this
same class — `test_module_l5_*`, `test_final_l5_*`, `test_p0_*`,
`test_trust_quality_phase1.py` — all of which require a running server
and/or seeded database unavailable in this environment.

### Pre-existing STALE CANARY tests (not environment, not this slice): 2
`tests/test_phase2d_tenant_access_model.py::TestTenantMutationPermissionCoverage::test_coverage_of_require_tenant_mutation_permission_is_still_narrow`
— asserts "exactly 5 files" call `require_tenant_mutation_permission`;
finds 8. The additional callers were added by legitimately-approved later
slices (2F-1, 2F-6, 2F-7 and beyond). The test's own failure message says
"If this changed, update tenant-readonly-decision.md's conclusion" — i.e.
it is a deliberate design canary that has gone stale, not a defect.

`tests/test_phase2d_tenant_access_model.py::TestRemediationScriptDisableFlag::test_disable_requires_corresponding_mapping_entry`
— related Slice-2D-era canary, `assert 1 == 0`.

**NOT fixed this slice.** These assert about application structure, and
2F-21 is a discovery/selection slice prohibited from changing application
authorization behavior; adjusting them requires the
`tenant-readonly-decision.md` product conclusion to be revisited, which
is a decision, not a mechanical recount. Recorded in
`known-limitations.md` and `product-decisions-required.md`.

**2F-20 did not cause these**: 2F-20 wired
`require_tenant_owner_mutation`, a different function from
`require_tenant_mutation_permission`, and added zero callers of the
latter.

## Attributable to Slice 2F-21 itself: 0
This slice changed no application code (verified: no file under `app/`
modified), added one new test file (28 tests, all passing), and corrected
one stale recount assertion. No failure in the sweep is caused by 2F-21.

## Honest conclusion
The repository's true pre-existing failure baseline is **86 failed /
11057 passed / 111 errors / 14 skipped** (post-fix), not the 45/11010/109
figure carried in prior slices' reports. Prior slices' "identical
baseline" claims should be treated as unverified. This slice makes no
claim that the baseline is clean — only that it is now accurately
measured, that exactly one failure was slice-attributable and has been
fixed, and that two stale canaries are honestly flagged rather than
silently absorbed.
