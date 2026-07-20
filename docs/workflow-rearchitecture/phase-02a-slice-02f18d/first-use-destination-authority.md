# First-Use Destination Authority

## Classification per persona (Workstream 2's required taxonomy)

| Persona | Classification | Evidence used |
|---|---|---|
| Customer attaching own upload to own thread | `CUSTOMER_SELECTS_OWN_THREAD` | `asset.customer_id == actor.user_id` (assert_can_view) AND `thread.customer_id == asset.customer_id` (2F-18B) |
| Tenant owner/staff attaching a customer's asset to that customer's thread | `OWNER_STAFF_SELECTS_COMPATIBLE_CUSTOMER_THREAD` | tenant match + `thread.customer_id == asset.customer_id` (2F-18B) + `assert_can_view`'s tenant-wide office rule |
| Technician attaching their OWN upload to their assigned Job's thread | `ASSIGNED_TECHNICIAN_SELECTS_ASSIGNED_JOB_THREAD`, additionally requiring `UPLOADER_SELECTS_AUTHORIZED_THREAD` evidence | `validate_thread_access`'s live ServiceJob-assignment check (2F-18A) PLUS (THIS SLICE) `asset.uploaded_by_user_id == actor.user_id` |
| Technician attaching an asset they did NOT upload, even to their own assigned Job's thread | `AMBIGUOUS_CONTEXT_REJECTED` | THIS SLICE — no evidence proves the technician chose this specific asset for this specific job legitimately, only that they happen to be assigned and tenant-matched |
| Any principal attaching to a thread the media engine has no upload-time record connecting to | `UNSUPPORTED` unless covered by one of the above rules | `MediaAsset` has no `EXISTING_UPLOAD_INTENT_MATCH` evidence available (no upload-session-to-thread linkage exists in this schema) — this classification exists in the taxonomy but has no live instances in the current codebase |

## Why "first thread supplied by the caller" is never sufficient alone
Every approved classification above requires evidence INDEPENDENT of the
caller's own thread-ID choice: customer/tenant/context matching (already
existing columns), or (this slice) uploader identity for technicians. The
mission's explicit prohibition — "Do not treat 'first thread supplied by
the caller' as provenance by itself" — is satisfied because in every
approved case, the SAME evidence that authorizes the ATTACH also
independently constrains WHICH threads are even reachable (a technician
who isn't assigned to a Job can't reach its thread at all;
`validate_thread_access` runs before `_validate_attachments`).

## Where destination intent is ambiguous, reject
The one case genuinely ambiguous with current data — a technician
assigned to Job A1 who did NOT upload the asset in question, attempting
to attach a generic tenant customer-context asset to A1's thread — is
REJECTED (`AMBIGUOUS_CONTEXT_REJECTED`), proven by
`test_technician_cannot_first_claim_unowned_asset`.
