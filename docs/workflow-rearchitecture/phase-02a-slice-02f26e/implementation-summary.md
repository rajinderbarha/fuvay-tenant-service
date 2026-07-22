# Implementation Summary — Slice 2F-26E

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage **214 / 257**, 43 unprotected. Canonical hash `45244cd9540456db`
before and after. Zero canonical edits, zero application files modified.

## 1. Unified resolved-authority model (WS1)

`scripts/workflow_rearchitecture/authority_model_2f26e.py` — one `resolve()`
record consumed by persona assignment, tenant-direction inference, capability,
side-effect and protection classification and the verifier. 2F-26D failed
because role resolution and `tenant_authority()` were separate models that
could disagree; they are the same record now.

Each record carries: resolved guard callable, guard family, static roles,
runtime-extensibility, permission string and whether it is in
`ROLE_PERMISSIONS`, tenant requirement, access-scope requirement, capability,
tenant direction with evidence, persona, abstention reason, side effect and
resolution status.

## 2. Runtime-extensible persona assignment (WS2) — D-01 repaired

`require_permission(P.X)` calls
`permission_checker.has(..., overrides=user.permission_overrides)`. A
permission absent from `ROLE_PERMISSIONS` is therefore **not**
super-admin-only. Admission is modelled as one of five `ADMISSION` values.

The two routes 2F-26D caught now classify correctly:

| Route | 2F-26D | 2F-26E |
|---|---|---|
| `POST /v1/tenants/{tenant_id}/plan/upgrade` | PLATFORM_ADMIN_MUTATION | **TENANT_PROVIDER_MUTATION** |
| `POST /v1/tenants/{tenant_id}/terminate/confirm` | PLATFORM_ADMIN_MUTATION | **TENANT_PROVIDER_MUTATION** |

The repair is bounded, not a blanket inversion: a permission that *is* in the
map with platform-admin roles still yields `PLATFORM_ADMIN_MUTATION`
(`deposit/admin-adjust`), asserted by its own test. Deny precedence,
cross-tenant grant isolation and unknown-role fail-closed are all re-asserted.

## 3. Shared taxonomy (WS3) — D-03 repaired

12 values, defined once, with comparison rules and canonical-inclusion
implications. `NO_TENANT_SCOPE` retired and asserted absent — it conflated
self-scoped routes with tenant-owned objects addressed by id, and the
classifier could never emit it, so every row carrying it was guaranteed to
disagree.

## 4. Tenant-authority consistency (WS4) — D-02 repaired

Direction is derived from the same resolved guard record as persona. The
decisive signal the old model discarded: guards in the `*_mutation` family run
the tenant read-only access_scope gate, which only makes sense for a
tenant-side principal — such a guard establishes `PRINCIPAL_TENANT` by
construction.

The mark-all-read control now asserts **both** persona and direction. 2F-26D's
control asserted persona only, which is precisely why D-02 survived it.

## 5. Abstention policy (WS5) — D-04 repaired

All 8 burned-sample abstentions traced to **avoidable** causes — the resolver
failing to use information it already had. All 8 eliminated. Remaining
abstentions emit a reason code from a closed 5-value set and block canonical
automation for that route.

## 6. Burned-sample regression (WS6) — development evidence only

| Field | Result | 2F-26D |
|---|---|---|
| Persona | **24/24** | 14/24 |
| Direction | **24/24** | 6/24 |
| Abstentions | **0/24** | 8/24 |

**This proves nothing about correctness** — the classifier was tuned against
this set, which is what a burned sample is for. Three real bugs were found
and fixed this way (platform-admin over-correction, self-scope overriding a
client-asserted tenant, and an over-broad `.tenant_id` match that read
object-derived tenants as client-asserted).

## 7. Verifier negative fixtures (WS7)

`verify_foundation_2f26e.py` — 19 blocking conditions, each with an executed
fixture that forces failure, produces a non-zero exit, names the exact
condition, and restores the clean state. `--selftest` exits 0; `main()` exits
1 on N09 alone.

## 8-10. Fresh holdout — 19/24, gate fails

24 routes from the 99 remaining (all 24 burned routes excluded, asserted by
N19 and by test). Manifest frozen `aeeb3fe510bf9671` before any verdict;
manual frozen `b02f35736a79eb3d` before the classifier ran.

| Field | Agreement |
|---|---|
| Capability | 21/24 |
| Side effect | 23/24 |
| Persona | 23/24 |
| Direction | 22/24 |
| **All four** | **19/24** (required 24/24) |

Two **new** classifier defects found: an alias-blind parameter scan
(`Query(..., alias="tenant_id")`) and actor identity read as scope. Neither
fixed — fixing a defect found by the holdout that measures the classifier and
re-running that holdout is circular.

One disagreement was **my** error with the tool correct: `GET
/v1/ds/tenants/{tenant_id}/demand/forecast` genuinely persists a
`DemandForecast` row. Two more are capability-column granularity errors
substantially mine.

## 11-12. Proposed routes and edit gate

Both reconfirmed as genuine tenant mutations under
`require_permission(P.TENANT_UPDATE)`; both recorded with `applied=NO`,
blocked by N09. Neither canonical CSV changed.

## Verification

- `tests/test_phase2f26e_classifier_repair.py` — **38 passed**
- All phase-2F suites (17A, 26, 26B, 26C, 26D, 26E) — **161 passed, 0 failed**
- Verifier `--selftest` — exit 0, 19/19 fixtures fire, clean state restores
- Verifier `main()` — exit 1 on N09 only
- Environment: api:8000, postgres:5432, redis:6379 REACHABLE throughout
- Zero `app/` files modified

## Known limitations

- **Only 5 of 24 required strata exist** in the remaining population; the
  holdout is stratified over what exists.
- **Both holdouts are now burned.**
- Burned-sample 24/24 is not independent evidence.
- Security observations are static-reading only; none executed.
