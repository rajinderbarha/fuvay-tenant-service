# Slice 2F-8 Implementation Summary

## Scope
Fully investigate, classify, protect, and verify every mounted mutation
endpoint owned by `app.engines.admin_catalog.tenant_router` — 10 mounted
mutations, confirmed via runtime introspection.

## What was found
- **9 of 10 tenant-facing mutations were already correctly protected**
  via `require_tenant_mutation_permission(P.TENANT_UPDATE)` before this
  slice began — re-verified, unmodified.
- **The 10th route** (`preview_tenant_price_options`, the one flagged as
  "remaining unprotected" by the global inventory) was investigated and
  confirmed to be a **synchronous, non-async pure computation with no
  `self.db` access at all** — a genuine `FALSE_POSITIVE`, not a real
  mutation. Reclassified accordingly rather than gated.
- **A genuine, directly-connected cross-tenant security bypass** was
  found in `TenantCatalogService._require_tenant_id`: `enable_service`/
  `disable_service` (and 3 GET routes sharing the same helper) accepted
  an optional `tenant_id` query parameter that was honored
  **unconditionally** — a `tenant_owner` (who legitimately holds
  `TENANT_UPDATE`) could supply a foreign tenant's ID and mutate (or
  read) that tenant's catalog. Fixed by requiring a non-platform actor's
  supplied `tenant_id` to match their own `actor_tenant_id`, mirroring
  the `FINAL-L5-05Q` pattern already used in `serviceability`'s admin
  router.

`TENANT_UPDATE` is granted **only to `tenant_owner`** in
`ROLE_PERMISSIONS` — staff/technician hold no `TENANT_UPDATE` grant at
all, so all 9 real mutations are `TENANT_OWNER_CATALOG_MAPPING`/
`TENANT_OWNER_SERVICE_ENABLEMENT`, not a delegated-staff capability. No
permission was granted this slice.

## What changed
1. **`app/engines/admin_catalog/tenant_service.py`** —
   `_require_tenant_id` fixed to reject a mismatched, client-supplied
   `tenant_id` for any non-platform actor.
2. **`scripts/workflow_rearchitecture/inventory_mutation_routes.py`** —
   `preview_tenant_price_options` added to
   `CONFIRMED_FALSE_POSITIVE_ROUTES`, bringing `--verify-module` to 0
   unverified (10/10).
3. **`frontend/tenant-portal/app/(tenant)/catalog/page.tsx`** — the
   Enable/Disable button had **no role gate at all** (rendered for any
   authenticated tenant user). Fixed by conditionally rendering it based
   on `isTenantOwnerRole(getUserRole()) && !isTenantReadOnly()`, reusing
   the same helpers from Slice 2F-7.
4. **Test suite**: new `tests/test_phase2f8_admin_catalog_tenant_authorization.py`
   (85 tests — persona enforcement, the cross-tenant `tenant_id`-override
   fix proven directly against the service class, cross-tenant
   `tenant_service_id` rejection via genuine mocked fixtures, existing
   guard regression checks, module-verification parity).
5. **Global coverage docs**: `mutation-enforcement-matrix.csv` and
   `tenant-mutation-endpoint-inventory.csv` updated in place.

## Workstream 7 resolution (tenant-catalog-enablement contract)
Resolved with an honest `PRODUCT_DECISION_REQUIRED` disposition, not a
serviceability code change: serviceability's `_assert_service_active`
only validates canonical `MasterService` activity, never
`TenantService.is_enabled`. Whether this is a proven, required business
rule was not established — and the matching engine's own join target
(`app.engines.service_catalog.ServiceCatalogItem`, a third, distinct,
apparently-legacy model) introduces a deeper, separate ambiguity that
would need its own investigation before any serviceability change could
be safely made. Per the interim policy ("only modify serviceability if
all conditions are proven"), **serviceability was left unchanged**.

## What did NOT change
No previously-closed module was modified. `serviceability.router`'s own
closure (Slice 2F-7) remains valid and untouched. Invoice/payment
closure (Slice 2F-6/2F-6A/2F-6B) was not reopened. The 3 sibling
`admin_catalog` provider/recommendation/option routers and
`complaints.provider_router` were not begun. No permission was granted.
No new role was introduced. `readonly@` and migration 144 were untouched.

## Outcome
`SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED` — see
`approval-gate.md`. Global tenant-mutation coverage: **97/183 → 97/182**
(denominator corrected for the confirmed false positive; no new route
protected, since all 9 real mutations were already guarded — but a real,
directly-connected cross-tenant bypass was closed within them).
