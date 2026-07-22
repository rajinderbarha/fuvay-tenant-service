# Product Decisions Required — Slice 2F-4

## 1. Should `tenant_engine.portal_router`'s `update_profile`/`update_settings`/`create_user`/`suspend_user`/`create_staff`/`update_staff_photo` be retired or wired into the frontend?
No frontend caller was found for these 6 endpoints in
`frontend/tenant-portal/lib/api.ts` (the profile update goes through
`tenant_engine.router`'s `PUT /v1/tenants/{tid}` instead; staff deactivation
goes through `auth.router`'s `/v1/auth/staff/{id}/deactivate`). This slice
did not retire, redirect, or otherwise change these endpoints — only
guarded them — since determining whether they are genuinely dead,
partially used by another client (mobile app? internal tooling?), or
awaiting a future frontend wire-up is a product question, not a security
one. Flagged for investigation, not resolved.

## 2. Should `create_staff` (direct password creation) and `auth.router`'s `/staff/invite` (invitation flow) be consolidated?
These appear to be two different staff-onboarding mechanisms (immediate
temp-password creation vs. email invitation) — not confirmed to be
intentional parallel options or an incomplete migration from one to the
other. Not decided or changed this slice.

## 3. Should the `admin_deactivate_staff` / `staff_deactivated` session-revocation reason strings be unified across `AuthService.deactivate_staff` and `AdminTenantService.deactivate_staff`?
Both now use `revocation_reason="staff_deactivated"` (matched deliberately
this slice), but the two methods remain otherwise independent
implementations rather than one calling the other. Whether they should be
consolidated into a single canonical deactivation path is a product/
architecture question, not resolved here (doing so was out of this slice's
narrow "close the found gap" scope).
