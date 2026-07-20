# Selected Module Implementation Contract - Slice 2F-30
## (to be executed by a FUTURE slice; not executed here)

## Selected module
`N01_media_assets` - `app.engines.media.new_router` /
`MediaAssetService` + `MediaService` + `MediaAccessService`.

## Set A - canonical routes (all 9 MUST be remediated)

1. `DELETE /v1/provider/profile/logo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)
2. `DELETE /v1/provider/profile/shop-photo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)
3. `DELETE /v1/staff/profile/photo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)
4. `POST /v1/me/profile-photo` (AUTHENTICATED_ONLY_NO_PERMISSION_CHECK)
5. `POST /v1/media/upload` (AUTHENTICATED_ONLY_NO_PERMISSION_CHECK)
6. `POST /v1/media/{media_id}/replace` (AUTHENTICATED_ONLY_NO_PERMISSION_CHECK)
7. `POST /v1/provider/profile/logo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)
8. `POST /v1/provider/profile/shop-photo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)
9. `POST /v1/staff/profile/photo` (ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE)

## Set B - held adjudication routes (3, MUST be adjudicated before closure)

1. `POST /v1/media/upload/initiate`
2. `POST /v1/media/upload/{session_id}/confirm`
3. `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}`

These are **not canonical**. They may only enter coverage with full evidence.

## Set C - EXCLUDED (must not be touched)

EXCLUDED: `GET /v1/media/signed/{token}` (read-only);
`DELETE /v1/media/{media_id}` (held, not canonical);
`POST /v1/security/api-keys/{key_id}/rotate` (separate subsystem);
`DELETE /v1/webhooks/endpoints/{endpoint_id}` and
`DELETE /v1/geo/zones/{zone_id}` (different modules, canonical but not
selected); `PUT /v1/me/profile` and `PUT /v1/staff/profile` (N03 profile module).

## Required guard pattern

Add mutation-capable access-scope enforcement using the **existing** canonical
guard family. The module is role-based today and has no media permission -
**do not add a permission**. Use the role-based access-scope-aware guard
(`require_*_mutation` family) matching the current admitted roles per route.

## Required service-layer changes

`MediaAccessService.assert_can_delete` / `assert_can_view` already enforce
same-tenant and must remain the enforcement point. Verify the same policy is
applied on upload and replace paths, and that replace cannot re-parent an asset
across tenants.

## Required audits

Connected-read privacy (404 vs 403 on foreign assets), state integrity
(no double-delete / replace-after-delete), transaction atomicity (no orphaned
storage object), internal-caller preservation.

## Allowed application files
`app/engines/media/new_router.py`, `app/engines/media/asset_service.py`,
`app/engines/media/access.py`, and `app/engines/media/service.py` **only if**
the upload/replace path requires it.

## Forbidden application files
Everything else, including `app/core/permissions.py` (no new permission),
`app/dependencies/auth.py` (no new role), any migration, any frontend/mobile
file, the security API-key subsystem, and every closed module including M01.

## Coverage arithmetic rules
Protected 226 -> up to 235 as routes close. Denominator stays 259 unless a Set B
route is added with full evidence (then it rises accordingly). Unprotected
33 -> 24 on full closure. Report honestly if fewer close.

## Allowed final statuses
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`,
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`, `SECURITY_CLOSED_PRIVACY_BLOCKED`,
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`,
`IMPLEMENTATION_SCOPE_BLOCKED`, `INCOMPLETE` - all scoped to N01 only.

## Stop condition
Stop at that slice's approval gate. Do not select the following module.
