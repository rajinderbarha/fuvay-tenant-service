# Deferred Items - Slice 2F-31

- Remediation of `POST /v1/media/upload` and `POST /v1/media/{media_id}/replace`
  (needs a new scope-only guard - `app/core/permissions.py` change, currently
  forbidden).
- Remediation of all 3 Set B routes on `app/engines/media/router.py` /
  `MediaService` (needs a fresh scope freeze including that router on the
  allow-list).
- Database/storage atomicity proof for media deletion.
- The remaining 22 canonical unprotected routes outside N01 (29 total minus
  the 7 above minus... see current-canonical-coverage.md for the exact set).
- Next module selection - explicitly out of scope.
