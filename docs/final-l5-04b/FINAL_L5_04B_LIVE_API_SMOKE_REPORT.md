# FINAL-L5-04B — Live API Smoke Report

All calls below are real HTTP requests made via `curl` against the live dev backend (`localhost:8000`) during this sprint — no mocking.

| # | Step | Method/Path | Role | Status | Result |
|---|---|---|---|---|---|
| 1 | Admin reads Tenant One entitlements | `GET /v1/admin/tenants/{t1}/entitlements` | super_admin | 200 | `modules:[home_services ACTIVE]`, `categories:[ac_services ACTIVE]` |
| 2 | Admin assigns a category | `POST /v1/admin/tenants/{t1}/entitlements/categories` `{category_id: plumbing}` | super_admin | 200 | Tenant One gained a second category (used for multi-category proof, then cleaned up) |
| 3 | Tenant One reads updated entitlements | `GET /v1/tenant/me/entitlements` | tenant_owner (T1) | 200 | Reflected the new category immediately, no delay |
| 4 | Tenant Two does not receive the entitlement | `GET /v1/tenant/me/entitlements` | tenant_owner (T2) | 200 | Unaffected — still only `plumbing` |
| 5 | Admin disables category | `POST /v1/admin/tenants/{t1}/entitlements/categories/{ac_id}/disable` | super_admin | 200 | `status: INACTIVE` |
| 6 | Tenant navigation API no longer returns it | `GET /v1/tenant/me/categories` | tenant_owner (T1) | 200 | `categories: []` while disabled |
| 7 | Direct route is denied | `POST /v1/tenant/catalog/enable-service` (AC-group service) | tenant_owner (T1) | **403** `CATEGORY_NOT_ENTITLED` | Real enforcement, not a UI hide |
| 8 | Admin re-enables category | `POST /v1/admin/tenants/{t1}/entitlements/categories/{ac_id}/reenable` | super_admin | 200 | `status: ACTIVE` |
| 9 | Tenant navigation API returns it again | `GET /v1/tenant/me/categories` | tenant_owner (T1) | 200 | `ac_services` reappeared immediately |
| 10 | Audit history records all changes | `GET /v1/admin/tenants/{t1}/entitlements/history` | super_admin | 200 | Full chronological list: ASSIGNED → DISABLED → REENABLED, each with real `actor_id`/`actor_role`/`request_id`/`created_at` |

## Additional real smoke evidence beyond the required 10 steps
- Duplicate active-row rejection at the raw-SQL/DB level (`UniqueViolationError`).
- 404 for a nonexistent category ID on assign.
- 403 for cross-tenant admin access attempts (both read and mutate).
- 401 for anonymous access.
- Positive-path proof: an entitled (`ac_services`) service enable call succeeded (201) at the same time a non-entitled (`plumbing`) one correctly 403'd, on the same tenant, same session.
- A real production bug (`StringDataRightTruncationError`, VARCHAR(20) overflow in the cascade-audit path) was found via this exact smoke-testing process and fixed before being shipped.

See `live-api-smoke-results.json` for the structured, timestamped record.
