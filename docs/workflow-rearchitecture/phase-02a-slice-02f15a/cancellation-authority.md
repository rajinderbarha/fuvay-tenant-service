# Booking Cancellation Authority

`cancel_booking` (`POST /v1/bookings/{id}/cancel`) supports two legitimate personas:

- **Customer** — cancelling their own booking. `BOOKING_CANCEL` is granted to `customer` in `ROLE_PERMISSIONS`.
- **Tenant** — cancelling on the customer's behalf (e.g. provider-initiated cancellation). `BOOKING_CANCEL` is also granted to `tenant_owner`.

**Fix:** guard upgraded from `require_permission(BOOKING_CANCEL)` (permission-only, not access-scope-aware) to `require_tenant_mutation_permission(BOOKING_CANCEL)`. This wrapper additionally denies any tenant-side caller whose `access_scope` is read-only, while leaving `customer` callers (who carry no tenant `access_scope`) and `super_admin` unaffected. No new permission was added; no role/scope was added.

**Object-level ownership** (a customer may only cancel their OWN booking; a tenant may only cancel a booking belonging to their OWN tenant) is enforced by the pre-existing, unmodified service-level checks in `BookingService.cancel_booking` — confirmed present and unchanged by this slice.

No customer- vs tenant-specific cancellation *reason code* or workflow difference exists in the codebase; both personas hit the same service method.
