# Actor Attribution Integrity — Slice 2F-24

## Field inventory and classification

| Field | Model | Source | Classification |
|---|---|---|---|
| `replied_by_user_id` | `ReviewReply` | `user.user_id` (JWT) | `PRINCIPAL_DERIVED` |
| `flagged_by_user_id` | `ReviewFlag` | `user.user_id` (JWT) | `PRINCIPAL_DERIVED` |
| `flagged_by_type` | `ReviewFlag` | route constant, allow-list validated | `PRINCIPAL_DERIVED` |
| `ReviewFlag.tenant_id` | `ReviewFlag` | **`review.tenant_id`** (was client body) | `REVIEW_DERIVED` |
| `ReviewReply.tenant_id` | `ReviewReply` | JWT tenant, ownership-verified against the review | `PRINCIPAL_DERIVED` |
| `CustomerReview.customer_id` | `CustomerReview` | `user.user_id` at submit | `PRINCIPAL_DERIVED` |
| `CustomerReview.tenant_id` | `CustomerReview` | client body at submit, eligibility-gated | `CLIENT_SUPPLIED_VALIDATED` (pre-existing, see note) |
| `ReviewEvent.actor_type` / `actor_id` | `ReviewEvent` | service constants + principal | `PRINCIPAL_DERIVED` |
| `moderated_by` / `resolved_by` (admin) | admin paths | `require_super_admin` principal | `PRINCIPAL_DERIVED` |

**No client-supplied actor field is accepted on any route in scope.** All four
request schemas use `extra="forbid"`, so `actor_type`, `flagged_by_type`,
`replied_by_user_id`, `provider_id` and `tenant_id` are rejected with 422
rather than silently dropped.

## The impersonation defect and its closure

Before this slice, `ACTOR_PROVIDER` was hardcoded on the reply path while the
route admitted **any** authenticated principal. A customer's reply was
therefore recorded in `ReviewEvent` as a provider action — the audit trail
asserted something false about who spoke for the business.

Hardcoding the actor type was never the bug; it is the correct pattern. The
bug was that the route did not guarantee the principal matched the constant.
With `require_tenant_owner_mutation` in place, `ACTOR_PROVIDER` is now
truthful by construction.

## Defence in depth at the service layer

A router guard alone would leave the reusable service method able to write any
attribution a future caller passed. `flag_review` now validates:

```python
if flagged_by_type not in (ACTOR_PROVIDER, ACTOR_CUSTOMER):
    raise ValueError(ERR_PERMISSION_DENIED)
```

so `"admin"`, `"system"`, `""`, `"PROVIDER"` (case), `"staff"` and any other
value fail closed **before** the ownership lookup and before any write.
Notably `ACTOR_ADMIN` is refused on this method: a provider or customer action
can never be recorded as a platform-admin one, which is the escalation
direction that matters.

## Requirements check

| Requirement | Status |
|---|---|
| Customer actions cannot be recorded as provider actions | MET — persona guard + server-set type |
| Provider actions cannot be recorded as platform-admin actions | MET — `ACTOR_ADMIN` rejected by the allow-list |
| Super-admin behaviour explicit | MET — admitted by the shared dependency; admin moderation is a separate router with its own actor constants |
| Actor identity survives service-layer calls | MET — passed as explicit parameters, never re-derived or defaulted |
| Audit events record the real actor | MET — `_log_event` receives the principal id and the validated type |
| Client-supplied actor fields rejected | MET — `extra="forbid"` on all four schemas |
| Unknown actor type fails closed | MET — allow-list, tested against five bogus values |

## Note on `CustomerReview.tenant_id` at submit time

The customer review-creation route still takes `tenant_id` from the body. This
is **pre-existing and out of this slice's scope** (that route is
`CUSTOMER_REVIEW_CREATE`, not a reply/flag/moderation capability). It is
gated by `ReviewEligibilityService`, which verifies the customer actually has
a completed record with that tenant, so it is `CLIENT_SUPPLIED_VALIDATED`
rather than trusted. Flagged in `known-limitations.md` as unverified-by-this-
slice rather than cleared.

## Tests
Actor assertions across `TestProviderReplyAuthority`,
`TestProviderFlagAuthority` and `TestCustomerFlagAuthority`, plus
`test_unknown_actor_type_fails_closed`.
