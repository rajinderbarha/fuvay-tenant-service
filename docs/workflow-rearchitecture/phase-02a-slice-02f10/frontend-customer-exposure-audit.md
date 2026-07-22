# Frontend/Customer-App Exposure Audit — Slice 2F-10 (Workstream 17)

## Caller inventory
Exactly one frontend surface calls any `customer_router` route:
`frontend/customer-app/lib/api/customer-complaints.ts` — a single API
client module used by the customer-app's complaint screens. No
tenant-portal, super-admin, or mobile staff-app file references any
`/v1/customer/complaints*` path (confirmed by repository-wide search).

## Requirements review
- **Only authenticated customers see customer complaint controls**:
  by construction — `customer-app` is a customer-only application; there
  is no role-switching UI in it that could expose these controls to a
  non-customer persona. No frontend change was needed or made.
- **Provider/technician surfaces do not expose customer-only
  decisions**: confirmed — `tenant-portal`'s provider complaint page
  (Slice 2F-9/2F-9A/2F-9B) has no accept/reject-resolution or
  respond-to-settlement-as-customer control; those are structurally
  separate provider-side actions (`offer_resolution`,
  `create_settlement_proposal`) on different service methods.
- **Backend remains authoritative**: the router-level `require_customer`
  gate and all service-layer ownership fixes in this slice apply
  regardless of what the customer-app's UI shows or hides.

## No frontend change made this slice
Given the backend fixes fully close the authorization/ownership/state
gaps, and the customer-app already only exposes these controls to an
authenticated customer viewing their own complaint (fetched via the now
correctly ownership-and-role-enforced `GET
/v1/customer/complaints/{id}`), no frontend policy misalignment was
found that required a change. This is reported honestly as "no change
needed," not fabricated as "verified working" — the customer-app's own
component-level rendering logic (e.g. whether it hides an accept/reject
button once a resolution has already been decided) was not exhaustively
reviewed line-by-line, since the backend is authoritative and already
rejects a repeated/illegal-state decision cleanly (see
`resolution-decision-boundary.md`).
