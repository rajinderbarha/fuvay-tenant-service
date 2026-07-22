# Parts and Quote Execution Security — Workstream 7

## Preserved rule
`PartsRequest` remains `ServiceJob`-only (`job_id` FK, confirmed unchanged
this slice — no model or table change was made). All 4 Parts mutation
endpoints (`staff_create_parts_request`, `provider_approve_parts_request`,
`provider_reject_parts_request`, `provider_install_parts_request`) remain
exclusively in `execution.home_service_router`.

## What changed
All 4 now use `require_staff_or_above_mutation` in place of bare
`get_current_user` — the same access-scope-aware guard applied to every
other execution-progress endpoint. No new permission was introduced; no
Parts capability was added to `home_service_assignment` (confirmed via the
unchanged `TestPartsRequestBoundaryStillIntact` regression tests, carried
over and re-passing from Slice 2F-3A).

## Provider-only installation
`provider_install_parts_request`'s provider-only restriction (established
in a prior slice, per the preservation list) lives in the handler/service
logic downstream of the router-level guard, not in the guard itself — this
slice's guard swap only establishes "authenticated, staff-or-above role,
not read-only-scoped," which is a **superset** check layered in front of
the existing, unmodified provider-only restriction. Confirmed via source
reading: the guard swap touched only the `Depends(...)` line, nothing in
the function body.

## What was NOT independently re-verified this slice
The exact mechanism enforcing "provider-only" for install (e.g. does it
check `user.role`, a specific permission, or an assignment-derived
provider-identity check?) was not re-traced end-to-end this slice — it was
confirmed unchanged (not touched), not re-audited for correctness. Flagged
in `known-limitations.md` for the record; not a new gap introduced.

## Quote actions
`staff_quote_required` only flags a job as needing a quote — confirmed
(same as Slice 2F-3A's finding) it does not create, read, or touch any
`PartsRequest` row. No quote-line-item is ever treated as a `PartsRequest`
record; no code change was made to this boundary.

## No cross-pipeline adapter introduced
Consistent with the mission's explicit prohibition — no code this slice
links `PartsRequest` to any non-`ServiceJob` record type, and no Parts
action was added to `home_service_assignment`.
