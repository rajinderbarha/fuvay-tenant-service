# Frontend Exposure Audit — Slice 2F-11 (Workstream 17)

## Caller inventory
`frontend/tenant-portal/lib/api.ts` defines `realEstateExecutionApi`
(9 of the 11 backend mutations: `accept`, `markContacted`,
`scheduleFollowUp`, `planSiteVisit`, `completeSiteVisit`, `qualify`,
`convert`, `closeLost`, `addNote`, plus `getTimeline`) — but **zero
`.tsx` components anywhere in `frontend/tenant-portal` call
`realEstateExecutionApi`** (confirmed by repository-wide grep). `reject`
and `disqualify` have no frontend client method at all, backend-only.

No mobile app, staff-app, or other frontend application references any
`real-estate-leads` path.

## Requirements review
- **Read-only tenant users have no active tenant mutation controls**:
  N/A — no UI surface exists at all to have controls in the first place.
- **Staff sees only proven delegated actions / technicians see only
  assigned execution actions**: N/A, same reason.
- **Backend remains authoritative**: true regardless — this slice's
  router-level fix is the actual enforcement boundary, independent of
  any (currently nonexistent) frontend surface.

## No frontend change made
Per Workstream 17's explicit instruction ("if no frontend surface
exists, report it as absent"), this is reported honestly as an absent
UI surface, not a working customer/staff workflow. No `.tsx` file was
created or modified — building a UI would be a product/design decision
well beyond this slice's authorization-and-ownership-closure scope, and
explicitly not requested.
