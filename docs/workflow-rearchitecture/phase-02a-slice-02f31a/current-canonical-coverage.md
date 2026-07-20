# Current Canonical Coverage (WS12)

As of the end of Slice 2F-31A:

- **Denominator:** 262 (unchanged from 2F-31)
- **Protected:** 238 (233 + 5 residual N01 closures)
- **Unprotected:** 24
- **Canonical hash:** `1f7891798eb8382f`
- **Matrix hash:** `abac4ae72e8ab1d4`

This is a LIVE figure that will move again as future slices close more
routes. This figure does NOT mean the application is fully secured — 24
routes remain unprotected across the whole application, tracked in the
canonical CSV and various slices' held/queued sets.

Scoped to N01_media_assets specifically: all 5 previously-blocked residual
routes are now protected on authorization and privacy grounds; one
data-integrity gap remains (see
[database-storage-integrity-report.md](database-storage-integrity-report.md)),
which is why the final status carries the `_DOMAIN_INTEGRITY_BLOCKED`
qualifier rather than a fully-closed status.
