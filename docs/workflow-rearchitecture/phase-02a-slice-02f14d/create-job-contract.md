# create_job — Exact Request Contract

## Mounted path

`POST /v1/jobs` (`app.engines.field_ops.router`), guard `require_tenant_mutation_permission(P.TENANT_UPDATE)` (unchanged this slice).

## Fields

| Field | Category |
|---|---|
| `title` | REQUIRED (client-supplied) |
| `service_type_id` | REQUIRED (client-supplied; `data["service_type_id"]` — no `.get()` — but empty string is accepted and skips ownership validation, see known-limitations.md) |
| `description` | OPTIONAL |
| `service_category` | OPTIONAL (defaults `"general"`) |
| `job_type` | OPTIONAL (defaults `JobType.REPAIR`; validated against `JOB_TYPES` enum; auto-detected from catalog if omitted and `service_type_id` given) |
| `parent_job_id` | OPTIONAL, CONDITIONAL (tenant + customer cross-checked this slice; service NOT cross-checked, see parent-job-relational-consistency.md) |
| `booking_id` | OPTIONAL, CONDITIONAL (tenant + customer + service cross-checked and duplicate-guarded this slice, see booking-relational-consistency.md) |
| `customer_id` | OPTIONAL (existence + `role=="customer"` validated since 2F-14C; cross-checked against booking/parent this slice) |
| `findings`/`recommendation` | OPTIONAL |
| `checklist` | OPTIONAL (overridden by catalog template if unset and catalog provides one) |
| `duration_estimate_minutes` | OPTIONAL (overridden by catalog if unset) |
| `address`/`pincode`/`latitude`/`longitude` | OPTIONAL, free-form (not a normalized reference) |
| `scheduled_at` | OPTIONAL |
| `quoted_price` | OPTIONAL (overridden by catalog `base_price` if unset and pricing is fixed) |
| `tags` | OPTIONAL |
| `tenant_id` | SERVER_DERIVED for `tenant_owner`/`staff`/`technician` (pinned since 2F-14B); CLIENT_SUPPLIED (honored) for `super_admin` and the internal `_spawn_repair_from_consultation` caller |

`address_id`/`zone_id`/`quote_id`/`assigned_staff_id`/`assigned_technician_id`/`category_id`/
`provider_id`/`checklist_template_id`/schedule-slot ID — **UNSUPPORTED**, not accepted by this
route at all (see Slice 2F-14C's create-job-request-field-inventory.csv).

## Model / initial status

`field_ops.Job` (table `jobs`), initial status always `JS.DRAFT` (hardcoded in
`_write_history(job, None, JS.DRAFT, "Job created", None, None)`), regardless of creation mode.

## Assignment / checklist / history / audit / notification

- No assignment is ever created by `create_job` itself (assignment happens exclusively via the
  separate `assign_job` route).
- Checklist: only auto-populated from the catalog's `checklist_template` if the client did not
  supply one AND `service_type_id`'s (now tenant-validated) catalog entry has one — this is a
  denormalized copy into `Job.checklist` (the legacy JSONB field), **not** the normalized
  `JobChecklistItem` system (which only ever gets materialized later via `start_job_checklist`).
- `JobStatusHistory`: one row, `from_status=None, to_status=JS.DRAFT`.
- Audit: none beyond the status-history row and a `structlog` warning on catalog-lookup failure.
- Notification: `self._publish("job.created", ...)` — a domain event, not a directly-observed
  user notification in this codebase.

## Flush/commit order

All new relational-consistency validations (this slice) + all pre-existing individual FK
validations (Slice 2F-14C) execute **before** `Job(...)` is constructed. `self.db.add(job)` +
`await self.db.flush()` occur next, followed by history/usage-quota/Redis-token/publish calls.
No explicit `commit()` call exists in this method — the surrounding request-scoped transaction
(managed by the FastAPI dependency layer, unchanged, out of scope) commits after the route
handler returns successfully.

## Frontend/internal callers

- **Frontend**: none (`FRONTEND_MUTATION_SURFACE_ABSENT`, confirmed in Slice 2F-14 and
  re-confirmed unchanged this slice).
- **Internal**: `FieldOpsService._spawn_repair_from_consultation` (called by both
  `spawn_repair_from_consultation` and `respond_to_quote`'s auto-conversion path) — always
  supplies `job_type=JobType.REPAIR`, `parent_job_id=str(consultation_job.id)`,
  `customer_id=str(consultation_job.customer_id)`, and `service_type_id` copied from the
  consultation. This is the **PARENT_JOB_DERIVED_REPAIR** mode (see supported-creation-modes.md).
- **`Booking.convert_to_job`** (in `app/engines/booking/service.py`) is a **separate, unmodified,
  distinct method** that constructs a `field_ops.Job` directly (not via `create_job`) — it is the
  canonical, atomic booking-conversion pipeline and is out of scope for this slice (modifying
  `Booking` is explicitly forbidden). `create_job`'s own `booking_id` field is a **secondary,
  manual reference** for a tenant staff member linking a manually-created Job to a booking record
  — not the same code path.
