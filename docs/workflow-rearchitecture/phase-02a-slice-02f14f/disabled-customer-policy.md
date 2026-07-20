# Disabled / Invalid Customer Account Policy

## Disposition: ACTIVE_CUSTOMER_REQUIRED

## Evidence

`auth.User` (the model backing every `customer`-role account) carries `is_active: bool` (default
`True`) and `deleted_at: datetime | None` (default `None`). No separate "suspended" state exists.

`Booking.convert_to_job` already applies an analogous pattern for staff assignment:
`if hasattr(staff, "is_active") and not staff.is_active: raise ServiceOSException("STAFF_INACTIVE", ...)`
— confirming `is_active` is the established, existing signal this codebase already uses to gate
*newly associating* an account with a Job.

## Fix

`create_job`'s customer validation (2F-14C, extended this slice) now also requires
`customer_user.is_active` and `customer_user.deleted_at is None` — a deactivated or deleted
customer account cannot be newly associated with a Job. Reuses the same `FOREIGN_CUSTOMER` error
code as the pre-existing "not a valid customer account" check (no new error code was needed —
both represent "this identifier does not resolve to a usable customer account", and using the
same code avoids leaking *why* a given `customer_id` was rejected, consistent with this slice's
privacy requirements).

## Scope

This governs only **new association** (creating a Job that references this customer). It does
not touch account-management behavior anywhere else (no deactivation/reactivation logic was
built or modified — explicitly out of scope).
