# Retrieval Lifecycle Policy

## Fixed this slice: `_assert_chat_attachment_lifecycle`
Applied at the START of `get_asset`, `get_local_file_for_serve`, and
`replace_asset` (immediately after `_load`, before any authorization
check even runs), scoped strictly to `media_context == "chat_attachment"`:

```python
if asset.media_context != "chat_attachment":
    return
if asset.deleted_at is not None or asset.status != "active":
    raise NotFoundException("Media", str(media_id))
```

## Requirement checklist
| Requirement | Status |
|---|---|
| Active asset succeeds for authorized principal | Unaffected — `test_active_chat_attachment_passes_lifecycle_check` |
| Soft-deleted asset denied | Fixed — `test_deleted_chat_attachment_rejected` |
| Inactive asset denied | Fixed — covered by the same `status != "active"` check |
| Quarantined asset denied | Fixed — `test_quarantined_chat_attachment_rejected` (any non-`"active"` status string is generically covered, not just `"quarantined"` literally) |
| Failed/unavailable asset denied where represented | Fixed — same generic `status != "active"` mechanism; `MediaAsset` has no separate "failed" status distinct from `status`, so this is covered by construction |
| Wrong `media_context` denied | Unchanged from 2F-18B (attach-time) — this slice's lifecycle check does not apply to non-`chat_attachment` retrieval by design (`test_non_chat_attachment_context_unaffected`), but a wrong-context asset was never reachable via the chat attachment flow to begin with |
| Asset becomes inactive AFTER attachment | Fixed — the lifecycle check runs on EVERY retrieval, not cached from attach time; an asset attached while active that is later marked inactive/deleted is denied on the NEXT retrieval attempt |
| Asset becomes deleted AFTER attachment | Same mechanism |
| Removed participant PLUS inactive asset | Both checks independently deny — whichever runs first (lifecycle check runs before the thread-authority check in the code, so lifecycle denial happens first, but the OUTCOME — denied — is identical either way) |
| Missing vs. inactive vs. unauthorized external behavior | ALL THREE now converge on the SAME `NotFoundException` for `chat_attachment` context (2F-18C's unification, this slice's lifecycle check raises the identical exception type) |

## No stale cached authorization bypasses lifecycle state
Confirmed by construction: there is no caching layer anywhere in this
retrieval chain — every `get_asset`/`get_local_file_for_serve` call
re-executes `_load` (a fresh DB query) and re-runs every check, including
this slice's lifecycle check, from scratch. A `chat_attachment` asset
that was valid a moment ago and is deleted/deactivated between two
retrieval calls is denied on the second call.

## Scoped narrowly, not applied app-wide
Every OTHER media context's lifecycle handling (via `_load`'s pre-existing
`status != "deleted"` filter alone) is completely unchanged — this fix
does not alter retrieval behavior for `provider_document`,
`customer_profile_photo`, or any other context, consistent with this
slice's mandate to touch only the direct chat_attachment chain.
