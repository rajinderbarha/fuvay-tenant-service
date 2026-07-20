# Customer Quote Decision Authorization

## Before this slice
`customer_router.py`'s 6 routes used `Depends(get_current_user)` with no explicit role check. Customer identity was already correctly server-derived — `customer_approve`/`customer_reject`/`customer_request_revision` all receive `str(user.user_id)` as the `customer_id` parameter directly from the router (never a client-suppliable field), and each service method independently verifies `str(q.customer_id) != customer_id` before proceeding, raising `QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED` on mismatch.

This made **cross-customer impersonation impractical** (a tenant_owner's own `user.user_id` will essentially never equal a real customer's `quote.customer_id`), but did not make the **canonical customer persona explicit** at the router level, and left `get_quote`/`list_quote_events` with **no ownership filter at all** (any authenticated user, of any role, could fetch full quote detail by ID — see `quote-job-item-ownership.md`).

## The fix
All 6 customer routes now use `Depends(require_customer)` (existing dependency, no new role). `get_quote`/`list_quote_events` now additionally receive `customer_id=str(user.user_id)` and enforce it inside the service layer.

## Provider cannot fabricate customer approval
No code path in `customer_approve`/`customer_reject`/`customer_request_revision` accepts an `actor_type` or `customer_id` override from the request body — the customer identity is 100% derived from the authenticated `UserContext`. A provider account cannot reach these routes at all now (`require_customer` denies non-customer roles), and even before this fix, could not have impersonated a *specific* customer (their own `user.user_id` would never match). No explicit, independently-proven "offline decision" policy exists anywhere in this codebase (searched: no admin-side "record customer decision on their behalf" route exists) — so there is no sanctioned provider-side approval-recording capability, consistent with the mission's requirement.

## Technician cannot approve on the customer's behalf
`require_customer` excludes technician entirely — same denial as any other non-customer role.

## Legal quote state enforced
`_assert_transition(q, QS_CUSTOMER_APPROVED)` (and the `_REJECTED`/`_REVISION_REQUESTED` equivalents) reads `QUOTE_TRANSITIONS[q.status]` — only `sent_to_customer` legally transitions to any of the three customer-decision outcomes (unchanged, pre-existing, re-verified via full regression).

## No tenant mutation scope required
`require_customer` has no `access_scope` concept at all (customers don't carry one) — customer decision authorization is completely independent of `require_tenant_mutation_permission`/`require_owner_or_office_staff_mutation`'s access-scope machinery, consistent with the established pattern from the Booking slices (2F-15 series).

## Uniform privacy-safe errors
`QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED` (foreign customer) and `QUOTE_ACCESS_DENIED` (wrong tenant/customer on read) are both used regardless of whether the quote doesn't exist, belongs to a different customer, or belongs to a different tenant — no case discloses which condition applied.

## Audit actor accuracy
Every customer-decision event write (`_log_event(..., "customer", user_id, ...)`) uses `user_id=str(user.user_id)` from the customer router — server-derived, never client-suppliable, unchanged from before this slice.
