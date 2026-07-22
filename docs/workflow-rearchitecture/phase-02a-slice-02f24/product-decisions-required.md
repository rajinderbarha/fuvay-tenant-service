# Product Decisions Required — Slice 2F-24

## 1. May `staff` reply to or flag reviews?
Currently denied — only `tenant_owner` (+`super_admin`). No existing
permission distinguishes a staff member authorised to speak in the business's
voice, and adding one is prohibited. Started narrow deliberately: widening
later is trivial, narrowing after release is not. This is the single most
likely refinement.

## 2. May a customer flag someone else's review?
This slice scoped customer flagging to the customer's **own** review, because
`CustomerReview.customer_id` is the only customer relationship the model can
prove. Pre-slice behaviour was "any review", which was unbounded rather than
intentional. If the product wants public-review reporting (a common moderation
pattern), it needs a defined relationship and abuse controls. **Deliberately
not invented.**

## 3. Should repeat flags be deduplicated?
A second flag on an already-flagged review creates another `ReviewFlag` row;
the review status is written only once and no aggregate moves. Whether to
enforce one open flag per (review, actor) is a moderation-queue design
decision.

## 4. May a final-state review be flagged?
`rejected` and `deleted` reviews can still be flagged. No established policy
forbids it and it has no aggregate or publication effect. Recorded as
`PRODUCT_DECISION_REQUIRED` rather than silently blocked.

## 5. Provider reply editing
No edit or delete route exists for a provider reply; one reply per review is
enforced. Whether providers may edit within a window is undecided. Multi-reply
semantics were explicitly not invented.

## 6. Flag reason taxonomy
`spam | fake | offensive | irrelevant | other` is now enforced at the schema
(previously any value was silently coerced to `other`). Whether the taxonomy
is right is a product question.

## 7. Legacy review engine
`app.engines.review` has the same unguarded flag pattern on the separate
`reviews` table — and, per the caller audit, **live frontend callers in
tenant-portal and super-admin**. Retiring it, protecting it, or migrating
those callers is a product/architecture decision.

## 8. Moderation SLA, appeals, automated moderation, retention
None exist. None invented, per the explicit prohibition.

## Carried forward, unchanged
Package Commerce payment integration and duplicate-pending index (2F-22);
compliance export worker and dedup (2F-20); the `tenant-readonly-decision.md`
conclusion behind the two Slice-2D canaries.
