# Selected Module Boundaries — Slice 2F-24

## In scope

- The 2 canonical mutations: `submit_reply`, `flag_review` in
  `app.engines.customer_reviews.provider_router`.
- The 4 related GET reads in the same router (read-privacy audit only).
- `ReviewService.submit_reply`, `ReviewService.flag_review`, and
  `ReviewService._get_review` — the service-layer ownership gap is the core
  defect and cannot be closed at the router alone.
- **`customer_router.flag_review`** — a same-record alternate path that
  currently accepts `tenant_id` from the client body. It writes the same
  `ReviewFlag` model and triggers the same `review.status` mutation, so
  closing the provider route without it would leave the bypass open. This is
  the "smallest safe correction outside the selected router" permitted for a
  proven same-record bypass.

## Explicitly OUT of scope for 2F-24

- `admin_router.py` review routes (`approve_reply`, `reject_reply`,
  `resolve_flag`) — already `require_super_admin`; audit only.
- `public_router.py` review reads — public by design.
- `customer_router.submit_review` / `edit_review` — the customer authoring
  surface is a different capability; only the `flag_review` alternate is in
  scope.
- The review aggregation/rating recomputation pipeline.
- Notification behaviour (`notify_customer_review_reply`) beyond confirming
  it fires only after successful persistence.
- Any moderation-policy change (`require_reply_moderation`).
- Any new role, permission, or migration.
- Rating recalculation, review eligibility, or the complaints engine.

## Boundaries that must hold

- No new role or permission — `require_tenant_owner_mutation` is the
  intended drop-in.
- No migration.
- No change to `ReviewFlag` / `CustomerReview` schema.
- No frontend work.
- Do not merge the customer and provider flag capabilities into one route —
  they are legitimately distinct personas writing the same record with
  different authority.
- Preserve the existing correct behaviours: the `submit_reply` tenant check,
  the one-reply-per-review guard, `ACTOR_PROVIDER` / `flagged_by_type`
  being server-set rather than client-supplied.

## Known trap for the implementer

`flag_review` currently accepts `tenant_id=None` (the customer path passes
`None` when the body omits it) and writes it straight onto `ReviewFlag`.
Adding an ownership check must not simply trust the passed `tenant_id` —
that value is client-controlled on one of the two call paths. Ownership must
be derived from the authenticated principal and compared against
`review.tenant_id`, in the same shape `submit_reply` already uses.
