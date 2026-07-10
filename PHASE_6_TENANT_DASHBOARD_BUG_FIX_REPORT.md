# Phase 6 — Tenant Dashboard Bug Fix Report

## Bugs found and fixed

1. **CRITICAL: The certified test tenant owner's account pointed to a
   phantom tenant, making the entire tenant portal unreachable for them.**
   `provider@serviceos.in`'s `users.tenant_id` was
   `f002bb6b-4e8b-4764-8d45-1f1ce4014999` — a tenant ID with **zero
   matching row** in the `tenants` table (confirmed via
   `GET /v1/admin/tenants/{id}` → `404`). Meanwhile the real "Demo AC
   Services" tenant's `owner_user_id` correctly pointed back to this exact
   user. Since every tenant-portal endpoint derives its tenant scope solely
   from the JWT's `tenant_id` claim (itself populated from
   `users.tenant_id` at login), this account could never actually reach
   its own real tenant's data — `GET /v1/tenant/dashboard/runtime` returned
   `tenant: null` for everything, and `GET /v1/tenant/wallet` silently
   returned a fresh zeroed-out balance for a wallet that doesn't exist
   under the phantom ID, masking the failure completely (no error, just
   wrong/empty data). Fixed by correcting `users.tenant_id` to point to the
   real Demo AC Services tenant. Live-confirmed after a fresh login:
   `dashboard/runtime` now resolves `tenant.business_name: "Demo AC
   Services"`, and `/v1/tenant/wallet` returns the real ledger history from
   Phase 4/5's test cycles (`lifetime_purchased: 1100,
   lifetime_consumed: 1100, balance: 0`).

2. **The `request_id` hardcoded-placeholder bug (first found and fixed in
   `package_commerce` during Phase 4, then `provider_portal`'s admin-side
   router during Phase 5) also existed across all 3 tenant-facing
   routers**: `tenant_engine/portal_router.py` (18 occurrences),
   `package_commerce/tenant_router.py` (2 occurrences), and
   `provider_portal/router.py` (28 occurrences — the tenant/provider-facing
   half of that file, distinct from the admin-facing half fixed in Phase
   5). All read `request.headers.get("X-Request-ID", "—")` instead of the
   real middleware-generated `request.state.request_id`. Fixed all 48
   occurrences across the 3 files. Live-confirmed: `dashboard/runtime`'s
   `meta.request_id` now shows a real `req_xxxx` ID instead of the literal
   placeholder.

## End-to-end proof (after fixes, real backend + real Postgres)

```
Fresh login (provider@serviceos.in) → JWT now carries the correct real tenant_id
→ GET /v1/tenant/dashboard/runtime → tenant correctly resolved, real request_id
→ GET /v1/tenant/wallet → real balance (0), real request_id
→ GET /v1/tenant/security-deposit → required_amount 5000, status unpaid, real request_id
→ POST /v1/tenant/service-areas {Ludhiana, 141001, zipcode} → created, real request_id
→ GET /v1/tenant/catalog/available-services → real platform catalog data
→ GET /v1/tenant/catalog/enabled-services → correctly empty (not yet configured)
→ GET /v1/tenant/staff → correctly empty (no staff created for this tenant yet)
→ tenant_id override via query param → silently ignored (isolation confirmed)
```

## Bugs found, not fixed (documented as blockers, correctly out of scope or too large for this sprint)

- **No dedicated tenant-portal document upload/reupload endpoint for
  onboarding-verification documents** (gst_certificate/pan_card/etc, the
  `TenantDocument` model from Phase 5). The only document-related router
  found (`app/engines/document/router.py`, prefix `/v1/documents`) is a
  generic contract e-signature engine, unrelated to onboarding document
  verification. Module 13's tenant-facing document view/reupload flow does
  not exist — a genuine feature gap, not a bug to patch over.
- **`GET /v1/tenant/dashboard/runtime`'s `enabled_engines`/`modules` fields
  are hardcoded empty lists** — confirmed via source inspection, not just
  live behavior. This appears to be an intentional stub for a
  category-driven dashboard-module system that was never finished. Not
  fixed — building the real module-resolution logic is a feature project,
  not a bug fix, and risks scope creep into "customer booking"/"job
  lifecycle" territory this ticket explicitly excludes.
- **Two overlapping wallet-read endpoints** exist:
  `tenant_engine/portal_router.py`'s `/v1/tenant/wallet` (returns a
  `WalletBalance`-shaped object, always succeeds with zeros if no wallet
  row exists) and `package_commerce/tenant_router.py`'s
  `/v1/tenant/credit-wallet` (404s if no wallet row exists). Both are
  correct in their own way (one is a "safe default" view, the other is a
  "does a real wallet exist" check) but are inconsistent with each other
  and not clearly documented as serving different purposes. Not
  consolidated this sprint — flagged for a future reconciliation pass.
- **Demo Technician** (referenced in this ticket's baseline scenario) does
  not actually exist as a real staff/user record for Demo AC Services —
  `GET /v1/tenant/staff` correctly returns empty. Not fabricated; documented
  as a fixture gap.
