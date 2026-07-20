# Known Limitations — Slice 2F-4

1. **7 of 10 endpoints have no confirmed frontend caller** (`update_profile`,
   `update_settings`, `create_user`, `suspend_user`, `create_staff`,
   `deactivate_staff`, `update_staff_photo`) — not chased to a definitive
   "dead" or "used by another client" conclusion. See
   `product-decisions-required.md` item 1.
2. **`create_staff`'s direct-password mechanism vs. `auth.router`'s
   `/staff/invite` invitation flow were not reconciled** — both exist,
   purpose/relationship not clarified this slice.
3. **Cross-tenant HTTP proof was not independently re-exercised live**
   beyond source-inspection regression tests confirming the pre-existing
   `AdminTenantService`/`AuthService` ownership mechanisms remain intact
   and unmodified (aside from the two fixes made this slice).
4. **`package_commerce.admin_router` and `finance_hub.admin_router`
   were flagged but not investigated** — their naming suggests
   platform-admin-only, but per the mission's own warning ("do not assume
   admin_router = platform-only"), their actual guard composition
   (`PERMISSION_ONLY_NOT_SCOPE_AWARE`, not `PLATFORM_ADMIN_ONLY`) was not
   independently re-verified this slice. Flagged as a real risk for a
   future slice, not resolved.
5. **`app.engines.auth.platform_users_router`'s relationship to this
   module's capabilities was not independently verified** — not confirmed
   to expose or duplicate any of this module's 10 endpoints.
6. **A full-repository test run was not completed** — 820 combined tests
   (594 targeted + 226 broader partition), 0 failures, is the evidence
   base.
7. **`readonly@demo-ac-services.local` remains untouched; migration 144
   remains unapplied; the 5 previously security-closed modules
   (`tenant_engine.router`, `provider_portal.router`,
   `execution.home_service_router`,
   `home_service_assignment.staff_router`/`.provider_router`) were not
   modified** — all confirmed per the brief's explicit exclusions.
8. **Pre-existing duplicate-operation-ID warnings** remain, unrelated,
   unfixed (same as every prior slice).
