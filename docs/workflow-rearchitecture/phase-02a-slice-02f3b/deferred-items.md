# Deferred Items — Slice 2F-3B

## Product decisions (see product-decisions-required.md)
1. Whether to eventually delete the dead shadowed functions.
2. Whether `reassign_job`/`cancel_assignment`/`schedule_job` need a
   dedicated ownership audit.
3. Whether `provider_install_parts_request`'s exact mechanism should be
   re-documented.
4. Whether staff/technician execution actions should eventually get
   granular permissions instead of the current role-based guard.

## Recommended next slice
This slice completes the execution/assignment mutation-enforcement work
Slice 2F-3A identified as the prerequisite. With `tenant_engine.router`,
`provider_portal.router`, and now `execution.home_service_router` +
`home_service_assignment.staff_router`/`.provider_router` all
`SECURITY_CLOSED`, the next candidate module (per Slice 2F's original
platform-wide inventory) should be selected from the remaining unprotected
modules — not decided here, per "do not begin another router module."

## Not in scope for any future slice unless separately approved
Merging Booking/Job/ServiceBooking/ServiceJob, Booking Exception
Resolution, modifying booking creation, cross-pipeline adapters,
`tenant_engine.router`/`provider_portal.router` changes, `readonly@`
remediation, migration 144 application, Admin/Tenant My Work, Next-Action
aggregation, onboarding/provider-setup redesign, chat ownership changes,
visual redesign, theme changes, new role aliases — none touched,
consistent with the brief's explicit exclusions.
