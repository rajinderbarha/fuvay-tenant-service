# Frontend and Client Caller Audit — Workstream 8

## Method
Grepped `frontend/super-admin/lib/api.ts` and `frontend/tenant-portal/lib/api.ts`
for every path fragment belonging to both modules.

## Findings
- **`frontend/super-admin/lib/api.ts`**: 53 matches across the combined
  path-fragment set for `/admin/packages`, `/admin/finance/deposits`,
  `/admin/finance/payouts`, `/admin/finance/topups`,
  `/admin/finance/warranty-claims`, `/admin/tenants/*/credit-wallet`, and
  `/admin/tenants/*/packages/*/purchase` — confirming the super-admin app
  is the real, live caller for both modules' capabilities.
- **`frontend/tenant-portal/lib/api.ts`**: 2 matches, both irrelevant —
  a comment mentioning "credit-wallet" and a DIFFERENT, already-closed
  endpoint (`GET /v1/tenant/credit-wallet`, the tenant's own read-only
  wallet view, not any endpoint in either audited module). **Zero
  tenant-portal callers of any mutation in `package_commerce.admin_router`
  or `finance_hub.admin_router`** — consistent with both modules being
  genuinely platform-admin-facing, not a case of an admin-named router
  secretly serving tenant traffic (the specific risk the mission warned
  against).

## Is an admin_router actually called from tenant portal?
**No**, for either module — confirmed by direct grep, not assumed from
naming.

## Does a tenant route appear incorrectly in super-admin?
Not applicable — neither module has a tenant-facing counterpart route
within itself; the counterpart (`package_commerce.tenant_router`'s
`tenant_purchase_package`) is a separate, correctly-tenant-scoped router
not audited in depth this slice (only its shared service method was
traced — see `financial-model-lineage.md`).

## Zero-caller routes
Not confirmed as fully dead — the 10 `finance_hub` payout/claims endpoints
and 13 `package_commerce` package-permission-gapped endpoints likely DO
have super-admin frontend callers (they appear among the 53 matches), but
since their underlying permission is granted to no role except
`super_admin`, only a literal `super_admin`-role user can successfully
call them today, regardless of which frontend button exists. This is a
runtime-accessibility finding, not a "the button doesn't exist" finding.

## Workers / scheduled tasks
Not found calling either module directly (grepped for
`package_commerce`/`finance_hub` service imports outside their own router
files and outside each other — no Celery task or cron job found importing
either module's admin services this slice).
