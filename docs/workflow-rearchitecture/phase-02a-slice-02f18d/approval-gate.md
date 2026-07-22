# Slice 2F-18D Approval Gate

> **DEEPENED BY SLICE 2F-18E.** This slice closed the TECHNICIAN first-use
> gap (uploader-match required) but left the OFFICE (tenant_owner/staff)
> first-use gap open — office could still first-claim any tenant/customer-
> matched unclaimed asset into any of a customer's threads with no proof
> of which specific Job/conversation it belonged to. Slice 2F-18E
> (`docs/workflow-rearchitecture/phase-02a-slice-02f18e/`) closed this,
> plus fixed `replace_asset`'s read-authority-equals-replace-authority
> conflation and added retrieval lifecycle enforcement (deleted/inactive
> assets) that this slice never addressed. Coverage remains 200/226
> (unchanged — router-level arithmetic). Nothing in this slice's findings
> was factually wrong; this notice records further depth on dimensions
> this slice's own mission scoped to technician only, not a correction of
> the technician-specific work, which remains intact and unmodified.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Why SECURITY_CLOSED (deepened — first-use authority no longer ambiguous)
- Per the mission's own instruction ("Do not claim security closure while
  an arbitrary authorized viewer may make the first claim into an
  unrelated conversation"): a technician can no longer first-claim an
  unowned, unclaimed asset merely by belonging to the tenant and passing
  thread access — `uploaded_by_user_id` match is now required
  (`test_technician_cannot_first_claim_unowned_asset`,
  `test_technician_can_first_claim_own_upload`).
- Office personas and customers were already sufficiently evidenced by
  existing tenant/customer-match checks and remain correctly unaffected
  (`test_office_staff_first_claim_unaffected_by_technician_rule`,
  `test_customer_first_claim_own_upload_allowed`).
- `staff_send_message` (the technician-reachable attachment route) is now
  fully covered by this same restriction — closing the specific route
  this slice's mission targeted.
- All 2F-18/2F-18A/2F-18B/2F-18C security controls (router guards,
  technician thread-assignment/participant policy, thread-error privacy,
  tenant/customer/context/lifecycle attachment checks, retrieval-time
  thread authority) remain intact and unmodified — re-confirmed by the
  full targeted regression (356 tests).

## Why DOMAIN_INTEGRITY_CLOSED (deepened — claim creation now proven atomic)
- Per the mission's own instruction ("Do not claim domain-integrity
  closure while two concurrent requests can claim one asset for different
  threads"): the asset lookup now uses `SELECT ... FOR UPDATE`, proven
  directly via compiled-SQL inspection
  (`test_asset_lookup_uses_select_for_update`) — the mechanism that makes
  the pre-existing conflict check (2F-18C) race-free rather than merely
  logically correct in isolation.
- Every writer of the claim metadata was audited (exactly two exist) and
  hardened: `upload()` strips a forged claim key defensively;
  `replace_asset()` now requires the same thread-authority a retrieval
  would, closing a real gap where a tenant-wide "replace"-authorized user
  could swap a claimed asset's content without conversation authority.
- Malformed/conflicting claim metadata (non-dict, non-UUID claim value)
  now fails closed at BOTH the attach layer and the retrieval layer,
  rather than being silently reinterpreted as "unclaimed."

## Why PRIVACY_CLOSED (deepened — unclaimed technician window closed)
- Per the mission's own instruction ("Do not claim privacy closure while
  unclaimed chat assets remain tenant-wide retrievable"): for technicians
  specifically, they no longer are — uploader-match is required for BOTH
  attach and retrieval of an unclaimed asset.
- Serializer/URL audit (`serializer-url-audit.csv`) confirms no private
  chat attachment is ever exposed through an unrestricted permanent URL —
  every non-public asset's `preview_url` resolves to the authenticated,
  authorization-re-checking API path.
- Missing/unauthorized privacy equivalence (2F-18C) remains intact and now
  additionally covers this slice's new technician-denial and
  malformed-claim rejection paths (both flow through the same unification
  mechanism).

## Why PRODUCT_POLICY_BLOCKED (not fully closed)
Four genuine product questions remain open (see
`product-decisions-required.md`), none representing a live authorization
bypass in the paths this five-slice series' combined mission actually
covers:
1. Whether office (tenant_owner/staff) unclaimed-asset access should also
   be narrowed beyond the existing tenant+customer-match policy.
2. Whether a future migration should give `MediaAsset` a first-class
   claim column instead of the `metadata_json` convention.
3. Whether ServiceJob cancellation/completion should time-box media
   access.
4. Whether future new upload endpoints must adopt the same claim-key
   stripping discipline.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation —
  this slice touched no Job/Booking model at all.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied — and no migration was added or applied this
  slice either (the atomicity fix uses `with_for_update()`, a pure SQL
  clause requiring zero schema change).
- No new role, permission, or alias added.
- All 2F-18/2F-18A/2F-18B/2F-18C controls remain intact and unmodified.
- All previously-approved tests still pass (mock-mechanics updates only,
  each documented — see `test-report.md`).

## Coverage
**Unchanged at 200/226** — verified route-by-route, not assumed (see
`canonical-coverage-reconciliation.md` and `final-selected-route-protection.csv`).
All 10 selected routes are individually confirmed `FULLY_PROTECTED`.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No frontend/mobile
file was modified. No media upload/storage/signed-URL infrastructure or
new message-attachment table was built — only the atomic-lock mechanism
(`with_for_update()`), claim-metadata hardening, and first-use authority
narrowing, all scoped exactly to the chat_attachment authorization chain
as explicitly permitted. No second, unrelated module's authorization was
begun.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18D approval gate. The remaining 26-route, 10-module queue is left for
a future slice; no implementation of any other module has begun. This
five-slice series (2F-18, 2F-18A, 2F-18B, 2F-18C, 2F-18D) has now
addressed every workstream explicitly assigned to
`app.engines.platform_notifications.provider_router` and its attachment
chain — no further sub-slice of this specific module is anticipated
unless new evidence surfaces.
