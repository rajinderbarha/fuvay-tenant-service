# Media Error Privacy Equivalence

## Within `platform_notifications`'s attach-time check (this slice — fully equivalent)
| Scenario | error_code | HTTP status |
|---|---|---|
| Missing asset | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| Wrong `media_context` | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| Deleted/inactive asset | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| Cross-tenant asset | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| Cross-customer asset (same tenant) | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| `MediaAccessService` denial (any of its 3 internal codes) | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |
| Malformed `media_id` | `CHAT_ATTACHMENT_NOT_FOUND` | 404 |

Every one of the 7 rejection reasons above collapses to the SAME error
code and HTTP status at the `platform_notifications` boundary — a caller
attaching an attachment reference cannot learn WHY it was rejected, only
that it was.

## At the media engine's own retrieval routes (`GET /v1/media/{id}*`) — NOT equivalent, pre-existing gap
| Scenario | error_code | Notes |
|---|---|---|
| Missing asset | `NOT_FOUND` (generic, via `NotFoundException`) | 404 |
| Cross-tenant/cross-customer/generic denial | `MEDIA_TENANT_SCOPE_VIOLATION` / `MEDIA_CUSTOMER_SCOPE_VIOLATION` / `MEDIA_ACCESS_DENIED` | none of these match `_domain_code_status`'s `NOT_FOUND`/`ACCESS_DENIED`/`DENIED`/`FORBIDDEN` substrings exactly for the two `*_VIOLATION` codes — they fall to the 422 default branch, distinct from the 404 "missing" case |

This is a genuine, DISTINGUISHABLE-by-status-code gap in the general media
engine's retrieval path — see `attachment-download-read-authority.md` for
why it is documented here rather than fixed (out of this slice's
`platform_notifications`-only scope; would require modifying
`app/engines/media/` and potentially `app/schemas/base.py`'s error map,
affecting every engine that uses media, not just chat).

## Internal logs preserve exact diagnostics
`ServiceOSException`'s `detail`/`blocking_rule`/`context` fields (used by
`MediaAccessService`) still carry the precise reason internally/in logs —
only the EXTERNAL, client-facing surface at the
`platform_notifications` boundary is unified. This matches the same
pattern used for thread-access privacy in 2F-18A.
