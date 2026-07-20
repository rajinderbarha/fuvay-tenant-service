# Customer Identity Authority

## Customer self-booking

- `customer_id` is server-derived from `uuid.UUID(u.user_id)` (router.py:93) — never read from
  the request body for this branch.
- Request `customer_id` cannot override the principal: confirmed via source — the ternary
  (`uuid.UUID(u.user_id) if u.role == "customer" else ...`) means a `customer`-role actor's body
  value is never even evaluated.
- Tenant and service are resolved server-side and validated for serviceability
  (`ServiceabilityService`), unchanged.
- Another customer's identity is not selectable: confirmed, structurally impossible for this
  branch.

## Tenant/provider-assisted booking

**Chosen policy: `EXISTING_TENANT_RELATIONSHIP_REQUIRED`** (fixed this slice).

Evidence considered for this choice (Workstream 6):
- No tenant-local contact model exists (confirmed, Slice 2F-14G's audit).
- No verified-invitation system exists.
- No lead/customer relationship model beyond `Booking`/`Job` rows themselves exists.
- No explicit offline-consent record field exists on `Booking` (confirmed this slice —
  `booking-model-lineage.md`).
- The only real, evidenced relationship signals anywhere in this codebase are: an existing
  same-tenant `Booking` (qualifying status) or an existing same-tenant `field_ops.Job`
  (source-derived) — the exact signals `FieldOpsService._assert_tenant_customer_relationship`
  already established in Slice 2F-14F/G.

**Rejected disposition: `ARBITRARY_CUSTOMER_TARGETING_DEFECT`** was the PRE-FIX reality (absence
of validation, confirmed exploitable) — now fixed, not merely re-labeled.

**Rejected disposition: `ANY_PLATFORM_CUSTOMER_ALLOWED_BY_EXPLICIT_POLICY`** — no such policy was
ever ratified; the opposite was explicitly disclosed as a vulnerability in Slice 2F-14G.

## Implementation

Reuses `FieldOpsService`'s exact qualifying predicate (Slice 2F-14G): `QUALIFYING_BOOKING_STATUSES`
(confirmed/scheduled/dispatching/in_progress/completed/converted_to_job) for existing Bookings,
`booking_id IS NOT NULL OR parent_job_id IS NOT NULL` for existing Jobs. No new relationship
model was created — this slice's fix in `BookingService.create_booking` is a direct, minimal
duplication of the same query logic, scoped to the `booking` engine's own service (cross-engine
import of `field_ops.models.Job`, read-only, no adapter).
