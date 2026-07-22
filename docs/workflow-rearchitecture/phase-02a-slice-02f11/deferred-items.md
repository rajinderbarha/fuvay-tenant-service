# Deferred Items — Slice 2F-11

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on:

1. `execution.coaching_router`, `field_ops.checklist_router`,
   `field_ops.staff_router` — not begun.
2. `app.engines.real_estate_lead` (a distinct real-estate module) — not
   begun or audited.
3. No property categories, listing types, or real-estate categories were
   seeded or created.
4. No property/listing marketplace was built.
5. No agent role, broker/agent commission model, or tenant_manager/manager
   alias was created.
6. No payment, escrow, deposit, or payout workflow was created.
7. No lead-subscription monetization was created.
8. Property inquiries were not merged with service bookings; Booking,
   Job, ServiceBooking, ServiceJob were not merged.
9. Booking Exception Resolution, Admin/Tenant My Work, and Next-Action
   aggregation were not implemented.
10. No property or execution page was redesigned; no map provider was
    added.
11. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
12. No permission was granted merely to make a route accessible — the
    fix reuses the pre-existing `require_owner_or_office_staff_mutation`/
    `require_staff_or_above`/`require_customer` dependencies verbatim.
