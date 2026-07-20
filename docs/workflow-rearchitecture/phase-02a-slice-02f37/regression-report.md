# Regression Report

## Summary

Full `tests/test_phase2f*.py` suite: **2445 passed, 0 failed, 0 errors**,
run twice for determinism (309.42s, 307.45s), identical results both
times. Baseline was 2418 passed at the end of Slice 2F-36; the +27 delta
is exactly the new `tests/test_phase2f37_financial_product_policy_batch.py`
file — no removed or renamed node IDs.

## Rebaseline detail

The live canonical CSV moved from 297/294/3 (total/protected/unprotected)
to 313/313/0 as a direct, intended consequence of this slice's closures
— canonical unprotected finally reaches **zero**, and pending held
candidates finally reach **zero**, matching the mission's stated
end-state exactly. 18 pre-existing historical test files across Slices
2F-14A through 2F-27A (including all 4 classifier-corpus files
2F-26E/F/G/H) assert these figures and classifier
tenant_direction/persona exception sets by reading the live canonical
CSV and live route/guard state (not a frozen snapshot), so each needed
its literals and exception sets updated in place, at their exact lines,
with attribution comments. No frozen point-in-time artifact, historical
CSV, or historical claim was rewritten — see `documentation-corrections.md`.
This is the same current-state-override pattern used by every prior
slice in this program.

## Classifier reclassification notes

Several routes' guard swaps (particularly `require_mutation_access_scope`
replacing bare `get_current_user` on `commerce.warranty/claims` and
`pricing.compute`) caused the live classifier to newly resolve
`PRINCIPAL_TENANT` where frozen pre-fix manual labels said
`CLIENT_ASSERTED_TARGET_TENANT` or `NO_TENANT_AUTHORITY_REQUIRED`. These
are forward-progress side effects of genuine application-code fixes, not
classifier tuning against any holdout corpus — each is documented with
an explicit exemption comment in the corresponding test file, following
this program's established `PROTECTED_BY_LATER_SLICE` discipline.

## M01 / geo / 2F-35 / 2F-36 non-regression

Confirmed unregressed by `TestM01GeoAnd2F35And2F36NonRegression` (4
tests) in the new targeted suite, and by re-running each of
`test_phase2f29_m01_identity_closure.py`,
`test_phase2f33_geo_zone_closure.py`,
`test_phase2f35_critical_authorization_batch.py`,
`test_phase2f36_enterprise_tenant_admin_operational_batch.py`
individually — all green.

## N01 non-regression

N01's own protected-route count (238/238) is unchanged — no file under
`app/engines/media/` was touched this slice, per the frozen contract.
See `n01-final-status.md`.

## Application files changed this slice

9 files: `app/engines/platform_commerce/{router,service}.py`,
`app/engines/pricing/{router,service}.py`,
`app/engines/payment/{router,service}.py`,
`app/engines/subscription/{router,service}.py`,
`app/engines/compliance/router.py`. No Slice 2F-35/2F-36/2F-38-exclusive
or N01 media file was touched.
