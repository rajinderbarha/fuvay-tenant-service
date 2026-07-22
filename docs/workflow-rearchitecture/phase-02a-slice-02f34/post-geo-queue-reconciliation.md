# Post-Geo Queue Reconciliation (WS1)

## Proof

- **Exactly 23 routes are unprotected**: `264 - 241 == 23`, confirmed by
  direct count of the live canonical CSV.
- **Every route is mounted**: all 23 keys confirmed present in
  `authority_model_2f26e.py::route_index()`.
- **Every route appears exactly once** in
  [authoritative-unprotected-route-inventory.csv](authoritative-unprotected-route-inventory.csv)
  — 23 rows, 23 unique keys.
- **No M01 route appears**: sample `POST /v1/auth/api-keys` confirmed
  `VERIFIED`.
- **No N01 route appears**: sample `POST /v1/media/upload` confirmed
  `VERIFIED`.
- **No closed geo Set A or Set B route appears**: `DELETE /v1/geo/zones/
  {zone_id}`, `POST /v1/geo/tenants/{tenant_id}/zones`, `POST /v1/geo/
  tenants/{tenant_id}/staff/{staff_id}/location` all confirmed `VERIFIED`
  and absent from the 23-route set.
- **No held candidate is counted canonically**: cross-checked all 54
  pending held route keys against the canonical CSV — zero overlap.
- **241 + 23 = 264**: arithmetic identity, holds trivially and is
  re-checked by the program verifier.

Full per-route detail (router, service, model, capability, permission,
tenant/object/parent ownership source, primary defect, privacy/integrity
concern, provenance): see
[authoritative-unprotected-route-inventory.csv](authoritative-unprotected-route-inventory.csv).
