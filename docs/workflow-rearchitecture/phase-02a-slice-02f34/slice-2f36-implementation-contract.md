# Slice 2F-36 Implementation Contract — Enterprise, Tenant-Administration and Operational Authorization

**Not executed in Slice 2F-34.** Frozen, ready-to-run brief. Executes
AFTER Slice 2F-35 completes (sequential, not parallel — see
[cross-slice-file-conflict-audit.csv](cross-slice-file-conflict-audit.csv)).

## Mission

Close all 7 modules (18 canonical routes) listed in
[slice-2f36-scope-summary.md](slice-2f36-scope-summary.md) with **strict
per-module isolation** — separate Set A/B/C, separate authority contract,
separate tests, separate coverage arithmetic, separate final status per
module. Adjudicate all 28 frozen held candidates.

## Starting arithmetic

Load live from Slice 2F-35's final `approval-gate.md` — do not assume
241/264/23/54. If Slice 2F-35 has not run or its output doesn't
reconcile, stop with `AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`.

## Exact modules and route files

- Set A: [slice-2f36-module-scope.csv](slice-2f36-module-scope.csv) (hash `0994c5373c08a2b6`)
- Set B: [slice-2f36-held-scope.csv](slice-2f36-held-scope.csv) (hash `9fe3fe305b53d174`)
- Set C: [slice-2f36-exclusion-scope.csv](slice-2f36-exclusion-scope.csv) (hash `6adb8d71a4c7e2b6`)

## Allowed application files (per module — confirm exact paths, do not assume)

- `enterprise_grid_saved_views` + `enterprise_grid_preferences_exports`:
  `app/engines/enterprise_grid/router.py`, `app/engines/enterprise_grid/
  services.py` (both modules share these files — touch each module's own
  functions only, do not conflate their fixes)
- `admin_catalog_provider_setup`: `app/engines/admin_catalog/
  brand_provider_router.py`, `recommendation_router.py`,
  `service_option_provider_router.py`, `brand_service.py`,
  `recommendation_engine_service.py`, and whatever file implements
  `ServiceOptionService` (discover, do not assume)
- `profile_technician_self_service` + `profile_universal_self_service`:
  `app/engines/profile/router.py`, `app/engines/profile/service.py`
- `marketing_automation_provider`: `app/engines/marketing_automation/
  provider_router.py`
- `analytics_provider_reports`: `app/engines/analytics/provider_router.py`
- Router/service files for the 28 held routes — discover per module.
- `app/core/permissions.py` — only if no existing guard fits.

## Forbidden files

Anything backing a Set C route or assigned to 2F-35/2F-37/2F-38.
`app/engines/geo/*`, `app/engines/media/*`, `app/engines/webhook/*`,
`app/engines/rag/*` (2F-35's scope — do not touch even if 2F-35 already
closed it).

## Workstreams

1. Reconfirm A/B/C hashes against the LIVE post-2F-35 canonical/matrix.
2. Per-module authority contract (7 separate contracts).
3. Adjudicate each of the 28 held routes individually from direct source
   evidence, grouped by their 10 held-registry modules — do not bulk-
   adjudicate by module label alone.
4. For `enterprise_grid_saved_views.set_default`: add an explicit
   `owner_user_id` re-check before mutating `is_default` (the confirmed
   partial-ownership gap), not merely a guard swap.
5. For the 6 confirmed-access-scope-gap-only modules
   (`admin_catalog_provider_setup`, `profile_*`, `marketing_automation_
   provider`, `analytics_provider_reports`): swap to `require_tenant_
   mutation_permission`/`require_mutation_access_scope` per each route's
   existing role shape — do not narrow admitted roles.
6. Full test matrix per module with negative controls.
7. A dedicated verifier script (`verify_2f36.py`) with `--selftest`
   covering all 7 modules and 28 held adjudications independently.

## Canonical/held update rules

Update only Set A rows after complete evidence; add only
`TENANT_PROVIDER_MUTATION_ADD`-adjudicated Set B routes, each exactly
once, keeping each module's rows traceable to its own module in the
canonical CSV's provenance column.

## Coverage arithmetic rules

Computed per-module and summed; report both. Do not force a single
combined number without the per-module breakdown.

## Regression requirements

Full suite, twice, deterministic, zero new failures, M01/N01/geo/2F-35
non-regression canaries re-run.

## Allowed final statuses

Same 6-status list as 2F-35, applied **independently per module** (a
batch may report mixed statuses).

## Approval gate / stop condition

Stop at Slice 2F-36's own approval gate. Do not select a further module.
Do not begin Slice 2F-37 in the same run.
