# Deferred Items — Slice 2F-10A

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on:

1. `execution.real_estate_router`, `execution.coaching_router` — not begun.
2. `complaints.provider_router`, `complaints.admin_router` — not modified.
3. No complaint permission was added; no role or alias was added.
4. No customer actions were granted to tenant roles; no provider actions
   were granted to customers.
5. No cash refund flow, payment-gateway refund behavior, or new
   service-credit behavior was created.
6. Dual-acceptance settlement was not changed.
7. Complaints, warranty, refund, and rework models were not merged;
   Booking/Job/ServiceBooking/ServiceJob were not merged; the
   booking-pipeline architecture question remains unresolved.
8. Booking Exception Resolution, Admin/Tenant My Work, Next-Action
   aggregation, and a new dispute UI were not built.
9. No visual redesign occurred; no frontend file was modified at all.
10. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
11. `ComplaintPolicy.get_complaint_policy`'s dead `tenant_id` parameter
    was noticed but not fixed (see `known-limitations.md` item 3).
12. `add_customer_message`'s resolved/settled policy question was not
    resolved.
