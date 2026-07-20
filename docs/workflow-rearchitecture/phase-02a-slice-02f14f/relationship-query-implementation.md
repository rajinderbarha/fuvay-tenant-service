# Relationship Query Implementation

## Helper: `FieldOpsService._assert_tenant_customer_relationship`

- **Accepts**: `tenant_id: uuid.UUID`, `customer_id: uuid.UUID` (uses `self.db`, the existing
  session — no new parameter for db/session since it's an instance method, matching every other
  helper in this service, e.g. `_get_job_for_assignment`).
- **Queries only existing tables**: `Booking` (via `select(Booking.id)...`) and `field_ops.Job`
  (via `select(Job.id)...`) — no new model, no new migration.
- **Applies the ratified relationship-status policy**: no status filter (any row counts, see
  tenant-customer-relationship-contract.md).
- **Returns without mutation** when a relationship exists (no side effect, pure read).
- **Raises a stable domain error** (`CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`, 422) when neither
  query finds a match.
- **Avoids leaking which other tenant knows the customer**: the query is scoped entirely to
  `tenant_id == principal tenant` — a customer known to a different tenant produces the exact
  same "no match" result as a customer known to no tenant at all; no other tenant's ID, Booking,
  or Job details are ever read or returned.
- **Performs no writes**: confirmed — only `select()` statements, no `db.add`/`db.flush`.
- **Reused only where appropriate**: called from exactly one call site in `create_job` (the
  standalone-manual-mode branch) — not applied to booking-referenced or parent-derived modes,
  which already prove the relationship through their own existing cross-checks.

## Naming

`_assert_tenant_customer_relationship` follows this codebase's existing convention for
assertion-style private helpers that raise on failure and return `None` on success (e.g.
`_assert_assigned`, `_assert_can_access_job`).
