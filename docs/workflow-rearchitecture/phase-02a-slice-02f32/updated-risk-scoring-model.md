# Updated Risk Scoring Model (WS5)

## Methodology

Every score in [updated-module-risk-scoring.csv](updated-module-risk-scoring.csv)
is derived from one of two sources, and the CSV states which for every
ownership-relevant cell:

1. **Direct inspection this slice** — the router file AND the underlying
   service file were both read, and the actual query/predicate logic was
   traced. This was done for `geo_zone_management`,
   `webhook_endpoint_management`, `platform_commerce_deposit`, and
   `enterprise_grid_saved_views`.
2. **Not inspected this slice** — the route's guard chain is known from the
   canonical CSV, but the underlying service was not read. These cells are
   explicitly marked `UNKNOWN -- not inspected this slice`, never silently
   scored as low-risk. This applies to `enterprise_grid_preferences_exports`,
   `admin_catalog_provider_setup`, `profile_technician_self_service`,
   `marketing_automation_provider`, `analytics_provider_reports`, and
   `rag_query`.

Per the mission's explicit instruction, missing ownership is never inferred
from route guards alone — a route having `require_technician` says nothing
about whether the underlying service scopes the target object to the
caller's tenant. Where the service was not read, the ownership cell says so
rather than guessing.

## Headline finding

`geo_zone_management`'s single route, `DELETE /v1/geo/zones/{zone_id}`, is
the only one of the 24 routes where **no tenant predicate exists anywhere**
— not even a client-supplied one to distrust. `GeoService.delete_zone`
queries `WHERE ServiceZone.id == zone_id` with nothing else. This is a
strictly worse defect than `webhook_endpoint_management`'s, which at least
filters by a (client-supplied, unverified) `tenant_id`. Both were
independently re-derived from source this slice, not carried forward from
prior documentation's risk ranking.

## Second-tier finding

`platform_commerce_deposit`'s 3 routes carry the "financial authority" flag
but, on direct inspection, `CommerceService._assert_owns_tenant_deposit`
already blocks cross-tenant access before any deposit read/write proceeds.
The real gap there is narrower (missing access-scope awareness only) than
its financial-sensitivity label would suggest in isolation — a concrete
example of why ownership must be verified in the service, not assumed from
the "financial" capability label.

## Third-tier finding

`enterprise_grid_saved_views`'s `set_default_view` route has a **partial**
ownership gap: `SavedViewService.set_default` calls `get_view` (which
enforces visibility rules) but never re-compares `owner_user_id` before
flipping `is_default` — weaker than `update_view`/`delete_view`, which both
explicitly check `view.owner_user_id == user_id`. This asymmetry was found
by reading the actual service code, not inferred.
