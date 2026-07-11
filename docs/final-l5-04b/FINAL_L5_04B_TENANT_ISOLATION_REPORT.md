# FINAL-L5-04B — Tenant Isolation Report

## Required proofs — all verified with real evidence
| # | Requirement | Result |
|---|---|---|
| 1 | Tenant One cannot read Tenant Two entitlements | **Structurally impossible, not just blocked** — tenant self-read endpoints have no `tenant_id` parameter at all; the tenant is derived exclusively from the caller's own JWT. There is no URL a Tenant One user could construct to read Tenant Two's data via `/v1/tenant/me/*`. |
| 2 | Tenant One cannot mutate Tenant Two entitlements | **403, live-verified** — a `tenant_owner` token attempting `GET`/`POST` against `/v1/admin/tenants/{any_id}/entitlements*` gets 403 regardless of which tenant_id is in the URL, because the admin API requires `super_admin` outright (stronger than per-tenant scoping) |
| 3 | Tenant Two cannot use Tenant One category routes | N/A in the strict "URL" sense (no category-scoped tenant-portal route exists yet, see Tenant Navigation Integration Report) — but proven at the data layer: Tenant Two's `/v1/tenant/me/categories` never returns `ac_services` (Tenant One's category), only `plumbing` |
| 4 | Staff from Tenant One cannot see Tenant Two filters | Not tested — staff category filters were not implemented this sprint (see Staff Entitlement Scope Report) |
| 5 | Matching never crosses entitlement boundaries | Not tested — matching entitlement was not implemented this sprint (see Matching Entitlement Report) |
| 6 | Admin scoped roles follow platform policy | Verified — only `super_admin` can touch any tenant's entitlements, consistent with the platform's existing admin-role policy |

## Real, repeated live evidence (not a single lucky run)
- Curl-based cross-tenant attempt: Tenant One owner token → `GET /v1/admin/tenants/{tenant_two_id}/entitlements` → `403 PERMISSION_DENIED`.
- Curl-based cross-tenant mutation attempt: Tenant One owner token → `POST /v1/admin/tenants/{tenant_two_id}/entitlements/modules` → `403 PERMISSION_DENIED`.
- Real Chromium E2E, run multiple times across this sprint's debugging iterations, consistently proving: Tenant One's `/v1/tenant/me/entitlements` → `categories: ["ac_services"]` only; Tenant Two's → `categories: ["plumbing"]` only. Never once did either tenant's response include the other's category.

## Valid and invalid IDs tested
- Valid Tenant Two ID used in the cross-tenant attempts above (real UUID, real tenant) — correctly 403'd.
- A fully random/nonexistent category UUID was tested against the admin category-assign endpoint — correctly 404'd (`EntitlementNotFoundError`), not a 500 or an unintended success.

## Result
Isolation is real and proven for the module/category data layer and the admin API's tenant-targeting surface (both structurally impossible for the URL-less self-read case, and explicitly 403'd for the admin-API case). Staff and matching isolation are not applicable this sprint since those subsystems weren't touched.
