# Known Limitations — Slice 2F-9A

1. **`provider_add_response` still allows messaging after `resolved`/
   `settled`** (only blocked on base `FINAL_STATUSES`) — consistent with
   its customer-side sibling, but a genuine open product question (see
   `product-decisions-required.md` item 1). Not fixed.

2. **Frontend "Offer resolution" button is gated on a coarser 3-state
   final check, not the full 2-state legal-source set** — it will still
   render (and then correctly fail server-side) in some illegal
   intermediate states. See `product-decisions-required.md` item 2.

3. **`complaints.customer_router`'s own authorization gap** remains open
   and out of scope for this slice, as instructed.

4. **Frontend lint not verified** — pre-existing environment/tooling gap
   (no ESLint v9 flat config), same as every prior slice; documented, not
   silently skipped.

5. **No new duplicate-proposal or cross-route interaction guard was added
   for `create_settlement_proposal`/`respond_to_settlement`** — these
   were reviewed only to confirm they are unreachable from the two target
   methods (see `alternate-caller-review.md`), not independently
   re-audited for their own state-machine completeness, which is outside
   this slice's 2-route scope.
