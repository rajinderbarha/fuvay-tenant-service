# Booking Model Lineage

## Exact model

`app.engines.booking.models.Booking` (table `bookings`) — the SAME model used by
`BookingService.create_booking`, `BookingService.confirm_booking`, `Booking.convert_to_job`, and
`FieldOpsService._assert_tenant_customer_relationship` (confirmed via direct import inspection —
all four reference `app.engines.booking.models.Booking`, no separate model exists).

## Fields

| Field | Present | Classification |
|---|---|---|
| `id` (PK) | yes | n/a |
| `tenant_id` | yes | `SYSTEM_ORIGIN_PROOF` — resolved server-side via serviceability matching, never client-suppliable (confirmed: router rejects `body.tenant_id` outright) |
| `customer_id` | yes | `CHANNEL_ONLY_NOT_AUTHORITY` before this slice (client-suppliable with no validation for non-customer actors); now `CUSTOMER_ORIGIN_PROOF` for self-booking (server-derived from `u.user_id`) and validated-but-still-`PROVIDER_ORIGIN_PROOF` for assisted booking (fixed this slice: existence + role + active + relationship required) |
| `service_type_id`/`service_category` | yes | `SYSTEM_ORIGIN_PROOF` — resolved server-side from `service_id` via `ServiceabilityService._resolve_service_type_id` |
| `status` | yes | see booking-status-trust-matrix.csv |
| `created_at` | yes (inherited `ServiceOSBase`) | `AUDIT_ONLY` |
| `created_by`/explicit creation-actor field | **ABSENT** — no dedicated column records who created the Booking (only inferable from `BookingStatusHistory`'s `changed_by`/`changed_by_role` on the initial DRAFT→PENDING_CONFIRMATION-equivalent history row, if one exists) | `INSUFFICIENT_PROVENANCE` |
| `confirmed_by_user_id` | **yes** (`Mapped[uuid.UUID \| None]`, set in `confirm_booking`) | `CONFIRMATION_ACTOR_PROOF` — proves WHO confirmed, but not WHETHER that confirmer was the customer (confirm_booking explicitly denies `customer` role from confirming — see confirmation-semantics.md) |
| `confirmed_at` | yes | `AUDIT_ONLY` |
| `source_type`/`source_id`/`channel`/`consent marker` | **ABSENT** — no field records the booking's channel (customer app vs. tenant-assisted) or any consent flag | `ABSENT` |
| `converted_job_id` | yes | `SYSTEM_ORIGIN_PROOF` (set only by `Booking.convert_to_job`, atomically) |
| `BookingStatusHistory` relationship | yes (`booking_id` FK) | `AUDIT_ONLY` — append-only, records `changed_by`/`changed_by_role`/`reason`, but no cryptographic integrity/immutability guarantee beyond normal DB row protection |
| `ServiceBooking` relationship | **NONE** — `Booking` and `ServiceBooking` are entirely distinct models in distinct engines; confirmed no FK or shared table between them (see out-of-scope confirmation below) |
| Notification relationship | indirect — `self._publish("booking.confirmed", ...)` domain events exist but no dedicated notification table |
| Payment relationship | indirect via `price_snapshot_id`/`quoted_price`; no direct payment FK |
| Soft-delete/disabled/voided behavior | `status` includes `BS.VOIDED`/`BS.CANCELLED` as terminal states; no separate `deleted_at`/`is_deleted` column exists on `Booking` (confirmed, unchanged finding from Slice 2F-14G) |

## Confirmed: Booking and ServiceBooking remain separate

No modification was made to any `ServiceBooking`-related model or service this slice. `Booking`
(this engine) and `ServiceBooking` (a distinct pipeline referenced in prior slices' scope
boundaries) share no foreign key, no shared table, and no adapter — confirmed via source
inspection, unchanged.
