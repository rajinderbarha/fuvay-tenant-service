# Slice 2F-18A — Implementation Summary

## Mission
Close the object-level authorization, privacy, and attachment-ownership gaps
that Slice 2F-18 left open (route-level guards were fixed; technician
tenant-wide access, attachment ownership, and thread-error privacy
equivalence were flagged `PRODUCT_DECISION_REQUIRED`/`known-limitations`
rather than fixed).

## What was fixed

### 1. Technician chat policy — from tenant-wide to assignment/participant-scoped
Previously (2F-18), `staff_chat_router` passed a hardcoded `RECIP_STAFF`
actor_type for EVERY caller, including technicians — so
`validate_thread_access`'s provider/staff branch (tenant-match only) applied
equally to technicians, granting them the same tenant-wide visibility as
office staff. Fixed:
- New `RECIP_TECHNICIAN` constant (`constants.py`).
- `provider_router.py`'s new `_staff_actor_type(u)` helper derives the real
  actor_type from the caller's actual role (`technician` vs `staff`) instead
  of hardcoding `RECIP_STAFF` — used by all 5 `staff_chat_router` routes.
- `chat_service.validate_thread_access` gained a dedicated `RECIP_TECHNICIAN`
  branch (ratified interim policy from this slice's mission): a technician
  is granted access to a thread ONLY if (a) currently assigned
  (`ServiceJob.assigned_staff_id == technician`, resolved LIVE from the
  thread's linked record, never from a stale participant snapshot) for
  resolvable record types (`service_job`, `service_booking`), or (b) has an
  ACTIVE (`left_at IS NULL`) participant row for unresolvable record types.
  Tenant membership alone is no longer sufficient for a technician.
- `list_threads`'s tenant-wide branch (`actor_type in (RECIP_PROVIDER,
  RECIP_STAFF)`) now naturally excludes `RECIP_TECHNICIAN` — falls through
  to the existing participant-scoped branch.
- Consequence: a technician assigned to Job A cannot see or access Job B's
  thread even though both belong to the same tenant; a reassigned
  technician loses access to their former job's thread on next check
  (live assignment lookup, not a cached participant flag).

### 2. Thread-access error privacy equivalence
`validate_thread_access` previously raised `ERR_CHAT_THREAD_ACCESS_DENIED`
(→ 403, per `app/exceptions.py`'s generic domain-code mapping) for a
real-but-unauthorized thread, distinguishable from `ERR_CHAT_THREAD_NOT_FOUND`
(→ 404) for a genuinely nonexistent one. Fixed: every denial branch
(customer, technician, provider/staff, generic participant fallback) now
raises `ERR_CHAT_THREAD_NOT_FOUND` — foreign and missing threads are now
externally identical (same status code, same error_code), matching the
established Booking-series precedent
(`BOOKING_ACCESS_DENIED` → 404 in `app/schemas/base.py`).

### 3. Attachment/media ownership — ATTACHMENT_MODEL_SUPPORTED disposition
`media_ids` were previously accepted with zero validation. A real,
pre-existing media engine (`app.engines.media.models.MediaAsset`, with
`tenant_id`/`owner_id`/`uploaded_by_user_id` columns) already exists in this
codebase — no new upload infrastructure was built. Fixed:
`ChatMessageService._validate_attachments` now resolves every referenced
`media_id` against `MediaAsset` and rejects (same error code,
`CHAT_ATTACHMENT_NOT_FOUND`, for both missing AND cross-tenant, again for
privacy equivalence) before any message is persisted.

## What was investigated and confirmed already correct (no code change)
- **Recipient-owned notification actions** (`mark_notification_read`,
  `mark_all_read`, `update_preference`) were already strictly principal-scoped
  by `user_id` — re-verified, not re-fixed.
- **Tenant-wide announcements**: confirmed (again) that no such capability
  exists anywhere in this router — `TECHNICIAN_NOT_SUPPORTED`/not
  applicable, not a gap.
- **Customer-router object ownership**: `require_customer` (2F-18) plus the
  pre-existing/now-privacy-fixed `get_thread`/`validate_thread_access`
  object checks together satisfy Workstream 14/8's requirements — no
  additional service-layer change was needed beyond the privacy-equivalence
  fix (which also applies to the customer path).
- **Sender identity, visibility-enum validation, non-admin visibility
  escalation, notification preference registry validation, create_thread
  tenant/customer ownership** — all confirmed unchanged and intact from
  2F-18, re-verified by this slice's regression suite, not modified.

## Coverage
Still **200/226** — this slice deepened the OBJECT-level policy behind the
10 routes 2F-18 already router-guard-protected; it did not change which
routes are counted or their `guard_status` (the canonical CSV's convention
is router-dependency-based, unchanged). What changed is that the technician
object-policy gap that made 2F-18's `DOMAIN_INTEGRITY_BLOCKED` status
honest is now closed — see `canonical-coverage-reconciliation.md`.

## Tests
26 new tests (`tests/test_phase2f18a_platform_notifications_technician_privacy.py`),
all passing. All prior platform_notifications suites (2F-18's 49 tests,
pre-existing mocked suites) still pass; 2 pre-existing tests needed
expected updates (error-code assertion + source-inspection string), both
consequences of the deliberate policy changes above.

## Final status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED** —
see `approval-gate.md`.
