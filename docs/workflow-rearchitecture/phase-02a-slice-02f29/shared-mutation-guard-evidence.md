# Shared Mutation-Guard Evidence - Slice 2F-29

The six tenant mutations now use the existing canonical guard family
`require_tenant_mutation_permission(<existing permission>)`. No parallel
authorization framework was created and no permission was added.

That guard proves, in one place:
- authenticated canonical principal (`get_current_user`),
- the required permission via `PermissionChecker.has`, which consults
  StaffPermission overrides (so a runtime-extensible permission is not reduced
  to super_admin-only),
- explicit deny beats grant,
- **mutation-capable access scope**: a tenant-side principal whose
  `access_scope` is read-only is rejected before the request body is parsed
  (`TENANT_READONLY_ACCESS_SCOPES`),
- unknown role / unknown scope fail closed.

Verified live per route by dependency introspection (`access_scope_gated=True`
for all six). `POST /v1/auth/impersonate` deliberately does NOT receive this
guard - it is a platform capability, not a tenant mutation, and `AuthService`
enforces `super_admin` directly.

Non-Set-A routes sharing the same permissions (e.g. `GET /v1/auth/api-keys`,
`POST /v1/auth/staff/{user_id}/invite/resend`) were left untouched and are
asserted unchanged by test.
