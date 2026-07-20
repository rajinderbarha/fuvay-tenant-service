# Deferred Items — Slice 2F-9B

Explicitly deferred, per the out-of-scope list — none of these were
investigated, designed, or acted on:

1. `complaints.customer_router` — not begun or modified.
2. `complaints.admin_router` — not modified (its own "Propose resolution"
   control, calling a distinct admin endpoint, was identified in the
   caller inventory but not touched — different service method, different
   router, out of scope).
3. `execution.real_estate_router` — not begun.
4. No provider complaint authorization was changed; no permission was
   granted; no role was created; no complaint capability was granted to
   staff or technicians.
5. `FINAL_STATUSES` and `ALLOWED_TRANSITIONS_EXT` were not changed.
6. Whether `provider_add_response` should also block on
   `resolved`/`settled` was not decided.
7. No new state machine, dispute workspace, or internal-note system was
   built.
8. Settlement, refund, rework, and credit behavior were not changed.
9. No models were merged; Booking Exception Resolution, Admin/Tenant My
   Work, and Next-Action were not implemented.
10. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
11. No visual redesign occurred.
12. Component-level/E2E frontend test tooling was not introduced (see
    `known-limitations.md` item 1).
