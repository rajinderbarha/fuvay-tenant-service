# HS4 — Permission Report

## Backend
Tenant catalog mutation endpoints (`tenant_router.py`) are gated by
`require_permission(P.TENANT_UPDATE)` — confirmed real (re-verified via
grep this sprint, matches the finding from the earlier Type-Dependent
Brand Pricing sprint).

## Frontend
No `usePermissions()`-equivalent gating was found wired into
`/tenant/setup/services` this sprint (not independently re-verified
beyond a grep check — no permission-conditional rendering found for
Publish/Save/Edit actions). Same class of gap as documented in HS2/HS3
for the admin side.

## Ticket's assumed permission namespace
`tenant.home_services.setup.*`/`tenant.home_services.pricing.*` etc. do
not exist in `app/core/permissions.py` — only the generic
`P.TENANT_UPDATE` is used.

## Verdict
Permission enforcement: **real on the backend** (`P.TENANT_UPDATE`
required for all mutations). Frontend permission-aware UI (hiding
Publish/Edit for read-only users): **not implemented**, consistent with
the same gap found across HS2/HS3.
