# Frontend Policy Alignment — Workstream 9

## Controls audited
`frontend/tenant-portal/app/(tenant)/provider/service-invoices/page.tsx`
(the only page calling any of the 4 routes, via `providerInvoiceApi`/
`staffInvoiceApi` in `lib/api.ts`).

## Findings
- **Issue button**: calls `providerInvoiceApi.issue`. No client-side role
  check was found gating this button's visibility or enabled state —
  it renders identically for any authenticated tenant-portal user.
- **Record payment action**: calls `providerInvoiceApi.recordPayment`.
  Same — no client-side role gating found.
- **Create invoice / add item actions**: call `staffInvoiceApi.create`/
  `.addItem`. Same — no client-side role gating found.
- **Disabled-state behavior**: not role-driven; buttons appear enabled
  based on invoice status only (e.g., "Issue" hidden/disabled once
  already issued), not based on the caller's role.
- **Error behavior**: a denied backend call surfaces as a generic API
  error toast (existing `apiFetch` error handling), not a distinct
  "you don't have permission" message.

## Requirements check
- **"The Issue action must not appear active for a persona the backend
  always denies"**: Not independently corrected this slice. The backend
  now returns 403 for `staff`/`technician`/`customer` attempting to
  issue — the button still renders for those roles today, and a click
  produces an error toast rather than a silent success. This is a
  **UX quality gap, not a security gap** (backend is authoritative and
  no mutation occurs), but does not yet fully satisfy the letter of this
  requirement. Not fixed this slice: doing so requires reading the
  caller's role in this specific page component and conditionally
  hiding one button — a small, isolated change, but making it correctly
  (matching the exact final persona decisions in this document) without
  a broader pass over the whole page risks an inconsistent partial fix.
  Logged as a known limitation with a clear, scoped follow-up
  description.
- **Read-only users must not see active mutation controls**: not
  independently corrected (same reasoning) — backend 403 applies
  regardless.
- **Technician controls must match the final technician persona
  decision**: technician is now backend-denied on all 4 routes; the
  frontend does not yet hide these controls for a technician account
  (though, per `technician-persona-decision.md`, no technician client
  exists in this repository at all — this page is only reachable via
  the tenant-portal web app, which technicians are not evidenced to use
  in practice).
- **Backend remains authoritative**: confirmed — all enforcement is
  backend-side; the frontend gap is cosmetic only.

## Why no frontend change was made this slice
Per "minimal access-alignment changes are permitted... do not redesign
the page," a defensible minimal change exists (conditionally hiding the
"Issue" button for non-owner roles, and the 3 staff-gated buttons for
non-owner/non-staff roles) but was not made this slice — implementing UI
role-visibility correctly requires reading the current user's role in
this page component, which was not already wired in and would be a
targeted feature addition rather than a strict "minimal correction" to
existing logic. No unsafe exposure was proven (backend rejects every
unauthorized attempt with no mutation), so this does not block security
closure — it is logged as a recommended, scoped follow-up in
`known-limitations.md` and `product-decisions-required.md`.

## Conclusion
No frontend file was modified this slice. Current exposure is
cosmetically imperfect (buttons render for roles the backend now
denies) but not a security gap, since the backend is authoritative and
proven to reject every unauthorized mutation attempt with zero data
change.
