# Decision 2 — Review Subsystem

## customer_reviews (canonical, per this decision)

| Aspect | Detail | Verification |
|---|---|---|
| Create endpoint | `customer_reviews/customer_router.py` (`/v1/customer/reviews`) | SOURCE_VERIFIED |
| Read endpoints | `/v1/customer/reviews`, `/v1/provider/reviews`, `/v1/public/reviews`, `/v1/admin/reviews` (+4 admin sub-routers) | SOURCE_VERIFIED |
| Database table | `customer_reviews` (+ `review_replies`, `review_flags`, `review_events`, `tenant_rating_summaries`, `staff_rating_summaries`, `review_policies`) | SOURCE_VERIFIED |
| Job foreign key | Linked to `ServiceJob`/booking completion (this is what `home_service_assignment/customer_router.py` was fixed to write to per L5-13, replacing the orphaned legacy table) | RUNTIME_VERIFIED |
| Customer permission | `require_customer` + `CustomerScopeService` | SOURCE_VERIFIED |
| Provider visibility | `/v1/provider/reviews` | SOURCE_VERIFIED |
| Admin visibility | `/v1/admin/reviews` + moderation sub-routers | SOURCE_VERIFIED |
| Moderation | Flag/resolve endpoints exist (`review_flags`) | SOURCE_VERIFIED |
| Rating aggregation | `tenant_rating_summaries`, `staff_rating_summaries` | SOURCE_VERIFIED |
| Frontend usage | tenant-portal `/reviews`, `/provider/reviews`; mobile-customer review submission post-completion | SOURCE_VERIFIED |
| Downstream consumers | `trust_quality` engine health scoring likely reads rating summaries (SOURCE_INFERRED — not independently re-traced this pass) | SOURCE_INFERRED |

## review (legacy)

| Aspect | Detail | Verification |
|---|---|---|
| Create endpoint | `review/router.py` (`/v1/reviews`) — still fully mounted and reachable, not disabled | SOURCE_VERIFIED |
| Read endpoints | `/v1/reviews` list/aggregate | SOURCE_VERIFIED |
| Database table | `reviews` (+ `review_requests`, `review_aggregates`, `review_status_history`) — explicitly called "orphaned" in code comments (L5-13) | SOURCE_VERIFIED |
| Job foreign key | Was the original target before L5-13 repointed job-completion ratings to `customer_reviews`; no confirmed active writer remains, but the endpoint itself still accepts POST | SOURCE_VERIFIED (mounted) / UNVERIFIED (whether any current frontend still calls it) |
| Frontend usage | The one page confirmed touching reviews in admin (`/admin/reviews`) has an unconfirmed target — could be pointing at either stack | UNVERIFIED — this is the single open item for full closure |
| Tests | Not investigated this pass | UNVERIFIED |
| Downstream consumers | None confirmed reading from `reviews` post-L5-13 | SOURCE_INFERRED |

## Verification pass results (confirms Phase 1 hope, closes the open item)
1. `frontend/super-admin/app/admin/reviews/page.tsx` imports and calls **only** `adminReviewApi`, which maps to `/v1/admin/reviews*` (customer_reviews canonical) — file:line confirmed at `lib/api.ts:6456-6475`. The legacy `reviewApi` object (`/v1/reviews*`, `lib/api.ts:2327-2338`) exists in the same file but **is not imported or used** by the reviews page. **The ambiguity flagged in Phase 1 is resolved: the admin reviews page already reads the canonical stack. No frontend fix is required.**
2. `app/engines/review/router.py:27` has a live, working `POST /v1/reviews` create endpoint that still writes to the legacy `reviews` table — this is not merely a read/moderation-only surface. However, a grep across all 4 frontend/mobile codebases found **no caller** of `POST /v1/reviews` anywhere. The endpoint is live but orphaned from any real user journey today.

## Decision
**customer_reviews is confirmed canonical, and is already what the frontend uses.** Per approved product direction #3/#4, the legacy `review` engine must not remain a parallel writable workflow — and since no frontend depends on its write path, blocking it carries no discovered frontend risk.

## Retirement plan
1. **Reads:** may remain temporarily for historical data (any reviews written to the legacy table before L5-13 shouldn't simply vanish) — expose as a read-only compatibility view if any pre-L5-13 rows exist, otherwise remove.
2. **Writes:** block `POST /v1/reviews` (410 or route removal) at the API layer — confirmed zero frontend callers across all 4 audited codebases, so this carries no frontend-facing risk. This is a backend-only change, listed in `backend-blockers.md`.
3. **Data migration:** if any legacy `reviews` rows exist without a `customer_reviews` counterpart, a one-time migration/backfill should be evaluated — backend decision, outside Phase 2 frontend scope.
4. **Frontend calls to change:** none — already confirmed correct.
5. **Route aliases:** none required.
6. **Regression tests required:** confirm blocking `POST /v1/reviews` does not break anything (expected: no impact, since no caller exists) and that `/admin/reviews` continues functioning unchanged.

## Decision status
**CLOSED.** Both the canonical subsystem (customer_reviews) and the one open verification item (admin reviews page target) are now confirmed. No Phase 2 frontend work is required for this decision beyond normal regression testing after the backend write-block ships.
