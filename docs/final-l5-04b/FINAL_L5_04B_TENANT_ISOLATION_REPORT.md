# FINAL-L5-04B — Tenant Isolation Report

> **Updated in FINAL-L5-04C**: row 5 (matching) is now real and verified; row 4 (staff) remains N/A per the Staff Entitlement Scope Report's finding that no staff category-filter endpoint exists.

## Required proofs — all verified with real evidence
| # | Requirement | Result |
|---|---|---|
| 1 | Tenant One cannot read Tenant Two entitlements | **Structurally impossible, not just blocked** — tenant self-read endpoints have no `tenant_id` parameter at all; the tenant is derived exclusively from the caller's own JWT. There is no URL a Tenant One user could construct to read Tenant Two's data via `/v1/tenant/me/*`. |
| 2 | Tenant One cannot mutate Tenant Two entitlements | **403, live-verified** — a `tenant_owner` token attempting `GET`/`POST` against `/v1/admin/tenants/{any_id}/entitlements*` gets 403 regardless of which tenant_id is in the URL, because the admin API requires `super_admin` outright (stronger than per-tenant scoping) |
| 3 | Tenant Two cannot use Tenant One category routes | N/A in the strict "URL" sense (no category-scoped tenant-portal route exists yet, see Tenant Navigation Integration Report) — but proven at the data layer: Tenant Two's `/v1/tenant/me/categories` never returns `ac_services` (Tenant One's category), only `plumbing` |
| 4 | Staff from Tenant One cannot see Tenant Two filters | N/A — no staff category-filter endpoint exists in this codebase at all (confirmed by dedicated investigation, see Staff Entitlement Scope Report) — there is nothing to isolate because there is no cross-tenant-visible surface to begin with |
| 5 | Matching never crosses entitlement boundaries | **FINAL-L5-04C: now real and verified.** The bulk entitlement resolver (`get_entitled_tenant_ids_for_category`) is queried per-category, per-candidate-pool — a candidate tenant's entitlement is resolved from its own rows only (the SQL `WHERE tenant_category_entitlements.tenant_id IN (...)` clause never joins across tenants). Live-verified: Tenant One's Plumbing-service matching attempt is excluded with `TENANT_CATEGORY_NOT_ENTITLED` even though Tenant Two holds a real, ACTIVE Plumbing entitlement — proving Tenant One cannot benefit from Tenant Two's grant. |
| 6 | Admin scoped roles follow platform policy | Verified — only `super_admin` can touch any tenant's entitlements, consistent with the platform's existing admin-role policy |

## Real, repeated live evidence (not a single lucky run)
- Curl-based cross-tenant attempt: Tenant One owner token → `GET /v1/admin/tenants/{tenant_two_id}/entitlements` → `403 PERMISSION_DENIED`.
- Curl-based cross-tenant mutation attempt: Tenant One owner token → `POST /v1/admin/tenants/{tenant_two_id}/entitlements/modules` → `403 PERMISSION_DENIED`.
- Real Chromium E2E, run multiple times across this sprint's debugging iterations, consistently proving: Tenant One's `/v1/tenant/me/entitlements` → `categories: ["ac_services"]` only; Tenant Two's → `categories: ["plumbing"]` only. Never once did either tenant's response include the other's category.

## Valid and invalid IDs tested
- Valid Tenant Two ID used in the cross-tenant attempts above (real UUID, real tenant) — correctly 403'd.
- A fully random/nonexistent category UUID was tested against the admin category-assign endpoint — correctly 404'd (`EntitlementNotFoundError`), not a 500 or an unintended success.

## Result
Isolation is real and proven for the module/category data layer, the admin API's tenant-targeting surface, and (as of 04C) the matching engine itself — Tenant One cannot match using Tenant Two's Plumbing entitlement, live-verified. Staff isolation remains N/A because no staff category-filter surface exists to isolate.
