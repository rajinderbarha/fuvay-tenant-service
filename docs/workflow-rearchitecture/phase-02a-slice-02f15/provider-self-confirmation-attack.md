# Provider Self-Confirmation Attack — Closed

## The exploit (Slice 2F-14G's disclosed residual risk)

1. Tenant A (`tenant_owner`) chooses a completely unrelated canonical customer.
2. Tenant A calls `POST /v1/bookings` with that `customer_id` — **previously accepted with zero
   validation**.
3. Tenant A calls `POST /v1/bookings/{id}/confirm` — unilateral, no customer participation
   required.
4. Tenant A calls `POST /v1/jobs` (standalone `create_job`) for that same customer.
5. `FieldOpsService._assert_tenant_customer_relationship` finds the now-CONFIRMED Booking and
   authorizes the Job.

## Where the exploit is now blocked

**At step 2** — `BookingService.create_booking` now rejects the request at the earliest possible
point:
- If `customer_id` doesn't resolve to a real, active, non-deleted `customer`-role account:
  `FOREIGN_CUSTOMER` (422) — closes the "fabricated UUID" variant.
- If `customer_id` IS a real customer but has no existing same-tenant relationship:
  `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (422) — closes the "real but unrelated customer"
  variant, which is the actual disclosed exploit.

Step 3 (self-confirmation) is never reached — there is no Booking to confirm, since step 2 fails
first.

## Tested variations

| Variation | Result | Verified by |
|---|---|---|
| Tenant owner creates AND confirms (both actions, same actor) | Rejected at creation (step 2) | `test_bootstrap_attack_no_relationship_rejected` |
| Canonical staff performs either action | N/A — `staff` does not hold `BOOKING_CREATE` or `BOOKING_MANAGE` (confirmed via `ROLE_PERMISSIONS`), denied at the router before reaching the service at all |
| Tenant owner creates; staff confirms | N/A — staff cannot confirm |
| Staff creates; tenant owner confirms | N/A — staff cannot create |
| Read-only actor attempts either | Denied at router (`require_tenant_mutation_permission`, fixed 2F-15) |
| Technician attempts either | N/A — technician holds neither `BOOKING_CREATE` nor `BOOKING_MANAGE` |
| Customer associated only with Tenant B | Rejected — `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (query scoped to Tenant A only) | `test_bootstrap_attack_no_relationship_rejected` (same mechanism) |
| Completely unrelated customer | Rejected — identical error to the Tenant-B case | same |
| Disabled/deleted customer | Rejected — `FOREIGN_CUSTOMER` | `test_disabled_customer_rejected` / `test_deleted_customer_rejected` |
| Cross-tenant Booking ID (for confirm) | Rejected — `_assert_can_access_booking` (pre-existing, unmodified) |
| Wrong service | N/A to this specific attack (service is independently validated, unrelated to customer authority) |
| Invalid Booking state (confirm from a non-pending state) | Rejected — `BOOKING_INVALID_STATUS_TRANSITION` (pre-existing, unmodified) |

## Conclusion

The exploit fails at the earliest authoritative boundary (Booking creation itself), not at a
later, more expensive checkpoint. No Booking, confirmation, or Job is ever created for the
attack scenario.
