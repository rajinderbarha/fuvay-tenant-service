# Canonical Coverage Update

## Starting approved baseline
200 protected / 226 total.

## Row-level reconciliation of the 6 selected routes
| endpoint_name | previous guard_status | new guard_status |
|---|---|---|
| withdraw_consent | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| customer_tenant_response | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| create_my_request | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| cancel_my_request | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| generate_export | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| staff_tenant_response | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | TENANT_MUTATION_ROLE_SCOPE_AWARE |

## Final tenant numerator/denominator
**Denominator unchanged: 226.** All 6 rows were already correctly counted
as tenant/provider mutations — no reclassification.

**Numerator: 200 → 206 (+6).**

## Fully protected vs. blocked
All 6 routes are `FULLY_PROTECTED` on the AUTHORIZATION dimension
(persona, mutation-scope, tenant ownership, subject ownership — the
dimensions the canonical CSV's `guard_status` column tracks). `generate_export`
specifically carries a documented, SEPARATE domain-integrity gap
(no worker exists to complete what it queues, per
`compliance-export-worker-discovery.md`) that does NOT block its
`guard_status` classification — the canonical CSV's convention (unchanged
since Design A, 2F-15C) measures router-level authorization, not
end-to-end feature completeness; this is consistent with how prior
slices (e.g. `platform_notifications`) have handled similar
partial-domain-integrity findings without blocking coverage credit.

## Customer/platform/internal compliance mutations — unaffected
`customer_router.py`'s and `admin_router.py`'s compliance mutations remain
correctly OUTSIDE this tenant-only canonical CSV (Design A convention,
unchanged) — this slice did not touch either router's route count.

## Both canonical CSVs recount identically
`tenant-mutation-endpoint-inventory.csv`: 226 rows, 206 protected (updated
this slice). `mutation-enforcement-matrix.csv`: the
`app.engines.compliance.provider_router` row updated from `0/6 protected
(0%)` to `6/6 protected (100%)`.

## Remaining module count
9 non-selected modules, 20 routes remain — unchanged from 2F-19's queue.
