# Product Decisions Required

## 1. Attachment uploader-level authorization (carried forward from `attachment-media-ownership.md`)
Currently, any same-tenant caller may reference any same-tenant
`MediaAsset` in a chat message — tenant-match is enforced, but
`uploaded_by_user_id`/`owner_id` is not cross-checked against the sender or
the thread's parent record. **Question for product**: should attachment
references be restricted to assets uploaded by the sender, or assets
already linked to the same parent Job/Booking/Complaint the thread is
linked to? Building this requires reading `app/engines/media/access.py`'s
own authorization semantics, which was not done this slice (judged out of
proportion without a dedicated pass on that engine).

## 2. Message-level attachment binding
Attachments are referenced via `ChatMessage.media_urls` (JSONB), not a
formal join table — so "belongs to the exact conversation/message" (beyond
tenant-match) cannot be independently verified without either a schema
change (forbidden — no migrations this slice) or trusting the tenant-match
check as sufficient. **Question for product/security**: is tenant-level
attachment ownership sufficient for this module's risk profile, or does a
future migration need to add a formal attachment-binding table?

## 3. Completed/cancelled Job technician read access
A technician who was the LAST assigned technician on a since-completed Job
retains thread-read access indefinitely (as long as `assigned_staff_id`
still points to them — jobs are not reassigned away after completion in
the existing workflow). **Question for product**: should completed-job
threads become read-only-forever-accessible to the last assigned
technician (current, unchanged behavior), or should access time-box out
after job completion?

## 4. Technician `list_threads` reassignment-timing gap
A technician's thread LIST is participant-row-scoped (added automatically
at thread-creation time via `_provider_participants`); a technician
reassigned to an EXISTING job mid-stream (after the thread already exists)
will not see it in their list until a participant row is added for them —
even though `get_thread`/`send_message`'s live-assignment check WOULD let
them access it directly if they had the thread ID. **Question for
product**: should `list_threads` also perform a live-assignment lookup
(more expensive, would require a join against `ServiceJob.assigned_staff_id`
for every listed thread) so the list matches what a technician can actually
access?
