# Claim Writer Reverification

Re-audited both existing writers of `MediaAsset.metadata_json`
(`upload()`, `replace_asset()`) against this slice's new authorization
changes — confirms the 2F-18D writer audit's conclusions still hold, with
one addition.

| Requirement | Status |
|---|---|
| Upload cannot create a claim | Unchanged from 2F-18D — `_strip_claim_key` still strips any `chat_thread_id` before persisting |
| Replace cannot delete or replace a claim | Unchanged from 2F-18D — `metadata_json=old_asset.metadata_json or {}` still copies verbatim; this slice's NEW authorization check (`_assert_chat_attachment_replace_authority`) runs BEFORE that copy step, so a denied replace never reaches it either — reconfirmed, not weakened |
| Worker metadata updates preserve the claim | Still not applicable — confirmed (again) that no worker/pipeline writer of `metadata_json` exists anywhere in this codebase |
| Unknown future metadata fields merged safely | Unchanged — both writers operate on `dict(...)` copies, never blind-overwrite the whole object with a client-supplied dict |
| Non-dict metadata fails closed | Unchanged from 2F-18D, both at attach time (`chat_service._validate_attachments`) and retrieval time (`MediaAssetService._assert_chat_thread_authority`) |
| Conflicting claim values fail closed | Unchanged from 2F-18C/2F-18D |

## New this slice: `replace_asset`'s authorization now ALSO gates the lifecycle-check path
Since `_assert_chat_attachment_lifecycle` runs before
`_assert_chat_attachment_replace_authority` in `replace_asset` (this
slice), a caller cannot even reach the authorization question for a
deleted/inactive claimed asset — the lifecycle check denies first. This
means the claim on an already-deleted/inactive asset is doubly protected:
neither an unauthorized user NOR an otherwise-authorized user can trigger
any write against it via `replace_asset`, since the method returns
(raises) before constructing the new row in either case.
