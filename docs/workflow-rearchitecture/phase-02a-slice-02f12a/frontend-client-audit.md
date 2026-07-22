# Frontend/Client Audit — Slice 2F-12A (Workstream 11)

## Cancel API client method
`frontend/tenant-portal/lib/api.ts` — `coachingExecutionApi.cancel(apptId,
reason)` → `POST /v1/provider/coaching-appointments/{apptId}/cancel`.

## Component callers
**None.** Repository-wide grep confirms `coachingExecutionApi` (and its
`.cancel` method) is defined in `lib/api.ts` but called by **zero `.tsx`
components** in `frontend/tenant-portal` (same finding as Slice 2F-12 for
the whole module). No mobile app, staff-app, or customer-app references
the coaching-appointment cancel path.

## Record
- **Caller persona**: n/a (no component caller).
- **Assignment context**: n/a.
- **Current role gate**: backend `require_owner_or_office_staff_mutation`
  (authoritative regardless of any UI).
- **Access-scope gate**: backend (read-only denied).
- **State gate**: backend (`APPT_TRANSITIONS`).
- **Confirmation / reason handling**: the API client requires a `reason`
  argument, matching the backend's `ERR_REASON_REQUIRED`.

## Disposition
**FRONTEND_MUTATION_SURFACE_ABSENT** — reported honestly, no UI exists.
No frontend change was made (none needed; the backend is the sole,
authoritative enforcement boundary). No UI was built.
