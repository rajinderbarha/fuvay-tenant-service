# Product Decisions Required

## 1. Cross-Job/cross-conversation media lineage (carried forward, deepened)
`MediaAsset` has no `job_id`/`thread_id`/`message_id` column — same-Job and
same-conversation substitution within the same tenant+customer cannot be
structurally proven or rejected with current data. **Question for
product/engineering**: is a schema change (new nullable FK-style columns
on `MediaAsset`, or a join table) warranted to close this, given it
requires a migration (explicitly out of scope for this and prior slices)?

## 2. Technician tenant-wide media view (existing platform policy, not introduced here)
`MediaAccessService.assert_can_view` grants `tenant_owner`/`staff`/
`technician` visibility into ANY customer-context asset in their own
tenant — broader than the Job-assignment policy 2F-18A introduced for
THREAD access. **Question for product**: should media access for
technicians be narrowed to match thread-assignment scope specifically for
`chat_attachment`-context assets? This would require modifying
`app/engines/media/access.py` itself (app-wide blast radius, affecting
every context, not just chat) — out of this slice's scope to decide
unilaterally.

## 3. Media engine retrieval-path error privacy (pre-existing, general gap)
`GET /v1/media/{id}*` routes distinguish missing (`NOT_FOUND`, 404) from
denied (`MEDIA_*_VIOLATION`, likely 422 via the generic domain-code
mapping) — not privacy-equivalent. **Question for product/security**: is
this worth fixing app-wide (affecting every engine that references media,
not just chat), and if so, should it follow the same "unify to 404"
pattern established for Booking/quote_checklist/chat threads?

## 4. Removed chat participant retaining generic media access
A technician/staff member removed from a chat thread's participant list
loses THREAD access immediately (2F-18A), but if they separately have
generic tenant-role media view authority (item 2 above) and still know a
`media_id` from before removal, they can still retrieve the raw file via
the media engine's own routes — the two authorization systems (thread
participation, media access) don't share revocation state. **Question for
product**: is this an acceptable gap (media access and conversation access
are intentionally separate concerns), or should removal from a
conversation also revoke access to media referenced within it?

## 5. `staff_send_message` never forwards `media_ids`
The schema accepts the field but the router silently drops it — not
insecure (no attachment is ever actually processed), but a functional gap.
**Question for product**: should staff/technician chat support
attachments at all, and if so, should this be wired up in a future slice?
