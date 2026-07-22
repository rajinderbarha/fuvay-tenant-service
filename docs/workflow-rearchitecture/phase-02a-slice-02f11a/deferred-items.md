# Deferred Items — Slice 2F-11A

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on:

1. `execution.coaching_router`, `field_ops.checklist_router`,
   `field_ops.staff_router` — not begun.
2. `app.engines.real_estate_lead` was inspected and classified, per the
   mission's explicit allowance, but not implemented, modified, or
   independently hardened as a new workstream.
3. No Property, Listing, Viewing, Offer, or PropertyMedia model was
   built.
4. No agent/broker role or tenant_manager/manager alias was created.
5. No permission was added.
6. No brokerage, escrow, deposit, or payout behavior was created.
7. No downstream conversion record was created.
8. Lead records were not merged with Booking, Job, ServiceBooking, or
   ServiceJob.
9. Booking Exception Resolution, Admin My Work, Tenant My Work, and
   Next-Action aggregation were not implemented.
10. No frontend lead page was built; no visual redesign occurred.
11. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
