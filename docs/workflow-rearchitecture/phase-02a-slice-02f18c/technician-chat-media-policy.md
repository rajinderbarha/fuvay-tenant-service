# Technician Chat Media Policy

## Corrected classification from 2F-18B
2F-18B's `known-limitations.md` classified "technician tenant-wide media
view" as a pure PRODUCT_POLICY item, out of scope to narrow. This slice's
mission explicitly rejects that framing for the RETRIEVAL path
("Do not claim privacy closure while a technician denied from a thread
can retrieve its media directly" — and separately: "The classification of
technician-wide media access as product-only" is listed among the claims
to correct). Corrected: for CLAIMED `chat_attachment` assets specifically,
technician access is NOW assignment/participant-scoped at retrieval time,
not tenant-wide — this is a SECURITY fix, not merely a product question.

## What changed
`MediaAssetService._assert_chat_thread_authority` (new, this slice) runs
AFTER `MediaAccessService.assert_can_view` succeeds, for
`chat_attachment`-context assets that have been claimed by a thread
(`metadata_json.chat_thread_id` set). It maps the actor's role to a chat
`RECIP_*` type and re-runs `ChatThreadService.validate_thread_access` —
the EXACT SAME rule 2F-18A established for THREAD access — against the
claimed thread.

## Directly tested
| Scenario | Result | Test |
|---|---|---|
| Technician assigned to ServiceJob A retrieves A's thread's media | ALLOWED | `test_assigned_technician_allowed_retrieval` |
| Technician assigned to ServiceJob B retrieves A's thread's media (same tenant) | DENIED | `test_unassigned_technician_denied_retrieval_of_job_thread_media` |
| Same-tenant unassigned technician retrieves any claimed Job-thread media | DENIED | same mechanism — `validate_thread_access`'s `RECIP_TECHNICIAN` branch requires live assignment or active participation, tenant match alone is never sufficient (2F-18A, reused unchanged) |
| Active participant technician (non-Job-resolvable thread) | ALLOWED | covered by `validate_thread_access`'s fallback branch (2F-18A), reused unchanged at retrieval time |
| Removed participant technician | DENIED | `left_at` filter (2F-18A), reused unchanged at retrieval time — see `participant-removal-revocation.md` |
| `super_admin` | ALLOWED (bypasses) | `test_super_admin_bypasses_thread_check` |

## What remains tenant-wide (honestly disclosed, narrower than before)
An UNCLAIMED `chat_attachment` asset (uploaded but never yet successfully
attached to any message) is still viewable by any same-tenant
`tenant_owner`/`staff`/`technician` per `MediaAccessService`'s own,
unmodified, existing policy — because there is no thread to check
authority against yet. This window is now MUCH smaller than before this
slice (only pre-first-use, not indefinitely), but is not eliminated —
closing it fully would require either (a) modifying `access.py`'s
CUSTOMER_CONTEXTS branch to exclude technician from tenant-wide viewing of
un-thread-claimed `chat_attachment` assets specifically (a targeted,
possible follow-up), or (b) restricting upload-time visibility (out of
scope — no upload infrastructure changes permitted). See
`known-limitations.md` and `product-decisions-required.md`.

## No technician-wide access was invented
Every technician media interaction in this slice's test suite is denied
UNLESS a specific, provable assignment or participant relationship exists
— consistent with 2F-18A's "do not invent technician-wide access"
constraint, now extended to media retrieval.
