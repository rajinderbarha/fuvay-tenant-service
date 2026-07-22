# Canonical Coverage Update — Slice 2F-22

## Starting approved baseline
**206 protected / 226 total**, 20 unprotected across 9 modules.

## Row-level reconciliation — the single selected route

| Field | Before | After |
|---|---|---|
| endpoint | `tenant_purchase_package` | unchanged |
| `dependency_names` | `...\|require_tenant_owner\|...` | `...\|require_tenant_owner_mutation\|...` |
| `guard_status` | `ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE` | `TENANT_MUTATION_ROLE_SCOPE_AWARE` |
| `required_action` | add access-scope-aware guard | `NONE — protected in Slice 2F-22` |
| verification | RUNTIME_VERIFIED (route/dependency only) | RUNTIME_VERIFIED + full domain/ownership/payment-authority review |

The route qualifies for `FULLY_PROTECTED` treatment because **every**
applicable control is closed: persona, mutation scope, tenant authority,
package eligibility, price authority, payment-state authority,
credit/entitlement integrity, duplicate safety, alternate-route closure, and
no-partial-persistence. See `approval-gate.md` for the per-criterion
determination.

## Arithmetic

- Numerator: 206 + 1 = **207**
- Denominator: 226 + 0 − 0 − 0 − 0 − 0 = **226**
- Unprotected: 226 − 207 = **19**
- Remaining modules: 9 − 1 = **8**

Counted live from the CSV, not asserted: `total: 226 protected: 207`.

## Every recount assertion updated

Workstream 23 required searching the **entire repository** for numeric
baseline assertions before declaring coverage complete — the exact step
Slice 2F-20 skipped, which left a stale assertion failing for a whole slice.
All were located by grep and updated:

| File | Change |
|---|---|
| `test_phase2f14a_field_ops_alternate_route_and_coverage.py` | `protected == 206` → `207` |
| `test_phase2f17a_global_mutation_inventory.py` | `protected == 206` → `207` |
| `test_phase2f19_remaining_queue_reconciliation.py` | `protected == 206` → `207`; `total - protected == 20` → `19` |
| `test_phase2f21_...selection.py` (3 sites) | live-canonical reads → `207` / unprotected `19`, each annotated |

**Deliberately NOT changed** — assertions that read Slice 2F-21's *own* slice
CSVs (module grouping sums to 20, non-selected + selected = 20, 20-row diff).
Those are a truthful point-in-time record of what was unprotected at 2F-21;
rewriting them would falsify that slice's finding. The distinction is
annotated in the test file itself.

Likewise `phase-02a-slice-02f21/runtime-reverification.csv` was left intact,
with the now-protected route handled by a narrow, named exemption in
`TestRuntimeReverification.PROTECTED_BY_LATER_SLICE` that still fails on
genuine drift in the other 19 rows.

## Second canonical CSV

`mutation-enforcement-matrix.csv` remains a legacy per-domain summary whose
TOTAL row is a stale pre-2F-17A figure. Consistent with the convention
already applied in 2F-19, 2F-20 and 2F-21, it is not the authoritative
denominator and was not forced to match.
`tenant-mutation-endpoint-inventory.csv` is the single source of truth and
recounts exactly.

## Non-tenant package routes remain outside X/Y

`admin_router` (platform admin) and `public_router` package routes stay
outside the tenant-only canonical CSV per the Design A convention, unchanged.
