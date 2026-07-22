# Deferred Items — Slice 2F-10

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on:

1. `complaints.provider_router` — not modified (no shared-service bypass
   required a change there; `_get_settlement_proposal` was already fixed
   by Slice 2F-9 and benefits both routers without further change).
2. `complaints.admin_router` — not modified.
3. `execution.real_estate_router`, `execution.coaching_router` — not begun.
4. No complaint permission was created; no provider actions were granted
   to customers; no customer actions were granted to providers; no
   platform adjudication was granted to customer/tenant roles.
5. No new role or role alias was created.
6. No dispute workspace, internal-note system, cash refund flow,
   payment-gateway refund, or customer service-credit issuance was built.
7. The dual-acceptance settlement model was not changed.
8. Complaints, warranty claims, and rework were not merged; Booking, Job,
   ServiceBooking, ServiceJob were not merged; the booking-pipeline
   architecture question remains unresolved and unmerged.
9. Booking Exception Resolution, Admin/Tenant My Work, Next-Action
   aggregation were not implemented.
10. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
11. No visual redesign occurred; no frontend file was modified at all.
12. `check_eligible`'s full policy was not wired into `create_complaint`
    (ownership only, per the conclusively-provable-defect scope rule).
