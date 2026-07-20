# Real-Estate Service Bypass Report — Slice 2F-11 (Workstream 15)

## Every method reached by `real_estate_router`, and every caller
Confirmed via full-repository grep that `real_estate_router.py` is the
**only** caller of `RealEstateLeadExecutionService`'s 12 methods
(`accept_lead`, `reject_lead`, `mark_contacted`, `schedule_follow_up`,
`plan_site_visit`, `complete_site_visit`, `qualify_lead`,
`disqualify_lead`, `convert_lead`, `close_lost`, `add_note`,
`get_timeline`, `get_notes`) — excluding test files.

## No bypass found
Every one of these methods already correctly:
- Filters by `tenant_id` in `_get_lead` (when supplied).
- Enforces `_assert_agent_owns_lead` for every mutation.
- Validates `LEAD_TRANSITIONS` before mutating (`_assert_transition`
  runs before `lead.status = new_status`).

The only gap was the **router-level persona check**, now fixed. No
directly-connected service-layer bypass (of the kind found in
`complaints.provider_router`/`customer_router` in Slices 2F-9/2F-10) was
found here — the service layer's ownership logic was already complete;
only the front door (role gate) was missing.

## No repository-wide real-estate coverage is claimed
This report covers only `RealEstateLeadExecutionService`. The separate
`app.engines.real_estate_lead` module (lead draft/intake creation) and
`app.engines.final_records` (read-only lead listing) were not
independently re-audited service-layer-by-service-layer this slice — out
of scope, per the "do not begin another real-estate module" instruction.
