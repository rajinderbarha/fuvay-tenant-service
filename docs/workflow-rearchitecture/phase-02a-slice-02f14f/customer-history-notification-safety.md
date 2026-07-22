# Customer History and Notification Safety

## Traced success effects of create_job

Job creation, `JobStatusHistory` (one row), a `structlog` catalog-lookup warning (best-effort,
non-fatal), usage-quota increment (best-effort), Redis customer-token caching (best-effort), and
the `job.created` domain event (`self._publish`). No email/SMS/push notification is fired
directly by `create_job` (unchanged from Slice 2F-14D's own findings). No customer-dashboard
read path or search/list exposure is affected by `create_job` itself (those are separate, later
read routes, already tenant/customer-isolated via `_assert_can_access_job`, unmodified).

## Verified for an unrelated-customer rejection

- **No Job exists**: `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` raises before `Job(...)` is ever
  constructed (verified: `test_completely_unrelated_customer_rejected`,
  `db.add.assert_not_called()`).
- **No customer Job history changed**: no Job row exists to have history.
- **No JobStatusHistory exists**: `_write_history` is only called after `db.add`/`db.flush`,
  never reached.
- **No audit success event**: same reasoning.
- **No domain success event published**: `self._publish("job.created", ...)` is only called
  after successful persistence, never reached.
- **No notification emitted**: none exists to begin with (see above); a fortiori, none fires on
  rejection.
- **No customer dashboard record appears**: no Job row exists.
- **No provider sees customer details beyond what the request already contained**: the
  relationship check only returns a boolean (existence), never the customer's other Booking/Job
  content, other tenant's identity, or any additional field.
- **No other-tenant relationship is disclosed**: confirmed — the query is tenant-scoped; a "no
  relationship" result is identical whether the customer is known to zero tenants or to a
  different tenant only.

## Rollback safety

No event publication occurs before `db.flush()` (which durably assigns `job.id` within the
current transaction) — unchanged, pre-existing ordering, re-verified this slice (see
transactional-consistency.md, Slice 2F-14D).
