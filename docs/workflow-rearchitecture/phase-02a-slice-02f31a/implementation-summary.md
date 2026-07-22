# Slice 2F-31A — N01 Residual Media Scope Expansion, Security Closure and Storage-Integrity Decision

**Status:** `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` (scoped to N01_media_assets only — not application-wide)

## What this slice closed

Slice 2F-31 left N01_media_assets at 233/262 canonical coverage with exactly 5
routes blocked because their remediation required application files outside
2F-31's frozen allow-list:

1. `POST /v1/media/upload`
2. `POST /v1/media/{media_id}/replace`
3. `POST /v1/media/upload/initiate`
4. `POST /v1/media/upload/{session_id}/confirm`
5. `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}`

This slice expanded the allow-list narrowly (see
[expanded-application-file-allow-list.md](expanded-application-file-allow-list.md)),
closed authorization and privacy gaps on all 5, and investigated database/
storage domain integrity — which remains genuinely unresolved (see
[database-storage-integrity-report.md](database-storage-integrity-report.md)),
hence the `_DOMAIN_INTEGRITY_BLOCKED` suffix on the final status.

## Coverage

| | Before (2F-31) | After (2F-31A) |
|---|---|---|
| Denominator | 262 | 262 (unchanged) |
| Protected | 233 | 238 (+5) |
| Unprotected | 29 | 24 |
| Canonical hash | `af8388463ac3dbfa` | `1f7891798eb8382f` |
| Matrix hash | `3066e137e9a23c19` | `abac4ae72e8ab1d4` |

## What was fixed, by workstream

- **WS1** — reverted historical-artifact contamination introduced in a prior
  session (2F-21/2F-23 point-in-time CSVs had been rewritten instead of
  fixing the tests that read them). Restored byte-true values; fixed the
  tests via the repository's existing `PROTECTED_BY_LATER_SLICE` pattern.
- **WS2** — added `require_mutation_access_scope`, a minimal scope-only guard,
  and applied it to `upload_media`/`replace_media` (mixed-persona routes that
  must NOT become staff-only).
- **WS3/WS4** — `MediaService` now takes trusted `actor_role`/`actor_tenant_id`
  context from the router dependency (never the client body), and
  `initiate_upload`/`confirm_upload`/`delete_file` all enforce it before
  touching the database.
- **WS5** — `MediaAccessService`/`MediaAssetService` object-ownership checks
  were verified intact and left unmodified (no evidence required touching
  them for these 5 routes).
- **WS6** — found and fixed one real storage-authority gap: `initiate_upload`
  concatenated the client-supplied `file_name` unsanitized into the storage
  key. Fixed to strip to a basename before use.
- **WS7** — investigated database/storage mutation ordering; found a real,
  currently-unaddressed integrity gap (`confirm_upload` materializes a
  `MediaFile` DB row without verifying the object actually exists in
  storage). Not fixed this slice (out of the authorization/privacy scope
  this mission authorized) — reported and the status reflects it.
- **WS8/WS9** — audited connected reads and alternate call paths; no bypass
  found.

## Regression

Full `tests/test_phase2f*.py` suite: **2289 passed, 0 failed** after
rebaselining ~15 cascading test files whose live-state assertions moved with
the canonical coverage change (see [regression-report.md](regression-report.md)).

## Scope discipline

- No route outside the 5 was modified.
- No new module was selected for the next slice.
- This status applies to N01_media_assets only. See
  [known-limitations.md](known-limitations.md) and
  [product-decisions-required.md](product-decisions-required.md).
