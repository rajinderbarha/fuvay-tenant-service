# Product Decisions Required

## 1. Office (tenant_owner/staff) unclaimed-asset access remains tenant-wide
This slice narrowed the technician case specifically; office personas
retain the existing tenant+customer-match policy (not uploader-restricted).
**Question for product**: should office unclaimed-asset access also be
narrowed (e.g., to the customer-relationship-owning staff only), or is
tenant-wide office oversight an intentional, permanent design choice?

## 2. Real schema-backed claim relationship
The `metadata_json.chat_thread_id` convention (2F-18C, hardened this
slice) is a pragmatic no-migration workaround. **Question for
product/engineering**: should a future migration-permitted slice add a
first-class, indexed `MediaAsset.linked_thread_id` column (or a join
table), making claim state queryable/reportable and removing the JSONB
parsing/fail-closed complexity this and the prior slice had to build?

## 3. ServiceJob cancellation/completion access time-boxing
Neither claimed nor unclaimed technician access is affected by Job status
(cancelled/completed Jobs behave identically to active ones).
**Question for product**: should completed/cancelled Job media access
expire or become read-only-forever for the last assigned technician?

## 4. Claim-writer scope if new upload paths are added
Currently exactly two writers exist and both are hardened. **Question for
product/engineering**: if a future slice adds a new media-upload entry
point (e.g., a dedicated chat-attachment upload endpoint, currently
absent — chat attachments are uploaded via the generic `/v1/media` upload
route and then referenced by ID), should that new endpoint be required to
go through the SAME `_strip_claim_key` defensive stripping this slice
added to the generic `upload()` method?
