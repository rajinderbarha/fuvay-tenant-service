# Implementation Summary - Slice 2F-31 (N01)

## Final status: SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED

Scoped to **N01_media_assets only**. This is NOT an application-wide claim.

## Result

| Metric | Before | After |
|---|---|---|
| Protected | 226 | **233** |
| Denominator | 259 | **262** |
| Unprotected | 33 | **29** |
| Canonical hash | fbe7cf863afa0d84 | af8388463ac3dbfa |
| Matrix hash | 753653ed32916f4e | 3066e137e9a23c19 |

c=7 (Set A closed), a=3 (Set B added), h=0 (no Set B route earned protection).
233 = 226+7+0. 262 = 259+3.

## Set A: 7 of 9 closed

Six role-guarded routes (provider logo/shop-photo, staff profile photo)
switched `require_technician` -> `require_staff_or_above_mutation` (the
IDENTICAL role set - `{super_admin, tenant_owner, staff, technician}` - plus
mutation-capable access-scope denial). `POST /v1/me/profile-photo` was already
correctly self-scoped and is now formally `FULLY_PROTECTED`.

**Two routes remain open**: `POST /v1/media/upload` and
`POST /v1/media/{media_id}/replace`. Both admit customers as well as tenant
staff (`get_current_user`), and no scope-only guard exists in the codebase.
Adding one requires `app/core/permissions.py`, which the frozen 2F-30 contract
**forbids**. Recorded as `IMPLEMENTATION_SCOPE_BLOCKED` for these two routes
specifically, not worked around.

## Set B: all 3 adjudicated TENANT_PROVIDER_MUTATION_ADD, all left unprotected

The critical scope finding of this slice: **all three Set B routes live in
`app/engines/media/router.py`**, a different router from the Set A boundary
(`new_router.py`) and **not on the frozen application-file allow-list**.

Each was adjudicated with full evidence and added to the canonical inventory
(denominator +3), but none could be remediated:

- `POST /v1/media/upload/initiate` - tenant_id taken from the request BODY,
  drives quota + storage-key prefix. No principal-tenant check anywhere.
- `POST /v1/media/upload/{session_id}/confirm` - resolves the upload session
  by id alone; inherits whatever tenant was asserted at initiate.
- `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}` - the exact
  client-asserted-tenant delete named in the mission. `require_permission
  (TENANT_UPDATE)` admits by permission only; the path `tenant_id` is never
  compared to the authenticated principal's own tenant.

Adding them to coverage without fixing them is the honest outcome: they are
real tenant mutations that were invisible to the canonical inventory, and now
they are visible and tracked as unprotected instead of silently absent.

## Why the scope gate did not block the whole slice

The mission's scope-block condition is triggered by a **frozen-set mismatch**
(wrong hash, wrong count, unmounted route). Set A/B/C all verified exactly as
frozen. The discovery here is narrower and more precise: the *implementation
contract's allow-list* does not cover the router Set B lives in. That is a
Workstream 3/8 evidence finding, not a Workstream-pre-check scope failure, and
it is handled by adjudicating-and-recording rather than by blocking the
9-route Set A work that WAS in scope.

## What was verified, not assumed

- `MediaAccessService.assert_can_delete` -> `assert_can_view` still enforces
  same-tenant scope and customer-self-only deletion - re-read and re-asserted,
  not modified.
- `MediaAssetService.replace_asset` still calls `assert_can_replace`.
- The non-allow-listed `media/router.py` was **not touched** - asserted by
  test (no `2F-31` marker in its source).

## Verification

- `tests/test_phase2f31_n01_media_closure.py` - **35 passed**
- Full phase-2F suite - **2290 passed, 0 failed**
- `verify_n01_2f31.py` - 20/20 PASS; `--selftest` exit 0
- Application files changed: exactly 1 - `app/engines/media/new_router.py`
