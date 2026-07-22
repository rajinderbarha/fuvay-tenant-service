# Deferred Items — Slice 2F-4

## Product decisions (see product-decisions-required.md)
1. Whether the 7 unconfirmed-caller endpoints should be wired into the
   frontend, retired, or left as-is.
2. Whether `create_staff` and `auth.router`'s `/staff/invite` should be
   consolidated.
3. Whether the two independent `deactivate_staff` implementations
   (`AuthService`/`AdminTenantService`) should eventually be unified.

## Recommended next slice
Re-verify `package_commerce.admin_router` and `finance_hub.admin_router`'s
true persona — their `admin_router` naming does not match their
`PERMISSION_ONLY_NOT_SCOPE_AWARE` guard status (genuine `PLATFORM_ADMIN_ONLY`
modules show `PLATFORM_ADMIN_ONLY` guard status elsewhere in this
inventory), meaning they may actually be tenant-facing despite the name —
exactly the trap the mission warned against assuming away. This should be
the next module investigated, per `remaining-module-priority-matrix.csv`.

## Not in scope for any future slice unless separately approved
Merging Booking/Job/ServiceBooking/ServiceJob, Booking Exception
Resolution, modifying booking creation, `readonly@` remediation, migration
144 application, Admin/Tenant My Work, Next-Action aggregation, onboarding/
provider-setup redesign, chat ownership changes, visual redesign, theme
changes, new role aliases, modifying any of the 5 already-security-closed
modules beyond the one proven direct bypass fixed this slice — none
touched, consistent with the brief's explicit exclusions.
