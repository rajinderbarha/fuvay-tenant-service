# Deferred Items — Slice 2F-3A

## Recommended next slice
Apply access-scope-aware mutation guards to all 3 audited modules together
(`execution.home_service_router`, `home_service_assignment.staff_router`,
`home_service_assignment.provider_router`) — now unblocked by this slice's
adjudication. Recommended scope:
- Skip the 2 dead (`staff_accept_job`/`staff_reject_job`) endpoints, or
  explicitly document them as excluded-because-unreachable.
- Guard the 20 remaining live `execution.home_service_router` endpoints
  (14 progress + 4 parts + 3 admin, noting the admin 3 need a different,
  platform-admin-appropriate treatment, not tenant access-scope guards).
- Guard `home_service_assignment.staff_router`'s accept/reject (the
  canonical, reachable implementation) and `provider_router`'s 4 endpoints.
- Independently re-verify object/assignment-ownership correctness for each
  (per `known-limitations.md` items 2-4) as part of that slice's own audit
  work, the same way Slices 2F-1/2F-2 did.

## Product/architecture decisions not made this slice
1. Whether to eventually retire the dead `staff_accept_job`/
   `staff_reject_job` functions (requires a proper retirement plan, out of
   scope here).
2. Whether `home_service_assignment`'s accept/reject should gain an
   explicit tenant_id filter as defense-in-depth (not proven necessary, but
   worth considering in the guard slice).
3. Whether the original intent behind the accept/reject duplication should
   be investigated further (git blame / original PR history) — not done
   this slice.

## Not in scope for any future slice unless separately approved
Merging Booking/Job/ServiceBooking/ServiceJob, selecting a platform-wide
canonical booking pipeline, Booking Exception Resolution, modifying
`tenant_engine.router` or `provider_portal.router`, `readonly@` remediation,
migration 144 application, Admin/Tenant My Work, Next-Action aggregation,
onboarding/provider-setup redesign, chat ownership changes, visual redesign,
theme changes, new role aliases — none touched, consistent with the
brief's explicit exclusions.
