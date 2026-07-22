# Media Error Privacy Equivalence

## Corrected from 2F-18B
2F-18B documented (`attachment-download-read-authority.md`,
`media-error-privacy-equivalence.md`) that the media engine's own
retrieval routes were NOT privacy-equivalent (missing → 404 generic
`NOT_FOUND`; denied → distinct `MEDIA_*_VIOLATION` codes, falling to a 422
default) and classified fixing it as out of scope ("general media engine
gap... app-wide blast radius"). This slice's mission explicitly corrects
that framing: "The claim that the media engine retrieval gap is unrelated
to chat privacy" must be corrected, because it DIRECTLY blocks
`platform_notifications` privacy closure per Workstream 6's own text.

## Fixed, scoped to `chat_attachment` context only
`MediaAssetService.get_asset` and `get_local_file_for_serve` now catch
`ServiceOSException` (from EITHER `assert_can_view` OR this slice's new
`_assert_chat_thread_authority`) and, when `asset.media_context ==
"chat_attachment"`, re-raise as `NotFoundException` — the SAME exception
type/error_code/status (404) a genuinely missing `media_id` produces via
`_load`.

## Verified end-to-end (not just at the `platform_notifications` boundary)
| Scenario | error_code | HTTP status |
|---|---|---|
| Missing `media_id` | `NOT_FOUND` (via `_load`'s `NotFoundException`) | 404 |
| Cross-tenant `chat_attachment` asset | `NOT_FOUND` (this slice — was `MEDIA_TENANT_SCOPE_VIOLATION`) | 404 |
| Cross-customer `chat_attachment` asset | `NOT_FOUND` (this slice — was `MEDIA_CUSTOMER_SCOPE_VIOLATION`) | 404 |
| Unassigned technician, claimed Job-thread asset | `NOT_FOUND` (this slice, NEW check) | 404 |
| Removed participant, claimed asset | `NOT_FOUND` (this slice, NEW check) | 404 |
| Deleted/inactive `chat_attachment` asset | Falls to `_load`'s own `status != "deleted"` filter — see note below | 404 (if `status == "deleted"` exactly) |
| Wrong-context asset (e.g. `provider_document`) referenced directly by ID | Unaffected by this slice — `MediaAccessService`'s normal, unmodified rule applies (NOT unified, since this fix is scoped to `chat_attachment` only) | unchanged from 2F-18B (distinguishable, out of scope) |

Test coverage: `test_get_asset_unifies_missing_and_denied_to_not_found`
proves the unification directly (a denied customer-role retrieval of a
`chat_attachment` asset raises `NotFoundException`, not
`ServiceOSException`).

## Note: `_load`'s own lifecycle filter is narrower than `chat_service`'s
`MediaAssetService._load` only excludes `status == "deleted"` (a specific
string) — NOT the fuller `status != "active"` check `chat_service`'s
ATTACH-time validation uses (2F-18B). A `chat_attachment` asset with
`status == "quarantined"` (rejected at ATTACH time) is still `_load`-able
and passes `assert_can_view` at RETRIEVAL time if otherwise authorized —
this is a genuine, narrower-scope inconsistency between attach-time and
retrieval-time lifecycle strictness, not fixed this slice (would require
modifying `_load`, a shared helper used by all `MediaAssetService`
methods for every context, out of this slice's narrow "smallest safe
correction" mandate) — flagged in `known-limitations.md`.

## Not unified beyond `chat_attachment`
Every OTHER media context's retrieval-error behavior is completely
unchanged — this fix does not touch `assert_can_view`'s core logic or any
other context's error handling, keeping the blast radius to exactly what
this slice's mission scopes ("Changes under app/engines/media are
permitted only when they are the smallest safe correction required by
chat-attachment retrieval").
