# Product Decisions Required

## 1. Technician chat visibility — tenant-wide vs. assignment-limited
**Current (unchanged) behavior**: any staff/technician user of a tenant can
list, read, and reply to EVERY chat thread belonging to that tenant, not
only threads for jobs currently assigned to them.

**Question for product**: should technician access be restricted to only
their currently-assigned job's thread (or threads they were added to as a
participant)? If so:
- Should access be revoked immediately on reassignment, or should a
  previously-assigned technician retain read access to history?
- Should this apply to `technician` only, or also to `staff` (who may
  legitimately need cross-job visibility for dispatch/coordination)?

**Why not decided here**: the existing tenant-wide design is explicitly
intentional (documented in `chat_service.py`'s own code comment) and is
actively relied upon by the tenant-portal's staff chat screen and the
mobile staff-app's chat screen (confirmed in `frontend-mobile-exposure-audit.md`).
Narrowing it without product sign-off risks breaking a currently-working
handoff flow. This is why the final status for this slice is
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` rather than a fully closed
status — see `approval-gate.md`.

## 2. Provider/customer thread-access privacy equivalence
`get_thread` currently returns two distinct error codes for "doesn't
exist" (`CHAT_THREAD_NOT_FOUND`) vs. "exists but belongs to another
tenant/customer" (`CHAT_THREAD_ACCESS_DENIED`) — distinguishable by error
code (though both are 4xx and neither leaks thread content). Other modules
in this initiative (Booking) unified this into a single privacy-safe 404.
**Question for product/security**: is unifying this for chat threads worth
the behavior change, given no content leak currently exists (only
existence-vs-access distinguishability)? Flagged, not fixed, to avoid
scope creep into a broader privacy-equivalence pass across the whole
module without an explicit go-ahead.

## 3. Media attachment ownership validation
`media_ids`/`media_urls` on chat messages are accepted with no check that
the referenced asset belongs to the tenant/thread/sender. Building this
validation requires a dependency on the media engine's ownership model,
which is out of this slice's scope (`OUT OF SCOPE: do not build attachment
infrastructure`). Flagged for a future slice or a bundled fix alongside a
media-engine-focused slice.
