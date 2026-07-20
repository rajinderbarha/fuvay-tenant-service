# Parts and Quote Boundaries — Workstream 11

## Verified rule preserved: PartsRequest is ServiceJob-linked only
Confirmed via direct model reading (`app/engines/execution/models.py`):
`PartsRequest.job_id` references `ServiceJob`, with `tenant_id` and
`technician_id` columns alongside it. All 4 Parts-related mutation
endpoints (`staff_create_parts_request`, `provider_approve_parts_request`,
`provider_reject_parts_request`, `provider_install_parts_request`) live
exclusively in `execution.home_service_router`.

## No competing route exists in home_service_assignment
Grepped `app/engines/home_service_assignment/staff_router.py` and
`provider_router.py` for the string `"parts"` (case-insensitive): **zero
matches**. No Parts creation, approval, rejection, or installation
capability is exposed anywhere in the assignment module. Confirmed via the
new regression test
`TestPartsRequestBoundaryIntact::test_no_parts_endpoints_in_home_service_assignment_module`.

## No quote-line-items treated as PartsRequest
`staff_quote_required` (execution router) only flags a job as needing a
quote — it does not create, read, or reference any `PartsRequest` row, and
the actual quote/checklist mechanism (Sprint 22, `test_sprint22_quote_checklist.py`
/ `test_step8_quote_checklist.py`) is a structurally separate concern
(confirmed by different table/model names, not investigated line-by-line
this slice since it is outside the 3-module overlap scope, but no evidence
of conflation was found in the routes actually audited).

## No cross-pipeline Parts adapter introduced or found
This slice introduced no code linking Parts to any non-`ServiceJob` record
type, consistent with the mission's explicit prohibition.

## Provider-only installation remains restricted
`provider_install_parts_request` remains in `execution.home_service_router`,
unchanged this slice — its provider-only restriction (established in a
prior slice per the brief's preservation list) was not touched, removed, or
weakened.

## Conclusion
**No boundary violation found.** No security or product blocker exists on
this dimension for the 3 modules audited.
