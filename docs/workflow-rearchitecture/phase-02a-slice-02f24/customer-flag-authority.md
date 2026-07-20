# Customer Flag Authority — Slice 2F-24

`POST /v1/customer/reviews/{review_id}/flag` is a **same-record alternate**:
it writes the same `ReviewFlag` model and triggers the same
`CustomerReview.status = flagged` transition as the provider route. It is in
scope for that reason even though it sits outside the tenant/provider
coverage numerator.

## The defect

```python
tenant_id = uuid.UUID(str(body["tenant_id"])) if body.get("tenant_id") else None,
```

The client chose the tenant its moderation record was attributed to
(`CLIENT_TENANT_TRUSTED`). Combined with the service performing no ownership
check at all, this route was a second, equally effective path to flag **any
review in any tenant** — and it let a caller mis-attribute the resulting flag
record to an arbitrary tenant, corrupting moderation-queue data.

The route was also `get_current_user`, so it was not even restricted to
customers.

## The fix

| Control | After |
|---|---|
| Persona | `require_customer` — the narrowest existing dependency; `role != "customer"` denied |
| Client tenant authority | **removed** — `tenant_id` rejected by `extra="forbid"` |
| Flag tenant | derived from `review.tenant_id` |
| Ownership | `_get_review_scoped(customer_id=<JWT user_id>)` |
| Actor type | server-set `"customer"`; allow-list validated in the service |
| Reason code | `Literal[...]` against the canonical `FLAG_REASONS` |
| Privacy | foreign or missing review both → `REVIEW_NOT_FOUND` |

`tenant_id` is rejected rather than ignored, so a caller still sending it
learns the field carries no authority instead of believing it worked.

## Ownership policy: self-scoped — an adjudication, not an invention

The mission asks for "the exact customer/review relationship where policy
requires ownership" and warns against inventing policy. The position taken:

**A customer may flag only its own review.**

Rationale:
- `CustomerReview.customer_id` is `NOT NULL` and indexed — self-ownership is
  the one customer relationship this model can *prove*.
- There is no established policy anywhere in the engine granting a customer
  authority over another customer's review.
- Fail-closed is the correct default when policy is unresolved.

**This is deliberately narrower than the pre-slice behaviour**, which allowed
flagging any review. If the product intends customers to report *other*
people's public reviews (a common moderation pattern), that is a real product
decision requiring a defined relationship — recorded in
`product-decisions-required.md`, not decided here. The honest framing: this
slice chose the provably-safe subset, and the wider policy remains open.

## Boundaries preserved

- A customer **cannot** reach provider capability: `submit_reply` and the
  provider flag route both require `require_tenant_owner_mutation`.
- A customer **cannot** perform admin moderation: `approve`, `reject`,
  `hide`, `delete` and `resolve_flag` are all `require_super_admin`.
- A customer **cannot** select a review status: the value is a service
  constant.
- A `tenant_owner` cannot use the customer route — `require_customer` denies
  it, so the two personas stay distinct rather than overlapping.

## Coverage treatment

This route is **not** added to the tenant/provider numerator. It carries a
`/v1/customer/` prefix and is excluded from the tenant-only canonical CSV by
the Design A convention held since 2F-15C. It was corrected because it is a
proven same-record bypass — exactly the narrow exception the mission permits
for changes outside the selected module — and is reported separately in
`canonical-coverage-update.md`.

## Tests
`TestCustomerFlagAuthority` (6).
