# CUSTOMER-L5-06 — Upload Lifecycle

## Real Lifecycle (`domain/media-item.ts`)

```
SELECTED
  → (validateMediaCandidate fails) → INVALID [terminal]
  → (compression via expo-image-manipulator)
  → UPLOADING
      → (POST /v1/media/upload fails) → UPLOAD_FAILED [retryable, capped at 3]
      → (succeeds) → UPLOADED (mediaAssetId set)
  → LINKING
      → (POST /{draftId}/photos fails) → LINK_FAILED [retryable, capped at 3]
      → (succeeds) → LINKED [terminal]

DELETING → DELETED [terminal] — only reachable for an already-`LINKED`
  item's underlying asset (see media-architecture.md's documented gap: the
  draft's own photo_urls list cannot be updated to remove the link)
```

Deliberately excludes the spec's `PREPARING`, `READY`, `AUTHORIZING`,
`UPLOAD_PAUSED`, `FINALIZING`, `FINALIZATION_FAILED`, `EXPIRED`,
`CANCELLED` states — no signed-URL authorization step exists (direct
multipart), no separate finalization step exists (the upload endpoint is
synchronous and atomic), and no upload-in-progress pause/cancel affordance
was built this sprint (no native XHR/`expo-file-system` uploader is used,
so there is no mid-flight request to pause or cancel — only the whole
`fetch` promise, which is not surfaced as a customer-facing cancel action
this pass).

## Failure and Retry Transitions

| Failure point | Resulting state | Retryable | What retry does |
|---|---|---|---|
| Client-side validation (`validateMediaCandidate`) | `INVALID` | No | N/A — customer must pick a different file |
| Compression (`expo-image-manipulator` throws) | Caught, surfaced as `UPLOAD_FAILED` | Yes | Re-attempts compression + upload from the original picked URI |
| `POST /v1/media/upload` fails | `UPLOAD_FAILED` | Yes (up to 3x) | Re-attempts the full upload |
| `POST /{draftId}/photos` fails after a successful upload | `LINK_FAILED` | Yes (up to 3x) | Re-attempts only the link call — the already-uploaded asset is **not** re-uploaded, avoiding an orphaned duplicate |

## Duplicate-Upload Protection

If the binary upload succeeds but the link call fails or times out, retry
only re-attempts the link step (`LINK_FAILED` → retry calls
`draftApi.linkPhoto` again, not `mediaApi.uploadBookingPhoto`) — the
already-created `MediaAsset` row's `id`/`preview_url` is retained in
`MediaItem.mediaAssetId` from the successful upload, so a retry can never
create a second asset for the same picked file. This is a real,
structural guarantee from the state machine's design, not a
server-side idempotency key (none exists for this endpoint — see
contract-matrix.md).

## What "Timeout After Upload" Actually Means Here

CUSTOMER-L5-06 §32 asks for detecting whether an object already exists
after a lost response. Since this client's upload is a single synchronous
multipart POST (not a two-phase authorize-then-upload flow), a lost
response after a successful server-side `INSERT` means the client simply
never learns the new asset's ID — there is no way for this client to
"detect" the orphan asset already created server-side (no idempotency key
was sent, and no "list my most recent uploads" reconciliation was built
this sprint). The honest behavior: the upload is reported as failed to the
customer (since the response was lost), and a retry creates a **second**
asset. This is a real, disclosed limitation — see known-gaps.md — not
silently pretended away.
