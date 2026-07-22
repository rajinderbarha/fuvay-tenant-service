# Participant and Assignment Revocation

## Re-verified (unchanged from 2F-18C, no code path touched this slice)
- Participant removal → thread read denied → future message read denied →
  claimed-attachment retrieval denied (all via `validate_thread_access`'s
  `left_at` filter, reused at retrieval since 2F-18C).
- Technician reassignment/unassignment → `_resolve_job_for_thread`'s LIVE
  `ServiceJob.assigned_staff_id` lookup means the very next access attempt
  (thread OR claimed-media retrieval) re-evaluates current assignment,
  not a cached snapshot — unchanged, re-confirmed.

## New this slice: unclaimed-asset access also has an implicit revocation property
Since a technician's UNCLAIMED-asset access now requires
`uploaded_by_user_id` match (not assignment), technician reassignment has
NO bearing on unclaimed-asset access at all — it was never
assignment-gated to begin with under the new rule, it is uploader-gated,
which cannot be "revoked" by reassignment (the technician remains the
historical uploader regardless of current Job assignment). This is
intentional and consistent: once claimed, the CLAIMED-asset rule
(assignment-gated) takes over and IS subject to reassignment revocation,
as established in 2F-18C.

## ServiceJob cancellation / completion
Not separately modeled — `_resolve_job_for_thread` does not filter on Job
status, and this slice did not add such a filter (carried forward,
unchanged limitation from 2F-18A/2F-18C — see `known-limitations.md`).

## Customer removal
No "remove a customer from a thread" capability exists anywhere in this
codebase (confirmed absent, unchanged) — a `ChatThread.customer_id` is
fixed at creation and never modified by any writer.

## Thread archive/close
`THREAD_CLOSED`/`ARCHIVED`/`BLOCKED` statuses block NEW message sends
(`TERMINAL_THREAD_STATUSES` check, unchanged since Sprint 27) but do NOT
block reads or existing-attachment retrieval — this is pre-existing,
intentional behavior (closed conversations remain readable for history)
and was not changed this slice.

## Historical-access policy for previously-returned URLs
As established in `serializer-url-audit.csv`: no permanent, unauthenticated
URL is ever returned for a private `chat_attachment` asset — every
retrieval re-runs live authorization. There is therefore no "previously
issued URL that can't be revoked" problem to document for this specific
asset type — a URL a client cached from BEFORE their access was revoked
still points to the authenticated API path, which will now correctly deny
them.
