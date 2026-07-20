# Supported Creation Modes

## MANUAL_PROVIDER_JOB

- **Required identifiers**: `title`, `service_type_id` (tenant-validated + active).
- **Forbidden identifiers**: none additional — `customer_id`/`booking_id`/`parent_job_id` are
  all optional.
- **Authoritative tenant source**: server-pinned `actor_tenant_id` (2F-14B).
- **Authoritative customer source**: `customer_id`, if supplied, must reference a real
  `customer`-role account (2F-14C) — otherwise the Job is created with `customer_id=None`.
- **Authoritative service source**: `service_type_id`, tenant + active validated (2F-14C).
- **Parent/source relationship**: none required.
- **Duplicate policy**: none applicable (no source to duplicate from).
- **Initial status**: `JS.DRAFT`.
- **Caller evidence**: this is `create_job`'s default/fallback mode — no dedicated frontend or
  internal caller exists for it (`FRONTEND_MUTATION_SURFACE_ABSENT`), but the route itself is
  clearly designed for it (tenant staff manually creating a Job with no booking/parent).

## PARENT_JOB_DERIVED_REPAIR

- **Required identifiers**: `parent_job_id`, `job_type=REPAIR` (typically).
- **Authoritative tenant source**: parent's own `tenant_id` (cross-checked, 2F-14C).
- **Authoritative customer source**: parent's own `customer_id` — cross-checked this slice
  (`CUSTOMER_PARENT_JOB_MISMATCH` if an explicitly-supplied `customer_id` disagrees).
- **Authoritative service source**: **not** derived from the parent — `service_type_id` is
  independently client-supplied (or auto-detected from the catalog) and MAY legitimately differ
  from the parent's own service (this mirrors `convert_to_repair`'s own established
  `repair_service_id or job.service_type_id` policy).
- **Duplicate policy**: exactly one `REPAIR` job per `CONSULTATION` parent (enforced this slice,
  mirroring `convert_to_repair`/`spawn_repair`'s existing guard).
- **Initial status**: `JS.DRAFT` (note: this differs from `convert_to_repair`'s own dedicated
  code path, which sets `JS.PENDING_ASSIGNMENT`/`JS.ASSIGNED` directly — `create_job`'s generic
  path always starts at `DRAFT` regardless of mode, an intentional simplification since
  `create_job` is not `convert_to_repair`'s replacement).
- **Caller evidence**: `FieldOpsService._spawn_repair_from_consultation` (internal), which always
  supplies a matching `customer_id` (derived from the consultation before calling `create_job`).

## BOOKING_DERIVED_JOB — NOT via create_job

The canonical, atomic booking-conversion pipeline is `Booking.convert_to_job` (in
`app/engines/booking/service.py`), a **separate method entirely**, unmodified and out of scope
this slice. It derives `tenant_id`/`customer_id`/`service_type_id`/address/pricing all directly
from the `Booking` row (not client-supplied at all), enforces `BS.CONFIRMED` status, blocks
duplicate conversion (`b.converted_job_id`), denies `customer` actors, and tags the resulting Job
with `source="booking"`. `create_job`'s own `booking_id` field is a **different, secondary
capability** — see `STANDALONE_JOB_WITH_BOOKING_REFERENCE` below.

## STANDALONE_JOB_WITH_BOOKING_REFERENCE

- **Required identifiers**: `booking_id` (tenant-validated), plus the usual
  `title`/`service_type_id`.
- **Authoritative tenant source**: booking's own `tenant_id` (cross-checked, 2F-14C).
- **Authoritative customer/service source**: booking's own `customer_id`/`service_type_id` —
  cross-checked this slice (`CUSTOMER_BOOKING_MISMATCH`/`SERVICE_BOOKING_MISMATCH` if an
  explicitly-supplied value disagrees).
- **Duplicate policy**: exactly one Job per booking (enforced this slice, mirroring
  `Booking.convert_to_job`'s own `converted_job_id`/existing-Job-by-`booking_id` guards).
- **Initial status**: `JS.DRAFT`.
- **Caller evidence**: no frontend/internal caller currently exercises this combination
  (`FRONTEND_MUTATION_SURFACE_ABSENT`) — this mode's closure is preventative, not observed-in-use.

## INTERNAL_CONVERSION_JOB / LEGACY_COMPATIBILITY

No distinct evidence of either as a separate mode from the above — not adopted as categories.

## Ambiguous mixtures

`booking_id` + `parent_job_id` supplied together: **not** enforced as mutually exclusive (no
existing policy requires this), but both are independently cross-checked (customer/service
consistency against each) — if both disagree with each other's implied customer, the request is
rejected on whichever check runs first (`booking_id`'s customer check, since parent is validated
before booking in source order — see create-job-contract.md). This is disclosed as
`PRODUCT_DECISION_REQUIRED` in product-decisions-required.md (whether the two should be formally
mutually exclusive), not silently allowed as an assumed-safe combination.
