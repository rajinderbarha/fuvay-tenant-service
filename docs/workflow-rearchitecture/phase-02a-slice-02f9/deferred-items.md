# Deferred Items — Slice 2F-9

Explicitly deferred, per the out-of-scope list and this slice's own
findings — none of these were investigated, designed, or acted on:

1. `execution.real_estate_router`, `execution.coaching_router` — not begun.
2. `complaints.customer_router` — confirmed structurally distinct, not
   audited or modified (flagged as the recommended next slice).
3. `complaints.admin_router` — confirmed `require_super_admin`-gated
   throughout (stronger, not a weaker alternate), not modified.
4. Redesigning complaints pages; building a new dispute workspace.
5. Admin/Tenant My Work; Next-Action aggregation.
6. Booking Exception Resolution; merging Booking/Job/ServiceBooking/
   ServiceJob; changing booking creation.
7. Inventing a refund workflow or cash payout workflow.
8. Granting customer service credits or deducting tenant credits beyond
   the existing, already-canonical dual-acceptance mechanism.
9. Merging complaints, warranty claims, and rework models.
10. Creating a new tenant role or role alias.
11. [RESOLVED IN SLICE 2F-9A] Fixing the final-state-check gap on
    `respond_to_complaint`/`offer_resolution`. `offer_resolution` was
    found already protected (no fix needed); `respond_to_complaint`
    (`provider_add_response`) was fixed with a `FINAL_STATUSES` guard.
12. [RESOLVED IN SLICE 2F-9A — WAS NEVER ACTUALLY MISSING] "Adding an
    audit event to `provider_add_response`" — this item was itself
    incorrect. `provider_add_response` already logs
    `EVT_PROVIDER_RESPONDED` via `_log_event`; no event was ever missing.
13. Locating and auditing rework-creation/admin-approval and refund
    admin-approval ownership (flagged, not investigated).
14. Remediation of `readonly@demo-ac-services.local`.
15. Migration 144.
16. Visual redesign.
17. Beginning a second router module.
