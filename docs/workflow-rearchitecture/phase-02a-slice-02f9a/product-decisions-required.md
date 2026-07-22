# Product Decisions Required — Slice 2F-9A

These are open questions, explicitly not decided or silently resolved by
code in this slice.

1. **Should `provider_add_response` also block on `resolved`/`settled`,
   not just base `FINAL_STATUSES`?** Currently a provider can still send
   a message after a complaint is `resolved` or `settled` (these are not
   in `FINAL_STATUSES`, only in the broader `FINAL_STATUSES_EXT`). This
   mirrors the customer-side sibling method's identical behavior, so it
   is at minimum *consistent*, but whether post-resolution/post-settlement
   messaging should be allowed at all is a product policy question, not
   a technical one. Classification: **PRODUCT_DECISION_REQUIRED**. Not
   changed this slice — changing it would mean diverging from the
   customer-side sibling's behavior without an explicit product decision
   to do so.

2. **[RESOLVED IN SLICE 2F-9B — not actually a product decision.]** Was:
   "Should the frontend gate `offer_resolution`'s button on the full
   2-state legal-source set instead of the coarser 3-state final check?"
   On reflection in Slice 2F-9B, this was mischaracterized as a product
   question — deriving the exact frontend gate from the already-approved
   backend `ALLOWED_TRANSITIONS_EXT` policy requires no new policy
   decision, only precise implementation. Slice 2F-9B implemented
   `canOfferProviderComplaintResolution` matching the exact 2-state set.
   See `phase-02a-slice-02f9b/frontend-helper-design.md`.

3. **`complaints.customer_router`'s own authorization gap** (flagged in
   Slice 2F-9, reiterated here) remains the most consequential open item
   in this problem area, but is explicitly out of scope for this slice
   per the "do not begin complaints.customer_router" instruction.
