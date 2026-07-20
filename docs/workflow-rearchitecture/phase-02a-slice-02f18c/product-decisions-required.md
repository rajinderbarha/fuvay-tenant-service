# Product Decisions Required

## 1. Unclaimed chat_attachment assets remain tenant-wide viewable
Before an asset's FIRST successful attach, it has no thread claim and is
still viewable per `MediaAccessService`'s existing, unmodified
tenant-wide-for-office/technician policy. **Question for product**:
should upload-time or a dedicated pre-claim check restrict this window
further (e.g., only the uploader can view an unclaimed `chat_attachment`
asset)? Would require modifying `access.py`'s core logic, a larger
change than this slice's scope permits.

## 2. `_load`'s lifecycle filter is narrower than attach-time validation
`MediaAssetService._load` only excludes `status == "deleted"`; a
`chat_attachment` asset with `status == "quarantined"` is rejected at
ATTACH time (2F-18B) but still retrievable if otherwise authorized.
**Question for product**: should `_load`'s filter be broadened to match
(`status != "active"` generally), and if so, should that be scoped to
`chat_attachment` only or applied app-wide (affecting every media
context's retrieval)?

## 3. Job/thread lineage via schema change
The thread-claim lock (`metadata_json.chat_thread_id`) is a pragmatic,
no-migration workaround. **Question for product/engineering**: is a real
schema addition (e.g. `MediaAsset.linked_thread_id` or a join table)
warranted in a future migration-permitted slice, to make this lineage a
first-class, indexed, queryable relationship instead of an opaque JSONB
value?

## 4. Non-`chat_attachment` retrieval privacy remains unfixed
This slice's privacy-equivalence fix is scoped to `chat_attachment`
context only. **Question for product/security**: should the same
unification (missing vs. denied → both 404) be extended to every OTHER
media context app-wide in a dedicated future slice?

## 5. Participant-removal revocation for non-chat-attachment media
This slice's revocation fix only applies to CLAIMED `chat_attachment`
assets. **Question for product**: should thread-participant removal have
any bearing on OTHER media contexts a removed participant might have
accessed via the same thread (there are none currently, since
`chat_attachment` is the only context this router permits, but this may
change if a future slice adds other contexts to chat).
