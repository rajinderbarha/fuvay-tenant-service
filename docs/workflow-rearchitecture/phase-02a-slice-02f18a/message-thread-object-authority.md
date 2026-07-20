# Message and Thread Object Authority

## Verified (re-confirmed unchanged from 2F-18, plus this slice's fixes)
- Thread belongs to principal tenant — `create_thread`'s 2F-18 ownership
  check; `validate_thread_access`'s tenant-match branch, now with
  privacy-equivalent errors (this slice).
- Message belongs to thread — `ChatMessage.thread_id` always the
  path-supplied, DB-validated `thread_id`; no route accepts a message-level
  thread override.
- Message author is principal-derived — unchanged from 2F-18
  (`sender-identity-authority.md`), re-confirmed.
- A message cannot move to another thread — no edit/move route exists on
  any router in this module (unchanged).
- A message from Thread A cannot be edited/deleted through Thread B — no
  edit/delete route exists at all on this router (structurally impossible,
  not merely denied).
- Thread `record_id` belongs to the expected parent model — enforced by
  `create_thread`'s 2F-18 `_resolve_record_parties`/ownership check
  (unchanged) and by this slice's `_resolve_job_for_thread`, which ONLY
  ever queries `ServiceJob`/`ServiceBooking` for the two resolvable
  `record_type`s, never any other model.
- Thread visibility (message-level `visibility` field) is enum-validated
  (2F-18, unchanged).
- Client `tenant_id`/`sender_id` cannot override authority — both always
  server-derived (unchanged, 2F-18's `sender-identity-authority.md`).
- Cross-tenant thread IDs are rejected — `validate_thread_access`'s tenant
  match, now privacy-equivalent (this slice).
- Same-tenant UNRELATED thread IDs: for `RECIP_PROVIDER`/`RECIP_STAFF`
  (office persona), a same-tenant thread IS accessible regardless of
  participant status — this is the ratified, intentional
  `STAFF_INTERNAL_CONVERSATION` tenant-wide policy, not a gap. For
  `RECIP_TECHNICIAN`, a same-tenant but unrelated (unassigned, non-participant)
  thread IS now rejected — this slice's core fix
  (`test_technician_tenant_membership_alone_is_not_sufficient`).
