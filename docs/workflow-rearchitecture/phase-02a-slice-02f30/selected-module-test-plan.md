# Selected Module Test Plan - Slice 2F-30 (for the future implementation slice)

## Universal matrix (per Set A route)

| Case | Expectation |
|---|---|
| Allowed canonical role | 2xx |
| Disallowed role (e.g. customer on a provider route) | 403 |
| Matching StaffPermission grant | 2xx (where role-based policy allows) |
| Explicit deny | 403 (deny beats grant) |
| Cross-tenant StaffPermission grant | 403 |
| **Read-only mutation access scope** | 403 before body parsing - the core gap |
| Same-tenant asset | 2xx |
| Foreign-tenant asset | 404, never a 403 that confirms existence |
| Missing asset | 404 |
| Client-asserted owner_type/owner_id/tenant_id | ignored; server-derived wins |
| Actor/subject mismatch | decided by the subject, not the actor |
| Invalid state transition (replace/delete an already-deleted asset) | 409 |
| Direct `MediaAssetService` call | still enforces `assert_can_delete` |
| Alternate route (`PUT /v1/me/profile`, `/v1/staff/profile`) | same policy |
| Internal caller | still works |
| Transaction rollback on guard failure | no partial write, no orphaned file |
| Audit assertions | `media.deleted` / upload audit retained |

## Module-specific

- Upload: MIME/size validation still enforced; `media_context` must be valid.
- Replace: the replacement inherits the original's tenant/owner - it must not
  become a way to re-parent an asset into another tenant.
- Profile photo: deleting clears `User.profile_photo_media_id`; deleting
  another user's photo is impossible.
- Provider logo/shop-photo: clearing `Tenant.business_logo_media_id` must only
  affect the principal's own tenant.
- Storage: physical delete only for local driver; no orphaned object on rollback.
