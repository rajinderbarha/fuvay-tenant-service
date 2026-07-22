# Vertical and Configuration Routing — Workstream 4

## Finding: single vertical, single pipeline for these 3 modules
All 3 audited modules (`execution.home_service_router`,
`home_service_assignment.staff_router`, `home_service_assignment.provider_router`)
are home-services-vertical-specific by naming and by the `ServiceJob` record
they share — there is no tenant-configuration, feature-flag, or
vertical-type branching found inside any of the 29 routes that would route
a request to a DIFFERENT execution system based on vertical or config.

## Other verticals use separate, non-overlapping modules
`app.engines.execution.coaching_router` and
`app.engines.execution.real_estate_router` exist as their OWN separate
routers (confirmed present in `app/main.py`'s registration block,
registered immediately after `execution.home_service_router` in the same
"Sprint 21" block) — these are structurally distinct pipelines for
different verticals (coaching appointments, real-estate leads), not
alternate configurations of the home-services pipeline. Not further audited
this slice (out of scope: this slice's mandate is specifically the 3 named
home-service modules).

## No cross-pipeline record crossing found
A `ServiceJob` created for a home-services booking stays within these 3
modules' shared `ServiceJob`/`ServiceJobAssignment`/`PartsRequest` record
set for its entire lifecycle — no evidence was found of a home-services
`ServiceJob` ever being converted into, or substituted by, a
`CoachingAppointmentExecutionEvent` or a real-estate-vertical record, or
vice versa (different tables entirely, confirmed via
`app/engines/execution/models.py`'s distinct model classes for each
vertical).

## Legacy / migration-state routing
Not found within these 3 modules. The `field_ops` legacy `Job` model
(referenced in project memory as already dead per Slices L5-35/36) is not
part of this overlap — it uses an entirely separate router
(`app.engines.field_ops.staff_router`, confirmed via Slice 2F's own
platform-wide inventory listing it separately at 6 endpoints, 0%
protected, `RUNTIME_VERIFIED`), untouched by this slice.
