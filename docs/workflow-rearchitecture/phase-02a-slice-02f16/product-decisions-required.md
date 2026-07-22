# Product Decisions Required

1. **Quote expiry is designed but unimplemented.** `QS_EXPIRED` exists in the state machine and `QUOTE_FINAL_STATUSES`, and `sent_to_customer → expired` is a legal transition — but no writer (scheduled job, cron, or manual action) ever performs it. Whether this should be a time-based automatic expiry (requiring a background worker, out of scope this slice) or a manual provider action (a new route, also out of scope) is a product decision.

2. **No maximum-discount cap.** A discount line item can reduce a quote's total to zero or below the sum of other items. Whether a business rule should cap discount as a percentage of subtotal is a pricing-policy decision this slice has no authority to make (explicitly out of scope: "Do not create new pricing policy").

3. **`QUOTE_NOT_FOUND` vs `QUOTE_ACCESS_DENIED` are distinguishable error codes**, unlike the single-uniform-error pattern established in the Booking slices. Whether to unify these (trading existing frontend error-handling compatibility for a marginally stronger privacy property) is a product/API-contract decision, not fixed this slice.

4. **Checklist completion has no Job-status side effect.** Unlike quote actions (which sync `ServiceJob.status`), `complete_checklist` does not change any Job-level field. Whether this is intentional (checklists are informational/quality-gate only) or a genuine gap is a product question — not resolved, not guessed at, this slice.

5. **No optimistic-concurrency versioning on quote totals.** Two staff members concurrently editing the same quote's items could race (last-write-wins on the recalculated total). Whether to add a version column (requiring a migration, out of scope) is a future product/engineering decision.

6. **Consolidation of `field_ops.JobQuote` and `quote_checklist.ServiceJobQuote`** into a single quote system remains a product question this slice explicitly did not investigate resolving (would require a pipeline merge, out of scope; the mission explicitly instructs not to reopen field_ops for this reason).
