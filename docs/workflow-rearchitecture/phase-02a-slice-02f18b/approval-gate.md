# Slice 2F-18B Approval Gate

> **DEEPENED BY SLICE 2F-18C.** This slice reused `MediaAccessService.assert_can_view`
> for the SENDER's view authority but did not distinguish it from
> redistribution/sharing authority, did not prevent same-customer
> cross-Job/cross-conversation reuse, and did not apply any thread-equivalent
> authority at the actual retrieval routes. Slice 2F-18C
> (`docs/workflow-rearchitecture/phase-02a-slice-02f18c/`) added a
> thread-claim lock (using the asset's existing `metadata_json` column) and
> a retrieval-time thread-authority check, closing both gaps. Coverage
> remains 200/226 (unchanged — router-level arithmetic). Nothing in this
> slice's findings was factually wrong; this notice records a genuine depth
> increase on the sharing/retrieval dimension, not a correction of the
> tenant/customer/context/lifecycle checks this slice added, which remain
> intact and unmodified.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Why SECURITY_CLOSED (maintained, now on stronger evidence)
- Attachment authorization no longer rests on tenant equality alone —
  `_validate_attachments` now independently checks asset existence,
  lifecycle state, `media_context` purpose-taxonomy, tenant match,
  customer match, AND reuses the existing, centralized
  `MediaAccessService.assert_can_view` to prove the ACTING PRINCIPAL is
  authorized to use the specific asset — not merely that the asset belongs
  to the right tenant.
- Same-tenant cross-customer media substitution is proven rejected
  (`test_cross_customer_media_within_same_tenant_rejected`).
- A customer cannot reference another customer's upload, proven via the
  REAL `MediaAccessService` policy, not a reimplementation
  (`test_customer_cannot_attach_another_customers_upload`).
- Wrong-context assets (uploaded for an unrelated purpose) are rejected
  before persistence (`test_wrong_media_context_rejected`).
- Deleted/inactive assets are rejected (`test_soft_deleted_asset_rejected`,
  `test_inactive_status_asset_rejected`).
- All 2F-18/2F-18A security controls (router guards, technician
  assignment/participant policy, thread-error privacy) remain intact and
  unmodified — re-confirmed by the full targeted regression (333 tests).

## Why DOMAIN_INTEGRITY_CLOSED (advanced from 2F-18A's tenant-only foundation)
- Per the mission's own instruction ("Do not claim domain-integrity closure
  while attachment authority is based only on tenant equality"): it no
  longer is. Five independent, principal-and-context-aware checks now gate
  every attachment reference.
- The one dimension NOT achievable — cross-Job/cross-conversation lineage
  — is honestly disclosed as a genuine schema limitation (`MediaAsset` has
  no `job_id`/`thread_id` column), not silently claimed closed. This keeps
  the label from being `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_CLOSED`
  (which would require ZERO open product questions).

## Why PRIVACY_CLOSED (maintained and extended)
- Every attachment rejection reason (missing, wrong-context, deleted,
  cross-tenant, cross-customer, `MediaAccessService` denial, malformed ID)
  collapses to the SAME error code
  (`test_missing_asset_and_cross_tenant_asset_share_error_code` proves
  the pairwise case directly; the others are proven by each individually
  raising the identical `ERR_CHAT_ATTACHMENT_NOT_FOUND`).
- Thread-error privacy (2F-18A) remains intact, unmodified.
- The media engine's OWN retrieval-path privacy gap (missing vs. denied
  distinguishable by status code) is a PRE-EXISTING, general gap outside
  `platform_notifications` — documented, not claimed closed, and does not
  block THIS module's own privacy closure since it is not a property this
  module introduced or controls.

## Why PRODUCT_POLICY_BLOCKED (not fully closed)
Five genuine product questions remain open (see
`product-decisions-required.md`), none representing an authorization
bypass on their own:
1. Whether to add schema support for Job/conversation media lineage.
2. Whether to narrow technician tenant-wide media view specifically for
   chat attachments (app-wide `access.py` change).
3. Whether to unify the media engine's own retrieval-path error privacy.
4. Whether removing a chat participant should also revoke their generic
   media view authority.
5. Whether to wire up `staff_send_message`'s currently-dropped
   `media_ids` field.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation —
  this slice touched no Job/Booking model at all, only `MediaAsset`.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied.
- No new role, permission, or alias added.
- All 2F-18/2F-18A technician assignment/participant policy, thread
  privacy equivalence, customer object ownership, and sender/tenant
  identity server-derivation controls remain intact and unmodified.
- All previously-approved tests still pass (1 pre-existing test received
  an expected, deliberate mock-completeness update — see `test-report.md`).

## Coverage
**Unchanged at 200/226** — verified route-by-route, not assumed (see
`canonical-coverage-reconciliation.md` and `final-selected-route-protection.csv`).
All 10 selected routes are individually confirmed `FULLY_PROTECTED`,
including the one attachment-accepting route on the previously-open
attachment dimension.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No frontend/mobile
file was modified. No media upload/versioning infrastructure or new
message-attachment model was built — only reference-validation against the
EXISTING `MediaAsset` model, reusing the EXISTING `MediaAccessService`
helper. No file in `app/engines/media/` was modified. No second, unrelated
module's authorization was begun.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18B approval gate. The remaining 26-route, 10-module queue is left for
a future slice; no implementation of any other module has begun.
