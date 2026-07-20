# Product Decisions Required — Slice 2F-9B

Only 1 open item remains from the complaint-provider-response/resolution
problem area (carried over, not created by this slice):

1. **Should `provider_add_response` also block on `resolved`/`settled`,
   not just base `FINAL_STATUSES`?** Unchanged from Slice 2F-9A's item 1.
   Not decided, not changed. This slice did not touch
   `provider_add_response`, `FINAL_STATUSES`, or the Reply control's
   frontend gate.

2. **`complaints.customer_router`'s own authorization gap** — remains the
   most consequential open item in this problem area; explicitly out of
   scope for this slice.

No new product-policy question was introduced by this slice. The item
Slice 2F-9A had classified as `PRODUCT_DECISION_REQUIRED` (exact frontend
resolution-state gating) was, on reflection, not actually a product
question — it required no new decision, only precise derivation from
already-approved backend policy — and is resolved as of this slice (see
`documentation-corrections.md`).
