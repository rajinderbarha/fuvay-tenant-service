# HS5 — Permission Report

## Status: not implemented (same gap as every prior HS sprint this session)
`/provider/service-areas` hardcodes `canCreate = true, canUpdate = true,
canDelete = true, canSetPrimary = true` (confirmed via grep this
sprint) — no permission-aware gating exists on either the service-areas
or availability pages.

## Backend
Both `create_service_area` and `create_availability`/
`update_availability` require `require_tenant_owner` — real, coarse
server-side authorization (unchanged this sprint, confirmed for
availability endpoints via source read).

## Verdict
Permission-aware UI: **not implemented**, consistent with the
established, repeatedly-documented gap across HS2/HS3/HS4/HS4B. Backend
authorization is real (`require_tenant_owner`).
