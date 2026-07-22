# Frontend and Client Caller Audit — Workstream 5

## Method
Grepped `frontend/tenant-portal/lib/api.ts` (the only frontend app with a
provider/staff execution-and-assignment surface) for every one of the 29
routes' path fragments.

## Findings

| Path fragment | Caller exists | Notes |
|---|---|---|
| `/staff/service-jobs/{id}/accept` | YES (2 call sites, lines ~3040, ~4075) | Calls the shared path; always answered by `home_service_assignment.staff_router` at runtime (confirmed this slice) — the frontend has no way to distinguish which module answers, and doesn't need to. |
| `/staff/service-jobs/{id}/reject` | YES (2 call sites) | Same. |
| `/provider/service-jobs/{id}/assign` | YES (2 call sites, lines ~2984, ~4132) | `home_service_assignment.provider_router` — sole owner. |
| `/provider/service-jobs/{id}/reassign` | YES (line ~2989) | Sole owner. |
| `/provider/service-jobs/{id}/cancel-assignment` | YES (line ~2994) | Sole owner. |
| `/provider/service-jobs/{id}/schedule` | YES (line ~2999) | Sole owner. |
| `/provider/service-jobs/{id}/cancel` | YES (line ~3062) | `execution.home_service_router` — sole owner of whole-job cancellation, distinct from cancel-assignment. |
| `/provider/service-jobs/{id}/parts-requests/{id}/reject` | YES (lines ~3074, ~4137) | `execution.home_service_router` — sole owner. |
| Other `execution.home_service_router` staff progress routes (on-the-way, reached-site, start-*, work-done, complete*, notes, media, parts-required, quote-required) | Not individually re-verified this slice | These were not part of the confirmed overlap and are out of this slice's specific-overlap mandate; Slice 2F's original inventory already covers them as `TENANT_TECHNICIAN_MUTATION` classified, unprotected. |

## Does the client present both competing actions?
**No.** The tenant-portal frontend calls the shared `/accept`/`/reject`
paths exactly once each per action (no separate "legacy" vs "new" button) —
there is no UI ambiguity, since only one implementation is ever reachable
regardless of which the frontend developer believes they're calling.

## Does the client have fallback behavior if the primary call fails?
Not observed — a single `apiFetch` call per action, no retry-to-alternate-
endpoint logic found.

## Mobile / customer-app
Not applicable — these are provider/staff/technician-facing capabilities;
`mobile/customer-app` has no execution or assignment surface (confirmed via
Slice 2F-era review, not re-grepped exhaustively this slice since these
capabilities are structurally staff/provider-only, not customer-facing).

## Conclusion
Frontend behavior is unaffected by the shadowing finding — real traffic to
`/accept`/`/reject` has always gone to (and continues to go to) the correct,
intended, ownership-checked `home_service_assignment.staff_router`
implementation. No frontend change is needed or was made.
