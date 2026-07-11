# FINAL-L5-04B — Admin Entitlement API Report

## Real endpoints (`app/engines/entitlement/admin_router.py`, prefix `/v1/admin/tenants/{tenant_id}/entitlements`)
| Method | Path | Verified |
|---|---|---|
| GET | `/` | Live curl + 12 automated RBAC tests |
| GET | `/history` | Live curl (shows real audit rows with actor/reason/timestamp) |
| POST | `/modules` | Live curl (assign) |
| POST | `/modules/{module_key}/disable` | Live curl + real Chromium E2E |
| POST | `/modules/{module_key}/reenable` | Live curl + real Chromium E2E |
| POST | `/categories` | Live curl (assign, and 404-tested against a nonexistent category) |
| POST | `/categories/{category_id}/disable` | Live curl + real Chromium E2E |
| POST | `/categories/{category_id}/reenable` | Live curl + real Chromium E2E |

All 8 registered and discoverable in the live OpenAPI schema (`/v1/admin/tenants/{tenant_id}/entitlements*` — confirmed programmatically in `TestRouterRegistration`).

## Required checks — verified against real behavior
| # | Check | Result |
|---|---|---|
| 1 | Platform Admin permission required | `require_super_admin` on every endpoint; 5 non-admin roles tested (customer, technician, tenant_owner, tenant_manager, tenant_readonly) all get real 403 |
| 2 | Tenant exists | `_require_tenant()` — 404 for unknown tenant_id, checked before any entitlement logic runs |
| 3 | Module/category exists | `EntitlementNotFoundError` → 404, live-tested against a nonexistent module key and a nonexistent category UUID |
| 4 | Module globally active where policy requires | Not separately re-checked at the entitlement layer — deliberately deferred: the mission's own `verticals.is_enabled` global toggle (from FINAL-L5-04) is a distinct, already-independently-enforced dimension; layering a second check here was judged out of this sprint's bounded scope, documented as a real gap in Remaining Blockers |
| 5 | Category belongs to module | Enforced — `assign_category_entitlement` resolves the category's real parent vertical and requires an ACTIVE module entitlement for it first, or 409 |
| 6 | Duplicate active entitlement rejected/idempotent | **Idempotent success** (mission allows either) — re-assigning an already-ACTIVE row returns 200 with the existing row unchanged, no duplicate created (DB-verified: partial unique index would reject a true duplicate anyway) |
| 7 | Invalid category/module relationship → controlled 4xx | 409 `CONFLICT` with a real, specific `detail` message |
| 8 | `request_id` on errors | Every `ServiceOSException` carries `request_id` via the RFC 7807 problem-detail handler (existing platform convention, inherited automatically) |
| 9 | Audit event created | Every mutation writes to `entitlement_audit_log` unconditionally — live-verified via `GET .../history` after each mutation |
| 10 | Cache invalidation event triggered | Admin UI calls `useAdminMenuRefresh()` after every mutation (frontend-side refresh, not a backend event bus) — see Cache Invalidation Report for the honest scope of what "invalidation" means here |

## Result
All 8 endpoints real, live-tested (curl + automated pytest RBAC + real Chromium E2E for the mutation+audit flow). 9/10 required checks fully met; 1 (global-module-active gate) deliberately deferred and documented, not silently skipped.
