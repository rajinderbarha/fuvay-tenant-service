# Product Decisions Required - Slice 2F-31

**None block the 7 closed Set A routes.**

Two items block full N01 closure, both requiring a scope/contract decision
rather than a product decision per se:

1. `POST /v1/media/upload` and `POST /v1/media/{media_id}/replace` need a
   scope-only guard usable by a mixed customer/staff persona. This requires
   `app/core/permissions.py`, forbidden by the frozen contract. A future slice
   should either add this guard as its own scoped implementation task, or the
   contract should explicitly widen the allow-list for it.

2. All 3 Set B routes need remediation in `app/engines/media/router.py` /
   `MediaService`, neither of which is on the allow-list. A future slice
   targeting this router directly is required; it should not be folded into a
   "N01 part 2" without a fresh scope freeze, per the frozen-scope discipline
   this program has followed throughout.

Non-blocking, carried from 2F-30: whether provider logo/shop-photo deletion
should be tenant_owner-only or delegable - **resolved implicitly** by keeping
`require_staff_or_above_mutation`, which preserves the existing delegable
policy rather than narrowing it. If the product intends tenant_owner-only,
that is a future, separate decision.
