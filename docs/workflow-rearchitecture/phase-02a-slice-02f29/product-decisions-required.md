# Product Decisions Required - Slice 2F-29

**None blocking. The one question carried from 2F-28 is now answered by the
code rather than by assumption:**

`POST /v1/auth/impersonate` - `AuthService.impersonate` requires
`impersonator.role == "super_admin"` and rejects everything else, including
`admin_security`, regardless of the `platform:impersonate` permission. The
effective policy is therefore **super_admin only**. No policy was invented and
no capability was expanded. If the product intends `admin_security` to
impersonate, that is a future product decision and a code change - not an
assumption this slice was willing to make.

Non-blocking observations for future modules (not decided here):
- Whether `invite_staff` should treat an email that already exists in a
  *different* tenant as a conflict (see known-limitations).
- Whether deactivating an already-inactive staff member should be a 409 rather
  than a no-op success.
