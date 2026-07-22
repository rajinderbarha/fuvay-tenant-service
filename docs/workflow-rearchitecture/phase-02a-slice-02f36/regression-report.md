# Regression Report

## Summary

Full `tests/test_phase2f*.py` suite: **2418 passed, 0 failed, 0 errors**,
run twice for determinism (408.68s, 371.13s), identical results both
times. Baseline was 2378 passed at the end of Slice 2F-35; the +40 delta
is exactly the new `tests/test_phase2f36_enterprise_tenant_admin_operational_batch.py`
file — no removed or renamed node IDs.

## Rebaseline detail

The live canonical CSV moved from 273/252/21 (total/protected/unprotected)
to 297/294/3 as a direct, intended consequence of this slice's closures.
16 pre-existing historical test files across Slices 2F-14A through 2F-35
assert these figures by reading the live canonical CSV file (not a frozen
snapshot), so each needed its literal (and, for the classifier-corpus
files 2F-26E/F/G/H, its `tenant_direction`/persona exception set) updated
in place, at its exact assertion line, with a one-line attribution
comment. No frozen point-in-time artifact, historical CSV, or historical
claim was rewritten — see `documentation-corrections.md` for the full
list. This is the same current-state-override pattern used by every
prior slice in this program (e.g. the `PROTECTED_BY_LATER_SLICE` set
idiom, extended this slice for the appointments calendar-block routes
and the inventory reservation-confirm route).

## M01 / N01 / geo / 2F-35 non-regression

Confirmed unregressed by `TestM01N01GeoAnd2F35NonRegression` (4 tests) in
the new targeted suite, and by re-running each of `test_phase2f29_m01_identity_
closure.py`, `test_phase2f31_n01_media_closure.py`,
`test_phase2f31a_n01_residual_closure.py`, `test_phase2f33_geo_zone_closure.py`,
`test_phase2f35_critical_authorization_batch.py` individually — all
green.

## Application files changed this slice

15 files: `app/engines/enterprise_grid/{router,services}.py`,
`app/engines/admin_catalog/{service_option_provider_router,
brand_provider_router,recommendation_router}.py`,
`app/engines/profile/router.py`,
`app/engines/marketing_automation/provider_router.py`,
`app/engines/analytics/provider_router.py`,
`app/engines/chat/{router,service}.py`,
`app/engines/inventory/{router,service}.py`,
`app/engines/appointment/{router,service}.py`,
`app/engines/service_catalog/{router,service}.py`,
`app/engines/dispatch/{router,service}.py`,
`app/engines/data_science/{router,service}.py`,
`app/engines/settings_engine/{router,service}.py`,
`app/engines/notification/{router,service}.py`. No Slice
2F-35/2F-37/2F-38-exclusive file was touched.
