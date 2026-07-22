# Property/Listing Ownership — Slice 2F-11 (Workstream 8)

## Reported as absent, not fabricated
No `Property`, `PropertyListing`, `PropertyUnit`, publication/
availability toggle, or listing-taxonomy model exists anywhere in this
codebase (see `real-estate-model-lineage.md`). There is therefore no
property-creation, listing-publication, unit-management, or
availability-management capability to audit, own, or protect in
`app.engines.execution.real_estate_router` or any connected service.

## What IS enforced (tenant/lead ownership, the closest analogue)
`RealEstateLead.tenant_id` is enforced via `_get_lead`'s tenant filter
(`RealEstateLead.tenant_id == tenant_id`, sourced from the authenticated
principal's own `tenant_id`, never request-supplied) — this is the
closest existing analogue to "property belongs to tenant" and is fully
enforced, re-verified this slice.

## Explicitly not built this slice
Per the mission's out-of-scope list ("do not seed real estate
categories," "do not create property categories or listing types,"
"do not build a real estate marketplace"), no property/listing model,
route, or ownership mechanism was created. This document exists to
honestly confirm the absence, per Workstream 17's instruction: "if no
frontend surface exists, report it as absent" — the same principle
applied here to the backend capability itself.
