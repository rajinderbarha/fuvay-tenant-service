# Legacy Read Privacy — Slice 2F-25

## The exposure

Six of the ten legacy reads were cross-tenant:

| Read | Before |
|---|---|
| `GET /v1/reviews?tenant_id=` | query value used verbatim — **any tenant enumerable** |
| `GET /v1/reviews/staff/{id}?tenant_id=` | same |
| `GET /v1/reviews/tenants/{tenant_id}/requests` | path value used verbatim |
| `GET /v1/reviews/tenants/{tenant_id}/recent` | path value used verbatim |
| `GET /v1/reviews/{review_id}` | primary-key only; `_assert_owns` guards customers ONLY |
| `GET /v1/reviews/requests?tenant_id=` | query value used verbatim |

A `tenant_owner`, `staff` or `technician` of tenant A could read tenant B's
reviews, including `flagged_reason`, `resolved_by` and reply content, simply
by changing one parameter.

## After

- The four list routes resolve their tenant through `_effective_tenant`, so a
  mismatching client value is refused and an omitted one falls back to the
  principal.
- The detail route resolves through `_get_review_scoped`, so it is tenant
  scoped first and customer-guarded second.
- Foreign and missing ids are privacy-equivalent (`NotFound`).
- No GET route mutates — confirmed by reading every handler body.

## Reads deliberately NOT changed, and why

| Read | Reason |
|---|---|
| `GET /v1/reviews/customers/{customer_id}` | guarded by `_assert_owns`, which is correct for the customer persona. A non-customer role still passes it — recorded in `known-limitations.md` as an accepted residual, since the route's persona is customer-self-service and tightening it further would need a product decision about tenant access to customer review history. |
| `GET /v1/reviews/aggregates/{entity_type}/{entity_id}` | pre-computed aggregate keyed by an opaque entity id; exposes counts/averages, not review content. Residual, recorded. |
| `GET /v1/reviews/requests/jobs/{job_id}` | keyed by job id; returns request status only, no review content. Residual, recorded. |
| `GET /v1/reviews/meta` | static engine metadata. |

These three are stated as **unclosed residuals with reasons**, not claimed as
protected. That is why privacy closure is asserted for the review-content
surface specifically and the residuals are disclosed in the approval gate.

## Tests
`TestReadPrivacy` (3), plus the `_effective_tenant` parametrised test covering
all five tenant-taking methods.
