# Slice 2F-23 Approval Gate

## Final status

**NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED**

Discovery, verification and selection slice. `SECURITY_CLOSED` is not claimed
and is not applicable — no authorization module was implemented.

## Coverage

**207 protected of 226 — UNCHANGED. 19 unprotected across 8 modules.**

- Numerator: 207 + 0 newly-protected − 0 incorrectly-counted = **207**
- Denominator: 226 + 0 − 0 − 0 − 0 − 0 = **226**

All 19 rows classified `GENUINE_UNPROTECTED_TENANT_MUTATION`. Zero stale,
duplicate, false-positive, non-tenant, disconnected or already-protected rows
found.

## Selected next module (Slice 2F-24)

**`app.engines.customer_reviews.provider_router`** — 2 mutations:
`POST /v1/provider/reviews/{review_id}/reply` (`submit_reply`) and
`POST /v1/provider/reviews/{review_id}/flag` (`flag_review`).

Selected because it is the **only module in the queue with a confirmed
cross-tenant mutation**. `_get_review` filters by primary key alone;
`flag_review` performs no ownership check and writes
`review.status = "flagged"`; the route dependency is bare
`get_current_user`. Any authenticated principal can therefore flag any review
in any tenant. `submit_reply` additionally lets a **customer** post the
official provider reply, logged as `ACTOR_PROVIDER`, and
`customer_router.flag_review` is a same-record alternate that takes
`tenant_id` from the client body.

Needs no new role, permission, migration or pipeline merge, and
`submit_reply` already contains the correct ownership pattern for
`flag_review` to copy.

## Findings that correct prior documentation

**Six canonical rows sat at `UNVERIFIED`** — concealing that six routes have
**no authorization check at all**. Corrected to their runtime value with the
numerator provably unmoved (207 → 207), per Workstream 1's prohibition on
leaving rows unverified.

**The carried-forward queue understated the selected module** as MEDIUM and
attributed its risk to `submit_reply` impersonation. The graver defect —
`flag_review`'s cross-tenant IDOR — was not in the prior queue at all. This
is the second consecutive slice where an inherited severity proved
understated on direct source reading.

**Three WS6 risk hypotheses are disproved by source** and were not preserved:
`marketing_automation` has no bulk targeting, consent model, dispatch or
external delivery of any kind; `media.new_router` ownership is already
enforced by the access-policy layer; `profile.router` cannot escalate role or
tenant through profile fields.

## Honest disclosure

A confirmed cross-tenant vulnerability is being **left open for one more
slice**. That is correct scope discipline for a discovery-only slice, but the
exposure is live in the meantime and is stated plainly in
`known-limitations.md` rather than softened. The finding is proven by source
inspection, not by an executed exploit — no database or live server exists in
this environment, and no stronger claim is made.

## Regression — exact node-ID comparison

| | BEFORE (2F-22) | AFTER (2F-23) |
|---|---|---|
| passed | 11108 | 11146 (+38 = exactly the new tests) |
| failed | 86 | 86 |
| errors | 111 | 111 |
| skipped | 14 | 14 |

**New failing node IDs: ZERO. Resolved: ZERO.** `comm` diff empty in both
directions. Failure identity — not keyword inference — establishes this.

## Preserved (re-confirmed)

field_ops 28/28 and 6/6; Booking, quote-checklist and invoice-lineage
closures; platform-notifications/chat-media closure; compliance provider
closure; **Package Commerce tenant purchase closure re-asserted by test**
(`require_tenant_owner_mutation` + `is_paid=False` still in place);
`PartsRequest` ServiceJob-only; `Booking`/`ServiceBooking` and
`field_ops.Job`/`ServiceJob` separate; canonical roles only;
`readonly@demo-ac-services.local` untouched; Migration 144 unapplied;
Slice-2D canaries untouched; historical 2F-19 and 2F-21 artifacts not
rewritten.

## Scope discipline

**No file under `app/` was modified.** No route dependency added, no service
authorization changed, no role/alias/permission added, no migration, no
pipeline merge, no frontend or visual work, no `My Work`/Next-Action, no
Booking Exception Resolution. Changes are limited to: one new test file, 25
documentation files, and a numerator-neutral precision correction to six
canonical CSV rows.

## Stop condition

This response stops at the Slice 2F-23 approval gate. Implementation of
`app.engines.customer_reviews.provider_router` has **not** begun and is
deferred to Slice 2F-24, per `selected-next-module.md`,
`selected-next-module-security-plan.csv` and
`selected-next-module-boundaries.md`.

## Forward annotation (added by Slice 2F-24)
Slice 2F-24 implemented the module selected here. **Every 2F-23 finding was
CONFIRMED against source** before being acted on: the primary-key-only
`_get_review`, the bare-authenticated `flag_review` with no ownership check
writing `status = flagged`, the customer-as-provider reply attributed as
ACTOR_PROVIDER, the client-supplied `tenant_id` on the customer flag route,
`CustomerReview` as the only in-scope model, and the legacy 410.

Coverage advanced **207/226 -> 209/226**, leaving 17 routes across 7 modules.

**One respect in which this slice understated the module's exposure:** 2F-23
did not identify that BOTH `GET /{review_id}` detail routes (provider and
customer) were also unscoped primary-key reads -- a cross-tenant read IDOR
exposing pending, hidden, rejected and deleted reviews together with their
moderation and rejection reasons. Found and closed in 2F-24. The selection
itself remains correct; the risk was larger than recorded.

This slice's five `TestSelectedModuleDefectIsReal` assertions -- written
deliberately so the finding could not rot before implementation -- fired when
2F-24 fixed the defect, exactly as designed. Rather than being deleted they
were **inverted**, so each now fails if the fix is ever reverted. The 2F-23
CSVs themselves were left untouched; the two now-protected routes are handled
by a narrow, slice-named exemption in the test.

The `-rE` error-node-ID baseline this slice captured made 2F-24 the first in
the initiative able to compare BOTH failures and errors at ID level: zero new
and zero resolved in each dimension.

Final status for 2F-24:
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`.
See `../phase-02a-slice-02f24/approval-gate.md`.
