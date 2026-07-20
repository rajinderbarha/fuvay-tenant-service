# Frontend/Mobile Exposure Audit — Slice 2F-12 (Workstream 17)

## Caller inventory
`frontend/tenant-portal/lib/api.ts` defines `coachingExecutionApi` (5 of
the 8 backend mutations: `accept`, `start`, `complete`, `noShow`,
`addNote`, plus `getTimeline` and `cancel`) — but **zero `.tsx`
components anywhere in `frontend/tenant-portal` call
`coachingExecutionApi`** (confirmed by repository-wide grep). `reject`
and `request-reschedule` have no frontend client method at all,
backend-only.

No mobile app, staff-app, or other frontend application references any
`coaching-appointments` execution path.

## Requirements review
- **Read-only tenant users have no active tenant mutation controls**:
  N/A — no UI surface exists at all.
- **Staff sees only proven delegated capabilities / technicians see only
  assigned execution capabilities**: N/A, same reason.
- **Customers see only customer self-service actions**: N/A — no
  customer-facing UI exists for coaching tracking either.
- **Backend remains authoritative**: true regardless — this slice's
  router-level fix is the actual enforcement boundary.

## No frontend change made
Per Workstream 17's explicit instruction ("if no frontend surface
exists, report it as absent"), this is reported honestly as an absent
UI surface, not a working workflow. No `.tsx` file was created or
modified.
