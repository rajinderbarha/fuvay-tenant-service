# Implementation Summary — Slice 2F-23

Discovery, verification and selection slice. **No application authorization
code was modified.**

## Baseline
**207/226 confirmed live** from the canonical CSV — 19 unprotected across 8
modules, matching the approved baseline and the expected module list exactly.

## What the 19 routes actually are

Runtime reverification of all 19 (all mounted, all genuine mutations) split
them into two populations:

| Live guard_status | Count | Meaning |
|---|---|---|
| `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` | 6 | dependency chain is `get_current_user` only — **no role or permission check at all** |
| `PERMISSION_ONLY_NOT_SCOPE_AWARE` | 13 | `require_technician`, which admits technician/staff/tenant_owner/super_admin with no access-scope awareness |

Six of these rows had been recorded in the canonical CSV as the vague
`UNVERIFIED`, which concealed that they have **zero authorization**.

## The decisive finding

`customer_reviews.provider_router.flag_review` has **no object-ownership
check whatsoever**:

```python
async def _get_review(self, db, review_id):
    r = await db.execute(select(CustomerReview).where(CustomerReview.id == review_id))
```

Filtered by primary key only. `flag_review` then writes
`review.status = STATUS_FLAGGED`. With a route dependency of bare
`get_current_user`, **any authenticated principal can flag any review in any
tenant** — a confirmed cross-tenant mutation on public reputation content.

Compounding factors:
- `submit_reply` has no role check, so a **customer** can post the official
  provider reply — logged as `ACTOR_PROVIDER`.
- `customer_router.flag_review`, a same-record alternate path, takes
  `tenant_id` **from the client body** (`CLIENT_TENANT_TRUSTED`).
- `submit_reply` already contains the correct ownership pattern
  (`review.tenant_id != tenant_id -> PERMISSION_DENIED`), so `flag_review`'s
  omission is a gap against an in-module precedent, not an unsolved design
  problem.

## Selection
**`app.engines.customer_reviews.provider_router`** — 2 mutations
(`submit_reply`, `flag_review`) for Slice 2F-24. It is the only module in the
queue with a confirmed cross-tenant mutation, needs no new role, permission
or migration, and has a proven fix template already in its own service.

## Corrections made

- **Six `UNVERIFIED` canonical rows corrected** to their runtime value
  (numerator provably unchanged: 207 before, 207 after).
- **The carried-forward queue understated this module** as MEDIUM severity
  and attributed the risk to `submit_reply` impersonation; the more serious
  defect is the `flag_review` cross-tenant IDOR the prior queue missed
  entirely.
- **Three WS6 risk hypotheses disproved by source** — marketing_automation
  has no bulk targeting/consent/dispatch/external send at all; media
  ownership is already enforced by the access-policy layer; profile fields
  cannot escalate role or tenant.

## Coverage
**207/226 unchanged.** Zero rows reclassified; zero already-protected, stale,
duplicate, false-positive, non-tenant or disconnected rows found.

## Tests
38 new deterministic tests, all passing — including five that assert the
selected module's defect against **live source**, so the finding cannot rot
silently before 2F-24 implements it.

## Final status
**`NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED`** — see `approval-gate.md`.
