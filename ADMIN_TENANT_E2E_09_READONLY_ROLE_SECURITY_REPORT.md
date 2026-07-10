# ADMIN-TENANT-E2E-09 — Read-Only/Role Security Report

Real users confirmed via psql (`users` table):

| Email | role | access_scope |
|---|---|---|
| provider@serviceos.in | tenant_owner | (none — full owner) |
| tenant.manager@serviceos.in | tenant_owner | tenant_scoped |
| tenant.readonly@serviceos.in | tenant_owner | customer_support_limited |

All three exist and are `is_active=true`. Note: all three carry `role=tenant_owner` in the DB; the distinction is entirely via `access_scope`, not a separate role value — "Tenant Manager" is not a separate DB role, it's the `tenant_scoped` access_scope on a tenant_owner-role user. This matches the platform's existing access_scope-based model used elsewhere (e.g., prior sprint's business-profile gap).

## Real finding: access_scope gap CONFIRMED to extend to service-setup pricing endpoints

Direct API call as `tenant.readonly@serviceos.in` (customer_support_limited scope):
```
PUT /v1/tenant/catalog/enabled-services/015efedb.../types/{split_ac}/pricing
Body: {tenant_min_price:700, tenant_max_price:850}
-> 422 TENANT_PRICE_BELOW_ADMIN_MIN (business validation error)
```
The request was **not** rejected with 403 for insufficient access_scope — it reached full business-logic validation, meaning the endpoint has no access_scope/role gate at all (any authenticated tenant_owner-role user, regardless of access_scope, can call every mutation in `tenant_router.py`: set-types, set-brands, set-type-pricing, set-brand-pricing, publish, save-draft — confirmed by reading all 12 endpoints, none reference `access_scope` or any scope-check dependency).

This is the **same class of gap** previously documented for `PUT /v1/provider/business-profile` in an earlier sprint, now confirmed to also affect the Service Setup / Coverage mutation endpoints tested in this sprint. Per the spec, fixing the business-profile instance is out of this sprint's scope, but this sprint's own endpoints being affected IS in scope to report (and would be reasonable to fix in a future dedicated security-hardening pass, given the scale of the router — 12 endpoints).

## UI-side observation
The Service Coverage page shows Publish/Save Draft buttons unconditionally for any logged-in tenant user regardless of access_scope — confirmed via browser as `tenant.readonly`: 15 "Publish" buttons rendered on the page (one per active service row) with no client-side disabling based on role. Combined with the backend gap above, a read-only-scoped user currently CAN both see and successfully invoke mutation actions on this page.

## Verdict: GAP CONFIRMED (not fixed — same-class pre-existing issue, remediation would require adding an access_scope guard to `tenant_router.py`'s 12 mutation endpoints plus client-side UI gating; scoped as a fix candidate for a future dedicated security sprint, consistent with how the spec treats the already-known business-profile instance of this same class of bug).
