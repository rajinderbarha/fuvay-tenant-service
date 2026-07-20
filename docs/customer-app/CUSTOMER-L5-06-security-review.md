# CUSTOMER-L5-06 — Security Review

## Ownership Enforcement

- **Draft ownership**: every real endpoint (`get`, `update`, `cancel`,
  `add_photo`) enforces `draft.customer_id == customer_id` server-side
  (`_require_draft`, `service.py`), returning 403
  `HOME_BOOKING_DRAFT_ACCESS_DENIED` on mismatch — verified by reading the
  backend source, not assumed. The client never attempts to enforce this
  itself; the local draft-ID pointer is customer-scoped defensively, but
  the actual security boundary is server-side.
- **Media ownership**: `MediaAccessService.assert_can_view`/
  `assert_can_delete`/`assert_can_replace` (`app/engines/media/access.py`)
  enforce `asset.customer_id == actor.user_id` for `CUSTOMER_CONTEXTS`
  (which includes `booking_issue_photo`) — verified by reading the actual
  access-control code, including the customer-role branch that is checked
  independent of any client-supplied `owner_id`.

## No Sensitive Logging

Verified by grep across `features/booking-draft/` (see the review process
in this doc's companion PR): every `logger.*` call passes only stable IDs
(`mediaAssetId`), booleans, error categories, and enum-like reason strings
— never a local file URI, never a signed/preview URL, never draft content
(`issue_summary`, address fields), never a token. `mediaApi.uploadBookingPhoto`
sends the file binary directly to the backend in the request body; it is
never logged.

## No Full Objects in Route Params

`BookingAssistantScreen` → `BookingDraftScreen` passes only branded IDs
plus three small, bounded strings (`brandId`, `offeringTypeId`,
`issueSummary` — the last capped at 500 characters by
`normalizeShortTextAnswer` back in CUSTOMER-L5-05). `BookingDraftScreen` →
`BookingMediaScreen` passes only `draftId`. No full draft object, no media
asset object, no signed URL, and no customer profile data crosses a route
boundary.

## Preview URL Handling

`preview_url` (`/v1/media/{id}/view`) is access-checked server-side on
every request — it is not a bearer-token-embedded signed URL, so there is
no secret to leak by it appearing in a network log; the *response* it
serves is still protected per-request by the same auth check as any other
endpoint. `resolveAuthorizedPreviewSource` attaches the customer's own
bearer token via request headers (not a URL query parameter), so it never
appears in server access logs or browser history either.

## Cross-Customer Isolation

Both the draft-ID local pointer and the entire React Query cache are
cleared on logout/logout-all (see local-persistence-policy.md and
cache-policy.md) — verified by reading the actual `use-logout.ts`/
`use-logout-all.ts` changes made this sprint, not merely described.

## Input Validation

- File MIME type and size are validated client-side
  (`validateMediaCandidate`) against the real, verified backend limits —
  UX-only, since the backend independently re-validates every upload
  server-side (`MediaValidationService.validate_upload`) and would reject
  anything the client validation might miss or a modified client might
  bypass.
- `issue_summary` sent via the assistant-answer sync is already trimmed,
  control-character-stripped, and length-capped by CUSTOMER-L5-05's
  `normalizeShortTextAnswer` before it ever reaches this sprint's code.

## No Production Mocks

Grepped `features/booking-draft/` for `mock`, `fake`, `TODO`, `FIXME` —
none found. Every draft field and media asset field traces to a real,
schema-validated backend response.

## Disclosed, Real Limitations (Not Vulnerabilities, But Honest Gaps)

- No idempotency key is sent on draft creation or photo upload — a lost
  response after a successful server-side write can result in a duplicate
  draft or duplicate media asset on manual retry (see upload-lifecycle.md
  and known-gaps.md). This is a backend contract gap (no idempotency-key
  support exists on these endpoints), not something this client can close
  on its own.
- No malware/content-moderation scanning exists anywhere in the media
  engine (confirmed absent, not merely undeferred) — an uploaded image is
  immediately `status="active"` and viewable. This is a genuine platform
  gap outside this sprint's scope to build.
