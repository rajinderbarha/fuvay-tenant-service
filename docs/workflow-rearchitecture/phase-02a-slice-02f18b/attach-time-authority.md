# Attach-Time Authority

## Validation order in `send_message` (unchanged ordering, new step added)
1. Authenticate / authorize persona+scope (router dependency layer).
2. Thread exists (`ERR_CHAT_THREAD_NOT_FOUND`).
3. Thread not terminal (`ERR_CHAT_THREAD_CLOSED`).
4. Thread/participant/assignment authority (`validate_thread_access`,
   includes 2F-18A's technician policy).
5. `can_send` participant flag.
6. Message has content.
7. Visibility enum + non-admin restriction.
8. **Attachment authority (`_validate_attachments`) — this slice, still
   here, strictly before persistence:**
   a. Asset exists.
   b. Asset not soft-deleted / `status == "active"`.
   c. `media_context == "chat_attachment"`.
   d. Tenant match (thread vs. asset).
   e. Customer match (thread vs. asset, when both set).
   f. `MediaAccessService.assert_can_view(actor, asset)` — the acting
      principal is authorized to use this specific asset.
9. Construct `ChatMessage`, `db.add`.
10. Update `thread.last_message_at`.
11. `_notify_other_participants`.
12. `db.commit()`.

Every check in step 8 raises BEFORE step 9 — proven directly by this
slice's tests (`db.add.assert_not_called()` on every new rejected path).

## Requirements checklist
- Principal may access target thread — step 4 (2F-18A, unchanged).
- Principal may send the selected visibility — step 7 (2F-18, unchanged).
- Asset belongs to same tenant — step 8d (2F-18A, unchanged).
- Principal may read/use the asset — step 8f (**this slice, new** — the
  core fix; 2F-18A had NO principal-level check at all, only tenant-level).
- Asset belongs to an authorized parent context — step 8c (**this slice,
  new** — `media_context` taxonomy).
- Asset state permits use — step 8b (**this slice, new**).
- Asset visibility compatible with message visibility — see
  `attachment-visibility-matrix.md`; not independently re-derived beyond
  what `MediaAccessService`'s `is_public`/context checks already encode,
  since `MediaAsset` has no separate visibility enum comparable to
  `ChatMessage.visibility`.
- Customer/technician recipient authorized where visible — covered by
  step 8f (the SAME `MediaAccessService` check applies regardless of who
  will eventually READ the message; the sender's own authority to use the
  asset is what's checked at attach time, per the mission's own framing —
  the different-persona READ path is covered separately in
  `attachment-download-read-authority.md`, which is the media engine's own
  route, re-checked independently at retrieval time).
- Staff-internal asset cannot be attached to customer message — partially
  covered: `media_context` taxonomy (step 8c) ensures only
  `chat_attachment`-context assets are used at all; there is no distinct
  "staff-internal" vs. "customer-facing" sub-context within
  `chat_attachment` in the existing schema, so this specific sub-case
  relies on `MediaAccessService`'s tenant/customer scoping rather than an
  explicit staff-vs-customer content flag — flagged as a residual gap in
  `known-limitations.md`.
- Customer-owned asset cannot be attached to unrelated customer thread —
  step 8e (**this slice, new**).
- Job-linked asset cannot be used in another Job's thread — **NOT
  achievable** with existing data (no `job_id` column on `MediaAsset`) —
  see `known-limitations.md` / `product-decisions-required.md`.
- Cross-conversation substitution fails when conversation linkage exists —
  **NOT achievable** with existing data (no `thread_id`/`message_id`
  column) — same limitation.
