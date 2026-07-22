# Deferred Items — Slice 2F-2

## Product decisions (see product-decisions-required.md)
1. Whether `create_member_login` should actually be implemented.
2. Whether per-technician individual availability is a wanted feature.
3. Whether `create_team_member` should detect duplicate invitations.
4. Whether any provider-portal capability should ever support delegated
   staff (would require a permission-based sibling guard, not a broadened
   role check).

## The core remaining platform-wide work (unchanged in kind)
Extend access-scope-aware mutation protection to the remaining router
modules Slice 2F's inventory identified as unprotected. This slice closed
`provider_portal.router` (24 endpoints); `tenant_engine.router` (27,
Slice 2F-1/2F-1A) and this module are now closed. Recommended next, per
Slice 2F's priority order: `execution.home_service_router` (20 endpoints)
— explicitly NOT started this slice, per the brief's instruction, and
still blocked on resolving its overlap with `home_service_assignment`
first (unchanged from Slice 2F's finding).

## Smaller, scoped follow-ups
1. `create_member_login`'s real implementation (if product decides to
   build it).
2. `create_team_member` duplicate-detection (if product decides it
   matters).
3. Individually re-verify `set_area_coverage`'s existing tests (not
   re-run in isolation this slice, only via the broader partition).

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, Next-Action aggregation, provider-setup
redesign, business-onboarding redesign, Booking Exception Resolution,
Booking/Job/ServiceBooking/ServiceJob merge, the execution/
home_service_assignment overlap, chat ownership changes, visual redesign,
theme changes, new component library, `readonly@` remediation, migration
144 application, new role aliases — none touched, consistent with the
brief's explicit exclusions.

## Recommended next slice
`execution.home_service_router` (20 endpoints) — but only after a
dedicated resolution of its overlap with
`home_service_assignment.staff_router`/`provider_router` (both define
overlapping endpoints like `.../accept`), a blocker Slice 2F identified and
no slice since has resolved. Recommend that resolution be its own small
slice before the guard-application work begins, to avoid guarding one of
two competing implementations while leaving the other exposed.
