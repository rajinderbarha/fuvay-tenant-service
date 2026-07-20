# Booking `add_note` Authorization

**Before:** `Depends(get_current_user)` only — any authenticated user of any role/tenant could attempt to add a note to any Booking (service-level `_assert_can_access_booking`, if present, was the only backstop, and was not confirmed to exist for this specific route at router level).

**After:** `Depends(require_staff_or_above_mutation)` — admits `tenant_owner`/`staff`/`technician`/`super_admin`, excludes `customer`, denies read-only tenant `access_scope`.

**Evidence for excluding `customer`:** a repo-wide search for booking-note API callers found only `bookingsApi.addNote` in the tenant-portal frontend (`frontend/tenant-portal`); no customer-facing surface calls this endpoint. Gating provider-only is evidence-based, matching the identical precedent set for `field_ops.add_note`/`add_media` in Slice 2F-14C (same reasoning: no live customer caller, mutation-scope-aware provider gate).

**If a customer note-taking surface is added in future**, it should follow the `DUAL_CUSTOMER_TENANT_MUTATION` pattern already established for `cancel_booking`/`request_reschedule` (own-booking ownership check + `require_tenant_mutation_permission`), not be bundled into this fix.
