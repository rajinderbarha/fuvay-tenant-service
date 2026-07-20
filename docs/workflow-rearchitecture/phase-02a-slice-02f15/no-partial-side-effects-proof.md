# No Partial Side Effects Proof

## Ordering

Both new checks (customer existence/state validation, and the relationship-requirement check)
execute in `create_booking` **before** any `Booking(...)` row is constructed:

1. Customer validation (if `actor_role != "customer"`) — immediately after the
   `address_id`/`service_id`/`job_type` required-fields check, BEFORE any serviceability/pricing
   work begins (fail-fast, avoids wasted downstream calls for an invalid identifier).
2. Serviceability re-match (unchanged, resolves `tenant_id`).
3. Relationship requirement (if `actor_role != "customer"`) — immediately after `tenant_id` is
   resolved, BEFORE idempotency-key lookup, pricing, or legacy preflight.
4. `Booking(...)` construction and `self.db.add(booking)`.

## Proven for every rejected case

- **No Booking**: `db.add.assert_not_called()` — explicit in `test_foreign_customer_rejected`,
  `test_wrong_role_account_rejected`, `test_bootstrap_attack_no_relationship_rejected`.
- **No Booking status mutation / no BookingStatusHistory success row**: `_write_history` is only
  called after `self.db.add(booking)` succeeds — never reached on any rejection.
- **No assignment**: not applicable — `create_booking` never creates an assignment.
- **No Job conversion**: not applicable — conversion is a separate, later call
  (`convert_to_job`), never reached.
- **No field_ops relationship evidence**: since no Booking is created, `_assert_tenant_customer_relationship`
  (called later, from a SEPARATE `create_job` request) would find nothing new either.
- **No field_ops.Job**: not applicable — this method never creates a Job.
- **No audit success event / domain event**: `self._publish(...)` only runs after successful
  persistence, never reached.
- **No notification**: none exist for `create_booking` beyond the domain event (unchanged).
- **No payment/invoice effect**: `create_booking` only computes a price snapshot in-memory;
  no payment/invoice row is created by this method regardless of success or failure.
- **No commit**: no explicit commit call exists; the exception propagates before any
  success-path statement runs.

## Invalid confirmation leaves the original Booking unchanged

Not modified this slice (pre-existing behavior) — `confirm_booking`'s status check
(`if b.status not in (BS.PENDING, BS.PENDING_CONFIRMATION): raise ...`) occurs before any field
assignment (`b.status = BS.CONFIRMED` etc.), so a rejected confirmation attempt leaves the
Booking row entirely as-is. Re-verified via the full `test_step4_booking.py` suite passing
unmodified.
