# Matching and Booking Impact — Workstream 8

## Consumers traced
`ServiceabilityService.match_tenants_for_location` (the core matching
engine, called by `check_serviceability`, `matching_tenants`,
`available_services`, and `admin_serviceability_test`) — the single,
canonical matching path for this module. `run_booking_preflight` (also
in this service file, though the router-level preflight endpoint itself
now lives in `app.engines.booking.router` per the router's own comment
— confirmed unmodified this slice, out of scope: "do not modify booking
creation").

## Verified requirements

| Requirement | Status | Evidence |
|---|---|---|
| Disabled coverage removes matching eligibility | YES | `match_tenants_for_location`'s base SQL `WHERE` clause includes `TenantServiceArea.is_active.is_(True)` AND `TenantServiceAreaService.is_available.is_(True)` — filtered at the database query level, not post-hoc in application code |
| Deleted coverage does not remain active through stale records | YES | Both `deactivate_service_area` and `delete_service_mapping` flip the same boolean flags the matching query filters on — there is no separate "cache" or "index" table that could go stale relative to these flags |
| Matching does not silently bypass tenant coverage | YES | Every row in the matching query result is joined through `TenantServiceArea` and `TenantServiceAreaService` — there is no code path that returns a tenant without a matching, active coverage+mapping pair |
| Booking preflight uses the canonical serviceability path | Not re-verified in depth this slice (booking.router is explicitly out of scope — "do not modify booking creation"); the router's own comment confirms `run_booking_preflight` was relocated to `BookingService`, and this module's `service.py` still contains the underlying `run_booking_preflight` method used by it |
| A fallback path does not return tenants outside configured areas | No fallback path was found — the query has one unconditional `WHERE` clause; there is no "if no matches, expand search" logic that could leak out-of-area tenants |
| Cache or index refresh behavior is documented | No cache/index exists for this matching path — it queries `TenantServiceArea`/`TenantServiceAreaService` directly on every call, so there is no staleness window to document |
| Publication requirements are explicit | N/A — there is no draft/published state concept for `TenantServiceArea`/`TenantServiceAreaService` (only `is_active`/`is_available`) |

## Zone-based matching
For `coverage_type == "zone"` areas, the matching engine batch-loads
`ServiceZone` rows filtered on `ServiceZone.is_active.is_(True)` as well
— confirming the platform-level zone's own active state is also
respected (a tenant's zone-based coverage silently stops matching if the
platform deactivates the referenced `ServiceZone`, which is the correct,
conservative behavior).

## Conclusion
No matching bypass was found — disabled/removed tenant coverage is
excluded from the canonical matching query at the SQL level, and no
stale-cache or fallback-expansion path exists that could circumvent it.
Per the mission's requirement, since no bypass was proven, nothing
required fixing here, and matching itself was not redesigned.
