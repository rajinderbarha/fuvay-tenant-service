# FINAL-L5-02 — Router Mount Certification

## Method
Cross-referenced the 143 router files (`find app -name "*router*.py"`) against `include_router()` calls in `app/main.py` (75 direct calls, many mounting multiple routers via loops), and verified the resulting mounted route set via the live `app.openapi()` (2,253 endpoints). Builds on FINAL-L5-00's router inventory.

## Result

| Classification | Count | Notes |
|---|---|---|
| MOUNTED_ACTIVE | 137 | Confirmed mounted and serving endpoints in the live OpenAPI |
| DEFINED_NOT_MOUNTED (intentional) | 4 | `leads`, `loyalty`, `real_estate`, `promo` top-level routers — commented out in main.py under "Plugin Engines (disabled: only home_services vertical is active)" |
| DEFINED_NOT_MOUNTED (dead) | 2 | `app/engines/brands/admin_router.py`, `provider_router.py` — superseded by `admin_catalog/brand_router.py` (confirmed in FINAL-L5-00); still unmounted |
| DUPLICATE_PREFIX | 1 system (7 endpoints) | Service-setup templates double-mounted at `/v1/admin/service-setup-templates` AND `/v1/admin/service-setup/templates` — see endpoint registry |
| Misnamed (not actual routers) | 2 | Files with "router" in the name that are service classes, not `APIRouter` |

## Checks
- **Router defined but never included**: 6 total (4 intentional/disabled, 2 dead) — all accounted for, none is a frontend-required active router unintentionally left out.
- **Duplicate router registration**: 1 confirmed (service-setup templates) — real finding, flagged DUPLICATE.
- **Conflicting prefixes**: the service-setup double-mount is the only prefix collision found.
- **Router import failures**: none — the app boots cleanly and generates a valid 2,253-endpoint OpenAPI spec, which proves every mounted router imported successfully.
- **Router mounted without required authorization**: the FINAL-L5-01B RBAC fix closed the one known instance (17 admin-tenant GET routes); no new instance of an admin router with a bare `get_current_user` on privileged reads was found in this sprint's smoke, but a full 2,253-endpoint auth-dependency audit was not performed (see auth dependency review).

## Assessment
**No active, frontend-required router is unintentionally unmounted.** The 6 unmounted routers are either deliberately disabled (4) or confirmed-dead duplicates (2). The 1 duplicate mount (service-setup templates) is a real cleanup item, not a missing-mount failure. **Router mount certification: PASS** (with the duplicate-mount finding logged for cleanup).
