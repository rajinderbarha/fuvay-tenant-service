# Frontend and Caller Alignment

## Confirmed via `frontend/tenant-portal/lib/api.ts`'s `bookingsApi`

The tenant-portal frontend exposes: `list`, `get`, `confirm`, `cancel`, `requestReschedule`,
`acceptReschedule`, `rejectReschedule`, `convertToJob`, `addNote`, `listNotes`,
`checkSlotAvailability`, `getCancellationPolicy`, `voidBooking`, `getTimeline`, `search`.

**No `create` method exists in `bookingsApi`.** The tenant-portal frontend never calls
`POST /v1/bookings` at all — confirming this slice's own finding
(`create-booking-caller-inventory.csv`) that the "tenant_owner override" path has no live UI
caller. `FRONTEND_MUTATION_SURFACE_ABSENT` for tenant-assisted booking creation specifically.

`bookingsApi.confirm` IS a live, called capability — confirmed via
`frontend/tenant-portal/app/(tenant)/bookings/[id]/page.tsx` and
`frontend/tenant-portal/app/(tenant)/bookings/page.tsx`.

## Requirements verified

- **Customer self-booking does not submit another customer's ID**: the customer-facing booking
  creation flow (not audited in exhaustive detail this slice, out of primary scope, but confirmed
  via backend inspection that `customer_id` is always server-derived for `customer`-role
  requests regardless of what any frontend sends) — backend remains authoritative either way.
- **Provider-assisted booking does not advertise arbitrary global customer selection**: confirmed
  — no such UI exists at all (no `create` method in `bookingsApi`).
- **Provider confirmation is not labelled as customer consent**: `bookingsApi.confirm`'s button
  context (in the tenant-portal booking detail page) presents this as a tenant-side action
  (consistent with the backend's `PROVIDER_ACCEPTS_BOOKING` semantics) — no minimal alignment
  change was needed since the frontend never mislabels this as customer consent.
- **Customer confirmation controls appear only where supported**: confirmed — no
  customer-facing "confirm" control exists anywhere (the backend has no route for it either).
- **Read-only tenant users see no mutations**: not independently re-audited at the frontend level
  this slice (would require live UI testing, out of scope for a backend-focused slice) — the
  backend's `require_tenant_mutation_permission` (fixed this slice) is the authoritative
  enforcement point regardless of what the frontend renders.
- **Backend remains authoritative**: confirmed throughout — every fix this slice made is
  server-side; no frontend file was modified.

## No frontend changes made

Since the vulnerable "tenant-assisted booking creation" path has no live frontend caller, no
frontend alignment change was required or made this slice.
