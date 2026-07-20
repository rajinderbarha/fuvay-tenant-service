# Slice 2F-18B — Implementation Summary

## Mission
Close the residual media/attachment authorization gap 2F-18A left open:
2F-18A's `_validate_attachments` only checked that a referenced
`MediaAsset` existed and belonged to the sending thread's own tenant —
tenant equality alone, which the mission explicitly identifies as
insufficient authority. This slice reuses the EXISTING, centralized media
authorization helper (`app.engines.media.access.MediaAccessService`)
instead of a duplicated, weaker tenant-only check, and closes the specific
same-tenant IDOR gaps that check couldn't catch.

## What was fixed

### 1. Reused the existing `MediaAccessService.assert_can_view` helper
Previously, `_validate_attachments` never consulted the media engine's own
access-control policy at all — it re-implemented (poorly) a subset of it.
Fixed: `send_message` now threads the acting `UserContext` (`actor`) through
from all three routers (`provider_router.py`'s `provider_send_message`/
`staff_send_message`, `customer_router.py`'s `send_message`), and
`_validate_attachments` calls `MediaAccessService.assert_can_view(actor,
MediaAssetRecord.from_orm(asset))` — the SAME helper the media engine's own
`view`/`download` routes already use. This directly proves the ACTING
PRINCIPAL (not just the tenant) is authorized to use the asset: a customer
may only reference their own uploads; a tenant_owner/staff/technician may
reference any customer-context asset in their own tenant (existing,
tenant-wide-for-media policy) or their own upload.

### 2. Same-customer lineage using the asset's existing `customer_id` column
2F-18A's tenant-only check could not distinguish Customer A's thread from
Customer B's thread within the same tenant. Fixed: when BOTH the thread and
the asset carry a `customer_id`, they must match — rejects Media B being
attached to Customer A's conversation, using data that already exists on
the model (no new column).

### 3. `media_context` purpose-taxonomy enforcement
The media engine already tags every asset with a `media_context`
(`chat_attachment`, `provider_document`, `customer_profile_photo`, ...).
Fixed: only assets with `media_context == "chat_attachment"` may be
referenced in a chat message — an asset uploaded for an unrelated purpose
is rejected as an unsupported reference, using existing data.

### 4. Lifecycle-state rejection
Fixed: `deleted_at IS NOT NULL` or `status != "active"` (covers soft-delete
and any non-active state such as `quarantined`) is now rejected, using
existing columns.

### 5. Privacy equivalence preserved and extended
Every one of the above checks raises the SAME error code
(`CHAT_ATTACHMENT_NOT_FOUND`) — missing, wrong-context, deleted,
cross-tenant, cross-customer, and access-denied-by-`MediaAccessService` are
all externally indistinguishable.

## What was investigated and found already correct / out of proportion to change
- **Retrieval/download re-authorization** (Workstream 7): `app.engines.media.new_router`'s
  `view_media`/`download_media` routes already call
  `MediaAssetService.get_asset`/`get_local_file_for_serve`, which already
  call `MediaAccessService.assert_can_view` before serving. This is
  PRE-EXISTING, unrelated to `platform_notifications`, and already correct
  — no code change needed or made. See `attachment-download-read-authority.md`.
- **Technician tenant-wide media view**: `MediaAccessService.assert_can_view`'s
  existing policy grants `tenant_owner`/`staff`/`technician` visibility into
  ANY customer-context asset in their own tenant — broader than the
  thread-access assignment policy 2F-18A introduced. This is EXISTING,
  established, platform-wide media policy (not introduced by chat) — per
  this slice's mandate to "reuse the helper directly" and "not duplicate a
  weaker media policy," narrowing it further would mean modifying
  `access.py` itself, which is out of this slice's `platform_notifications`-only
  scope and would ripple across every OTHER engine that uses media
  (profile photos, complaints, reviews, etc.). Documented, not fixed — see
  `known-limitations.md`.
- **Cross-Job/cross-conversation lineage**: `MediaAsset` has no `job_id` or
  `thread_id`/`message_id` column — `owner_type`/`owner_id` are free-form,
  caller-supplied strings at upload time with no guaranteed relationship to
  a specific chat thread. Per the ratified policy's own instruction ("when
  existing fields cannot prove safe attachment authority... do not invent a
  migration"), full same-Job/same-thread lineage enforcement is NOT
  achievable with current data and was not built. This is the slice's
  single largest honestly-disclosed residual gap — see
  `product-decisions-required.md`.

## Coverage
Unchanged at 200/226 — same reasoning as 2F-18A's own reconciliation: this
slice deepened object/attachment-level policy behind the same 10
router-guarded routes; the canonical CSV's router-dependency-based
convention is unaffected. See `canonical-coverage-reconciliation.md`.

## Tests
9 new tests (`tests/test_phase2f18b_platform_notifications_media_authority.py`),
all passing. Combined platform_notifications + media-engine regression: 333
passed, 0 failed. Full repository sweep: see `regression-report.md`.

## Final status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED** —
see `approval-gate.md`.
