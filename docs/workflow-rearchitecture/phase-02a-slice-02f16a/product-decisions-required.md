# Product Decisions Required

1. **`visit_charge`/`other` item types contribute zero to any total bucket.** `_recalculate` (unchanged, pre-existing, re-documented this slice in `customer-visible-monetary-contract.md`) only sums `labour`/`part`/`material`/`service`/`discount`/`tax` — an item with `item_type="visit_charge"` or `"other"` appears in the items list with a non-zero `line_total` but contributes nothing to `total_amount`. Whether this is intentional (these types are informational-only) or a genuine gap requiring a new bucket is a pricing-policy decision this slice has no authority to make (explicitly out of scope: "Do not introduce a new pricing policy").

2. **No distinct classification between "internal cost reference" and "internal margin."** `is_customer_visible` is a single boolean — the schema cannot distinguish WHY an item is hidden (raw cost data vs. margin padding vs. an internal-only line for bookkeeping). A future slice adding a typed classification would require a schema change (new column/enum), out of scope here.

3. **Quote expiry automation.** `QS_EXPIRED` exists in the state machine but no writer ever transitions a quote to it (confirmed, 2F-16 and re-confirmed this slice) — building an expiry job/scheduler is a product decision, not addressed.

4. **Discount-cap policy.** No maximum-discount enforcement exists (2F-16 finding, unaffected this slice) — whether a discount should be capped relative to other line items is a pricing-policy decision, not addressed.

5. **Quote versioning / offline customer decisions / PDF generation.** None built, all explicitly out of scope.

6. **Tenant-local customer directory.** Not built, consistent with every prior slice in this initiative.

7. **Optimistic concurrency/version fields on `ServiceJobQuote`.** No version column exists (2F-16 finding, `duplicate-concurrency-review.md`) — a genuine but low-severity concurrency characteristic shared with the rest of this codebase, not addressed this slice.

8. **Consolidation of `ServiceJobQuote` and `field_ops.JobQuote` into one model.** Explicitly out of scope — the two remain intentionally distinct pipelines.

9. **Idempotent-approval short-circuit does not re-reconcile the total from visible items on repeat.** By design (see `known-limitations.md`) — a product decision could require even the idempotent path to re-verify total consistency, at the cost of an extra query on every repeat-approval call. Not changed this slice; the original approval (non-idempotent branch) already correctly reconciles.
