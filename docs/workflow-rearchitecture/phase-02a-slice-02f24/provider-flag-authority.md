# Provider Flag Authority — Slice 2F-24

## The defect

This was the most serious finding in the module, and it had two independent
halves that combined into a cross-tenant write:

**Route half** — `POST /v1/provider/reviews/{review_id}/flag` was guarded by
bare `get_current_user`. No role check, no permission check, no scope check.

**Service half** — `flag_review` resolved the target with `_get_review`, a
primary-key-only lookup, and then performed **no ownership comparison of any
kind** before:

```python
if review.status != STATUS_FLAGGED:
    review.status = STATUS_FLAGGED
```

Net effect: **any authenticated principal could set any review in any tenant
to `flagged`** by supplying its id. A competitor could flag a rival's positive
reviews; a tenant could flag its own negative ones. The `ReviewFlag` row also
took its `tenant_id` from whatever the caller passed.

Notably, the sibling method `submit_reply` in the same class *did* compare
`review.tenant_id` — so this was a gap against an in-module precedent, not an
unsolved design question.

## The fix

| Control | After |
|---|---|
| Persona | `require_tenant_owner_mutation` — `tenant_owner` + `super_admin` only |
| Mutation scope | read-only `access_scope` denied |
| Ownership | central `_get_review_scoped(tenant_id=<JWT tenant>)` |
| Cross-tenant | SQL predicate; foreign row never loaded → `REVIEW_NOT_FOUND` |
| Flag tenant | `review.tenant_id` — never the caller's parameter |
| Actor type | server-set `"provider"`; validated against an allow-list in the service |
| Reason code | validated at the schema against the canonical `FLAG_REASONS` |
| Client fields | `extra="forbid"` — no tenant, actor, provider or status field accepted |

## Provider flagging does not confer moderation authority

Verified, not assumed: a provider flag sets `status = flagged` and opens a
`ReviewFlag`. It **cannot** reach `approved`, `rejected`, `hidden` or
`deleted` — those transitions exist only in `admin_router` under
`require_super_admin`. There is no code path by which a provider selects an
arbitrary status; the value is a constant in the service.

## Repeated flagging — explicit, not idempotent-by-design

Current behaviour, documented rather than redesigned:

- A second flag on an already-`flagged` review **creates another `ReviewFlag`
  row**; the `if review.status != STATUS_FLAGGED` guard means the review
  status itself is written only once.
- No rating aggregate is touched by flagging at all (see
  `review-rating-aggregate-integrity.md`), so repeated flags **cannot** move a
  provider's score.
- Multiple open flags on one review are therefore a moderation-queue
  duplication question, not an integrity defect.

Whether repeat flags should be deduplicated per (review, actor) is a product
decision — recorded, not invented.

## Flagging a final-state review

A `rejected` or `deleted` review can still be flagged. No established policy
in this codebase forbids it, and inventing one would be out of scope. It has
no aggregate or publication effect. Recorded as `PRODUCT_DECISION_REQUIRED` in
`review-idor-impersonation-test-matrix.csv` rather than silently blocked.

## Tests
`TestProviderFlagAuthority` (9) — including a cross-tenant rejection that also
asserts `db.add` and `db.commit` were never called, and an actor-type
allow-list test covering `admin`, `system`, `""`, `"PROVIDER"` and `"staff"`.
