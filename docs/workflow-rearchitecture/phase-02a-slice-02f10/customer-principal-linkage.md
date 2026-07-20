# Customer Principal Linkage — Slice 2F-10 (Workstream 5/6)

## Canonical dependency: `require_customer`
`app/dependencies/auth.py` — pre-existing, already used across
`customer_credits`, `compliance`, `profile`, and `media` customer
routers. Checks `user.role != "customer"` and fails closed with
`PERMISSION_DENIED` for any other value, including `undefined`/unknown
roles (unlike `isTenantOwnerRole`'s frontend loading-state convention,
this backend dependency has no such carve-out — it is a hard equality
check). Does **not** grant `super_admin` a wildcard override — confirmed
directly by `test_super_admin_not_wildcarded_through_customer_route`.
Platform administrators must use `complaints.admin_router`, which is
separately `require_super_admin`-gated (Slice 2F-9, unmodified).

## Principal → customer_id linkage
Every route derives the customer identity exclusively from
`UserContext.user_id` (the JWT-sourced principal), passed directly as
`customer_id` to the service layer. **No route schema
(`CreateComplaintIn`, `AddMessageIn`, `CancelComplaintIn`,
`ResolutionActionIn`, `CreateRefundIn`, `SettlementRespondIn`,
`AIAnswersIn`) contains a `customer_id` field at all** — confirmed by
direct read of every Pydantic model in `customer_router.py`. There is
therefore no request-body override path to reject in the first place;
the authenticated principal is unconditionally authoritative by
construction, not merely by convention.

## Missing customer-profile linkage
`get_current_user`/`require_customer` populate `UserContext` entirely
from JWT claims (no extra DB call) — there is no separate "customer
profile" record distinct from the authenticated user for this router;
`customer_id` IS `user_id`. A JWT for a disabled/deleted account is
already rejected upstream by the existing blacklist/session-revocation
check in `get_current_user` (unmodified, pre-existing, shared by every
router in the platform) — not a customer-router-specific concern.

## Error responses do not reveal foreign-complaint existence
`get_customer_complaint` raises the same `COMPLAINT_ACCESS_DENIED` for
"complaint belongs to someone else" as `_get_complaint` raises
`COMPLAINT_NOT_FOUND` for "complaint doesn't exist" — two distinct codes,
but neither discloses record contents, and Slice 2F-10's own
`_get_resolution` fix mirrors the stronger pattern (same
`RESOLUTION_NOT_FOUND` for both "doesn't exist" and "belongs to another
complaint") to avoid a foreign-resolution existence oracle. Verified
directly in `test_get_resolution_cross_check_directly`.
