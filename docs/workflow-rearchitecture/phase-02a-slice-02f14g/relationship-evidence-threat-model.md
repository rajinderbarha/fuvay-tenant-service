# Relationship Evidence Threat Model

## Evidence sources reaching `_assert_tenant_customer_relationship`

| Source | Model/table | Tenant key | Customer key | Creation actor | Creation route | Customer required? | Provider may create? | Platform may create? | Pre-2F-14F possible? | Cancellable? | Fabricable? | Audit provenance? | Source lineage? | Trust classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Booking (any status, pre-2F-14G) | `Booking` | `tenant_id` | `customer_id` | customer OR tenant_owner | `POST /v1/bookings` | No (tenant_owner override) | **Yes, with zero customer_id validation** | No | Yes | Yes (multiple ways) | **Yes** | `BookingStatusHistory` exists but wasn't queried | none | **PROVIDER_CREATED_UNVERIFIED** |
| Booking (CONFIRMED-or-later, post-2F-14G) | `Booking` | `tenant_id` | `customer_id` | customer OR tenant_owner (confirmed by tenant_owner) | `POST /v1/bookings` + `POST /v1/bookings/{id}/confirm` | No | Yes (see known-limitations.md — confirm is unilateral) | No | Yes | Only after confirmation for CONFIRMED itself; SCHEDULED+ generally reached from CONFIRMED | Residual (see below) | `BookingStatusHistory` exists, not queried this slice | `status` reachability | **PROVIDER_CREATED_BUT_VERIFIED** (structurally requires passing through the tenant's own confirm step; genuine customer-initiated confirmation is not technically distinguishable from a self-serving one — see known-limitations.md) |
| field_ops.Job (booking_id set) | `Job` | `tenant_id` | `customer_id` | tenant_owner/super_admin (via `Booking.convert_to_job`) or create_job with booking_id | `POST /v1/bookings/{id}/convert-to-job`, `POST /v1/jobs` (booking_id mode) | No | No (customer_id copied from Booking) | No | Yes | N/A | Only as fabricable as its source Booking | `booking_id` FK-like reference | **BOOKING-DERIVED, inherits Booking's trust level** |
| field_ops.Job (parent_job_id set) | `Job` | `tenant_id` | `customer_id` | tenant_owner/super_admin (via `convert_to_repair`/`spawn_repair`/create_job with parent_job_id) | `POST /v1/jobs/{id}/convert-to-repair`, `POST /v1/jobs/{id}/spawn-repair`, `POST /v1/jobs` (parent_job_id mode) | No | No (customer_id copied/cross-checked from parent) | No | Yes | N/A | Only as fabricable as its own ultimate root evidence | `parent_job_id` reference | **PARENT-DERIVED, inherits ultimate root trust** |
| field_ops.Job (generic, both null) | `Job` | `tenant_id` | `customer_id` | tenant_owner/super_admin (standalone `create_job`) | `POST /v1/jobs` (standalone mode) | No | Yes (post-2F-14C: validated User row + post-2F-14F: relationship-checked) | No | **Yes — pre-2F-14C rows could target ANY customer_id with zero validation** | N/A | Indistinguishable from a legacy arbitrary row using existing fields | none reliable | **LEGACY_PROVENANCE_UNKNOWN — excluded this slice** |

## Confirmed exploitable path (Slice 2F-14F, closed for the trivial case this slice)

1. Tenant_owner calls `POST /v1/bookings` with an arbitrary REAL customer's UUID (`BookingService.create_booking` never validates this against the `User` table) → `Booking(status=PENDING_CONFIRMATION)` created, zero customer participation.
2. Under Slice 2F-14F's `ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` predicate, this immediately satisfied `_assert_tenant_customer_relationship`.
3. Tenant_owner then calls standalone `create_job` for that customer — succeeded.

**Fixed this slice**: step 2 now requires the Booking to be in a CONFIRMED-or-later status, which the tenant_owner cannot reach via `create_booking` alone.

## Residual risk (disclosed, not fixed — see known-limitations.md)

`confirm_booking` (in `BookingService`, out of this slice's scope) allows the SAME `tenant_owner` to unilaterally confirm their own fabricated Booking with zero customer participation, reaching a now-qualifying status. This is a genuine architectural gap in the booking engine's `create_booking`/`confirm_booking` methods (missing customer-existence validation at creation, and no requirement for actual customer interaction at confirmation) — not something `_assert_tenant_customer_relationship` can close by inspecting status alone, and modifying those booking-engine methods is outside this slice's scope (confined to the `create_job` relationship helper).
