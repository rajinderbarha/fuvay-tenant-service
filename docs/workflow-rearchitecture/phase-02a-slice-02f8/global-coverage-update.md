# Global Coverage Update — Workstream 17

## Reconciliation method
Re-ran the runtime mutation inventory tool with no module filter, then
recomputed the tenant-facing (`TENANT_USER_MUTATION` +
`TENANT_TECHNICIAN_MUTATION`) denominator and the file's own
"fully_protected" convention.

## Corrected totals

| Metric | Previous (Slice 2F-7) | After this slice |
|---|---|---|
| Total tenant-facing mutations | 183 | **182** (−1) |
| Protected tenant-facing mutations | 97 | **97** (unchanged) |
| Remaining unprotected | 86 | **85** (−1, via denominator correction, not a new protection) |

## Why the denominator changed, not the protected count
`preview_tenant_price_options` was previously counted in the 183
denominator (auto-classified `TENANT_USER_MUTATION` due to its
`/v1/tenant/...` path prefix and POST verb) as one of the module's 10
mounted mutations, and listed `UNVERIFIED` (the "one remaining gap" this
slice's mission referenced). Direct source investigation this slice
confirmed it is a **synchronous, non-async computation with no
`self.db` access at all** — a genuine `FALSE_POSITIVE`, not a real
mutation. Per the same convention already used for
`provider_portal.preview_matching_inputs` (excluded in an earlier
slice), it is now excluded from the tenant-mutation denominator
entirely — it was never "protected" nor "unprotected" in a meaningful
sense, since no record is ever touched.

No new route was newly protected this slice: all 9 real
`admin_catalog.tenant_router` mutations were **already**
`require_tenant_mutation_permission`-guarded before this slice began
(re-verified, unmodified). This slice's actual security contribution was
a **directly-connected bypass fix within already-counted, already-
protected routes** (`TenantCatalogService._require_tenant_id`'s
cross-tenant query-param override) — a real, meaningful fix, but not one
that changes the guard *type* or therefore the protected *count*.

## Routes reclassified
`preview_tenant_price_options`: `UNVERIFIED` → `FALSE_POSITIVE`, added to
`CONFIRMED_FALSE_POSITIVE_ROUTES`.

## Remaining module count
16 tenant-facing modules remain with at least one unprotected mutation
(down from 17 before this slice) — `admin_catalog.tenant_router` is now
fully closed.

## Remaining unverified count
0 within `admin_catalog.tenant_router` (10/10 verified, exit 0).

## Files updated
- `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`:
  updated in place — `preview_tenant_price_options`'s row corrected to
  `FALSE_POSITIVE`.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`:
  updated in place — `admin_catalog.tenant_router`'s row and the running
  TOTAL row (183→182 denominator, 97/183 53.0% → 97/182 53.3%).
