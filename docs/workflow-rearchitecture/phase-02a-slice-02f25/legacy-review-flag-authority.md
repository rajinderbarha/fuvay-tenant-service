# Legacy Flag Authority — Slice 2F-25

## The defect

Two independent halves, the same shape as the canonical engine's:

- **Route:** bare `get_current_user` — no role, no permission, no scope.
- **Service:** `select(Review).where(Review.id == review_id)` then
  `rv.status = ReviewStatus.FLAGGED` with **no ownership comparison**.

Any authenticated principal could flag any review in any tenant.

## The fix

| Control | After |
|---|---|
| Persona | `require_tenant_mutation_permission(P.TENANT_UPDATE)` |
| Mutation scope | read-only tenant users denied (the scope-aware variant) |
| Ownership | `_get_review_scoped` — SQL predicate on `tenant_id` |
| Actor | `flagged_by = self.actor_id`, server-derived (unchanged) |
| Status | a service constant; the client cannot choose it |
| Cross-tenant | `NotFound`, foreign row never loaded |

## Repeated flagging — explicit, and already correct
```
if rv.status == ReviewStatus.FLAGGED:
    raise ServiceOSException("CONFLICT", "Review is already flagged.")
```
Idempotency is enforced by an explicit conflict, raised **before** any write.
This is stricter than the canonical engine, which permits duplicate flag rows.

## Provider flagging confers no moderation authority
`resolve_flag` — the only transition out of `flagged`, and the only path that
sets `published`/`removed` — is `require_super_admin`. A tenant principal
cannot reach it. Verified, not assumed.

## Aggregate effect
Flagging writes `status`, `flagged_reason`, `flagged_by` and a
`ReviewStatusHistory` row. Aggregate recomputation happens on
publish/remove transitions, not on flag. See
`legacy-review-aggregate-integrity.md`.

## Tests
`TestMutationAuthority` (8) including a cross-tenant flag that asserts
`db.add` and `db.commit` were never called.
