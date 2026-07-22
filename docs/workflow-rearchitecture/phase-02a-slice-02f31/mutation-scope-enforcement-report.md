# Mutation-Scope Enforcement Report - Slice 2F-31

Six Set A routes moved from `require_technician` (role-only) to
`require_staff_or_above_mutation` (role + mutation-capable access-scope
denial). Verified live via dependency introspection: all six now report
`access_scope_gated=True`.

`require_staff_or_above_mutation` wraps `require_staff_or_above`, admitting
the IDENTICAL role set as `require_technician` -
`{super_admin, tenant_owner, staff, technician}` - and additionally denies any
tenant-side principal whose `access_scope` is read-only, before the request
body is parsed.

`POST /v1/me/profile-photo` needed no guard change: it is self-scoped and now
formally `FULLY_PROTECTED`.

Two routes (`POST /v1/media/upload`, `POST /v1/media/{media_id}/replace`)
remain unscoped: they admit `get_current_user` broadly (including customers),
and no scope-only guard family exists. `require_staff_or_above_mutation` is
NOT applicable - it would incorrectly exclude customers who are allowed to
upload/replace their own media. A correct fix needs a new guard in
`app/core/permissions.py`, forbidden by the frozen contract.
