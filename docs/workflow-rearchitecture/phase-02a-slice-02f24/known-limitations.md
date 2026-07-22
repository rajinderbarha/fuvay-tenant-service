# Known Limitations — Slice 2F-24

1. **No live database or HTTP server.** All 46 new tests are deterministic
   source, schema, signature and session-double assertions. The cross-tenant
   fix is proven by the SQL predicate being present and by denial paths
   writing nothing — **not** by an executed end-to-end request. Stated as an
   environment exclusion, not claimed as live verification.

2. **The legacy review engine remains unguarded on its own table.**
   `app.engines.review.flag_review` uses the same primary-key-only pattern
   behind bare `get_current_user`. It is `DISTINCT_MODEL` (table `reviews`),
   so outside this slice's permitted change boundary — but the caller audit
   found **live frontend callers in two applications**, which makes it a
   more live concern than an orphaned-legacy framing would suggest. Not fixed;
   flagged for a future slice.

3. **`CustomerReview.tenant_id` at submit time is still client-supplied.**
   The customer review-creation route takes `tenant_id` from the body, gated
   by `ReviewEligibilityService`. That route is `CUSTOMER_REVIEW_CREATE`, not
   a reply/flag/moderation capability, so it was inventoried but not
   re-verified in depth. Classified `CLIENT_SUPPLIED_VALIDATED`, not cleared.

4. **Read-only UI gating not audited.** The backend denies read-only
   `access_scope`, which is the load-bearing control, but whether the
   customer-app hides mutation controls for such users was not inspected.

5. **`edit_review` mutates the ORM object before validating the rating.**
   Fields are assigned, then `overall_rating` bounds are checked. The raise
   precedes `flush`, so nothing persists, but the ordering is fragile. Not in
   scope (customer edit is not a selected route and no bypass was proven);
   recorded rather than silently fixed.

6. **Flagging a final-state review is permitted** — see
   `product-decisions-required.md` #4.

7. **Repeat flags create duplicate open flag rows** — no integrity impact
   (no aggregate effect), but a moderation-queue duplication.

8. **`ReviewFlag.tenant_id` remains nullable** at the schema level. It is now
   always written from `review.tenant_id`, so no new null can be introduced by
   these paths, but historical rows may carry null or a client-chosen value.
   Backfilling would require a migration — prohibited.

9. **Two stale Slice-2D canaries still failing**, deliberately untouched.

10. **`mutation-enforcement-matrix.csv` remains stale**, per the standing
    convention.
