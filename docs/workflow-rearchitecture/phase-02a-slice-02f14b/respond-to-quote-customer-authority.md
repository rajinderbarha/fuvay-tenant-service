# respond_to_quote Customer Identity — Disposition

## Disposition: was CUSTOMER_IMPERSONATION_DEFECT — now CUSTOMER_SELF_DECISION

## Before this slice

```python
customer_id = uuid.UUID(u.user_id) if u.role == "customer" else uuid.UUID(body["customer_id"])
```

Any non-customer authenticated caller (`staff`, `tenant_owner`, `technician` — anyone passing
`get_current_user`) could supply an arbitrary `customer_id` in the request body. The service
method (`respond_to_quote`) has no way to distinguish this from a genuine customer request — it
records the exact same `quote.status = "approved"/"rejected"` and `quote.responded_at`, with no
actor-type field anywhere recording that the "decision" was actually made by a provider on the
customer's behalf. No offline-decision audit trail, no separate endpoint, no product
documentation, and no test anywhere established this as an intentional workflow.

Per the mission's explicit instruction ("Absence of a canonical customer caller is not evidence
that provider impersonation is acceptable"), this is a confirmed **CUSTOMER_IMPERSONATION_DEFECT**,
not a `PRODUCT_DECISION_REQUIRED` or `TRUSTED_INTERNAL_CALLBACK`.

## Fix

The route now requires `require_customer` (canonical customer role only); `customer_id` is always
`uuid.UUID(u.user_id)`, never read from the request body.

## Directly tested

- Correct customer, own quote: succeeds (`test_correct_customer_can_respond`).
- Foreign customer: denied, 404, quote unchanged (`test_foreign_customer_denied`).
- Repeated response: denied, 409 `CONFLICT` (`test_repeated_response_rejected`).
- Foreign/nonexistent quote ID: 404 (`test_foreign_quote_id_rejected`).
- Same-tenant/cross-tenant provider actor, technician, guest, unauthenticated: all now denied at
  the router by `require_customer` before the service is ever reached (source-verified via
  `test_respond_to_quote_uses_require_customer`, which also asserts the old
  `body["customer_id"]` substitution pattern no longer appears in source).
- Request `customer_id` substitution: no longer possible — the parameter is not read from the
  body at all.

## Audit/notification

`_write_history` records `changed_by_role`/`reason` on the Job's status history — since the
route now only ever executes as the real customer, this accurately reflects the actor. No change
was needed to the audit/notification path itself.
