# Frontend Exposure Audit — Workstream 12

## Method
Grepped `frontend/super-admin/lib/api.ts` and `frontend/tenant-portal` for
all 20 mutation path fragments.

## Findings
- Package CRUD/lifecycle (13 routes: create/update/delete/activate/
  deactivate/clone package + feature/limit CRUD) and `admin_purchase_package`:
  callers exist in `frontend/super-admin/lib/api.ts` under the packages
  admin surface (consistent with the "Packages & Plans" enterprise page
  referenced in the router's own `/summary` endpoint docstring).
- `admin_topup_wallet`, `admin_adjust_wallet`: **zero frontend callers
  found** — confirmed via grep of `credit-wallet` / `credit-ledger` in
  `lib/api.ts` (only the unrelated canonical `usage-credit-ledger` path
  is called, which is a different, non-legacy endpoint not part of this
  module). These 2 routes are reachable only via direct API call today.
- `admin_deduct_commission`, `admin_calculate_commission`: **zero frontend
  callers found** — confirmed via grep of `deduct-commission` /
  `calculate-commission` in `lib/api.ts`.
- The 3 deprecated security-deposit POST routes + 1 GET: zero frontend
  callers (re-confirmed, matches Slice 2F-5A's original finding).

## Tenant-portal exposure
Zero occurrences of `/v1/admin/packages` or `/v1/admin/tenants/{tenant_id}/packages/{package_id}/purchase`
or any of this router's other paths in `frontend/tenant-portal` — no
tenant persona can reach any `package_commerce.admin_router` mutation
from the frontend. Tenant-facing package purchase goes through the
distinct `package_commerce.tenant_router` (its own route,
`tenant_purchase_package`), not this module.

## Role-based UI gating
As in Slice 2F-5B's equivalent finding for `finance_hub`: this slice did
not perform a per-component, per-role trace of which buttons render for
`admin_readonly` vs `admin_finance` vs `super_admin` in the super-admin
Next.js package-admin pages. The backend 403 gate is the authoritative
enforcement point, verified via the direct-authorization test matrix
(196 tests, all personas, all 20 routes). No frontend code was changed
this slice (out of scope: "do not redesign package UI").

## Requirements check
- Tenant portal has no admin-router exposure: confirmed.
- `admin_readonly` sees no mutation controls: not independently traced at
  the UI-component level (see limitation above), but backend-enforced.
- `admin_finance` sees only already-granted operations (the 2 credit-
  wallet routes, which have no frontend caller at all today, so this is
  vacuously true — there is no button to see).
- Super-admin-only operations do not appear to unauthorized platform
  roles: not independently traced at the UI-component level; backend-
  enforced.
- Deprecated security-deposit actions do not appear as active: confirmed
  — zero frontend callers found for any of the 4 routes.

## Conclusion
No frontend changes made. No unsafe exposure proven (the routes with
live frontend callers are exactly the super-admin-only package-CRUD
routes, correctly gated backend-side; the 2 admin_finance-only routes
and the 2 commission routes have no UI surface at all today).
