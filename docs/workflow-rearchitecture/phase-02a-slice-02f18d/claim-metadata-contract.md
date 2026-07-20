# Claim Metadata Contract

## Structure
The claim lives inside the EXISTING `MediaAsset.metadata_json` JSONB
column (no new column, no migration) as a single key:

```json
{"chat_thread_id": "<uuid string>"}
```

| Field | Server-generated? | Format | Notes |
|---|---|---|---|
| `chat_thread_id` (the claim key) | YES — set ONLY by `chat_service.ChatMessageService._validate_attachments`'s claim-application pass | UUID string (`str(thread.id)`) | The ONLY server-owned key this mechanism defines |
| Claimed-by user ID | NOT tracked | n/a | Not part of the contract — the claim identifies a THREAD, not a claiming user; thread membership itself (via `validate_thread_access`) is what governs who may use a claimed asset, not who claimed it first |
| Claimed-at timestamp | NOT tracked | n/a | Not part of the contract — `MediaAsset.updated_at` (existing column, auto-managed by `ServiceOSBase`) already reflects the last modification time generically |
| Claim version | NOT tracked | n/a | Not needed — the claim is single-valued and immutable once set (see below); no versioning scheme required |
| Asset-context version | NOT tracked | n/a | Not applicable — `media_context` itself is immutable post-upload (no writer ever changes it) |

## Parsing behavior (this slice, both writer and both readers)
| Input | Behavior |
|---|---|
| `metadata_json` is not a dict at all (corrupted/malformed) | Fails closed — treated as an error, NEVER silently treated as "unclaimed" |
| `chat_thread_id` key absent | Unclaimed — first-use policy applies |
| `chat_thread_id` present but `None`/falsy | Unclaimed — first-use policy applies (an explicit `null` is equivalent to absent) |
| `chat_thread_id` present, not a valid UUID string (malformed, or a non-string type like a list/dict) | Fails closed — rejected, never reinterpreted as unclaimed |
| `chat_thread_id` present, valid UUID, matches the current thread | Idempotent reuse — allowed |
| `chat_thread_id` present, valid UUID, does NOT match the current thread | Rejected — cross-conversation reuse denied |
| Referenced thread does not exist (retrieval path only — `ChatThreadService().validate_thread_access` needs a real `ChatThread` row) | Fails closed |
| Referenced thread belongs to a different tenant than the retrieving principal | Fails closed via `validate_thread_access`'s own tenant-match logic (unchanged) |

## Duplicate-key behavior
Not applicable — `chat_thread_id` is the only key this mechanism ever
writes or reads; there is no "duplicate key" concept within a single JSON
object (a JSON object cannot have two keys with the same name by
construction).

## Server-owned, not client-owned
No request schema in `provider_router.py`, `customer_router.py`, or
`new_router.py`'s upload endpoint exposes a `chat_thread_id` or
`metadata_json` field the client can set directly — confirmed by schema
read (see `claim-writer-audit.csv`).
