# HS4B — Permission UI Report

## Status: not implemented this sprint (documented, not claimed done)
Consistent with the same gap already documented in HS2/HS3/HS4: the
tenant setup wizard does not use any `usePermissions()`-equivalent
gating. The ticket explicitly allows this: *"If full permission UI
cannot be completed in this sprint, document as remaining blocker, but
do not claim READY."*

## What is real
Backend mutation endpoints (`set_type_pricing`, `set_brand_pricing`,
`publish_service`, etc.) are gated by `require_permission(P.TENANT_UPDATE)`
— confirmed unchanged, real, server-side enforcement. The new
`/status/refresh` endpoint requires `require_tenant_owner` (unchanged
from the original stub) — a coarser but real authorization gate.

## Not done
- No frontend hiding of Publish/Save/Refresh-status buttons based on
  permission.
- No dedicated `tenant.home_services.*` permission constants exist
  (same finding as every prior HS sprint this session).

## Verdict
Permission-aware UI: **not implemented**. Backend authorization is real
(`P.TENANT_UPDATE`, `require_tenant_owner`). This is an honest,
explicitly-flagged gap per the ticket's own allowance — not a silent
omission.
