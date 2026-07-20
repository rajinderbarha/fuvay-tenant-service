# Slice 2F-18A Approval Gate

> **DEEPENED BY SLICE 2F-18B.** This slice's attachment/media check was
> tenant-equality-only (existence + tenant match against `MediaAsset`) —
> Slice 2F-18B (`docs/workflow-rearchitecture/phase-02a-slice-02f18b/`)
> replaced it with the EXISTING `MediaAccessService.assert_can_view` helper
> plus same-customer and `media_context`-taxonomy checks, closing the
> same-tenant IDOR gap this slice's own `known-limitations.md` (item 1,
> uploader-level authorization) had already flagged. Coverage remains
> 200/226 (unchanged — router-level arithmetic, not object-level). Nothing
> in this slice's findings was factually wrong; this notice records a
> genuine depth increase on one specific dimension (attachments), not a
> correction of the other closures (technician policy, thread privacy)
> this slice made, which remain intact and unmodified.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Why SECURITY_CLOSED
- Technician access to chat threads is no longer tenant-wide — the
  `RECIP_TECHNICIAN` branch in `validate_thread_access` requires either
  live assignment to the exact parent `ServiceJob` (for resolvable record
  types) or an active participant row (for unresolvable ones). Tenant
  membership alone is proven insufficient
  (`test_technician_tenant_membership_alone_is_not_sufficient`).
- Unassigned technicians, technicians assigned to a DIFFERENT job, and
  removed participants are all denied, each independently proven
  (`TestTechnicianThreadAccessPolicy`).
- `list_threads` no longer grants technicians tenant-wide visibility —
  falls through to the existing participant-scoped branch.
- All dependency semantics directly tested by invocation, not just
  introspection (`TestDependencySemantics`, 11 tests) — confirms
  read-only-owner/staff denial, technician exclusion from
  `require_owner_or_office_staff_mutation`, prohibited-alias denial,
  customer exclusion from tenant branches, and vice versa.
- Customer-router reverified: `require_customer` is layered under real
  object ownership (`customer_id`/`validate_thread_access`), not a
  standalone role check — proven not merely asserted
  (`TestCustomerRouterObjectOwnership`).
- No weaker same-record route remains (2F-18's fix re-confirmed intact).

## Why DOMAIN_INTEGRITY_CLOSED (advanced from 2F-18's BLOCKED)
- Attachment ownership is no longer unknown — `ATTACHMENT_MODEL_SUPPORTED`
  disposition implemented: every referenced `media_id` must exist and
  belong to the sending thread's own tenant, verified before persistence,
  with privacy-equivalent rejection (same error code for missing vs.
  cross-tenant).
- Notification/message states remain explicit (2F-18, unchanged);
  delivery ordering re-verified with the new attachment check correctly
  inserted before persistence (`delivery-ordering.md`).
- Invalid actions (technician denial, attachment rejection) create no
  partial database or delivery state — proven directly
  (`no-partial-persistence-delivery-proof.md`).

Residual attachment-depth gaps (uploader-level authorization, formal
message-binding) are real but are PRODUCT_POLICY questions about how far
attachment ownership SHOULD go, not unresolved security holes — the
acute cross-tenant IDOR risk (the part a security review would flag first)
is closed. See `product-decisions-required.md`.

## Why PRIVACY_CLOSED (advanced from an open gap in 2F-18)
- Foreign and missing threads are now externally indistinguishable — same
  error code, same HTTP status (404), proven end-to-end including the
  actual `_domain_code_status` mapping
  (`test_thread_not_found_maps_to_404_not_403`).
- This applies uniformly across customer, technician, and provider/staff
  denial branches — not just one persona.
- Content visibility is now technician-aware — staff-internal
  (`provider_only`) messages are correctly invisible to technician
  viewers, closing a real (if narrower) leak 2F-18 didn't examine.
- Notification privacy was already unified pre-existing (single error code
  for missing/foreign in `mark_notification_read`).

## Why PRODUCT_POLICY_BLOCKED (not fully closed)
Four genuine product questions remain open, none of which represent an
authorization bypass or content leak on their own:
1. Attachment uploader-level authorization depth.
2. Formal message-level attachment binding (would require a migration).
3. Completed/cancelled Job technician access time-boxing.
4. `list_threads`' participant-snapshot vs. live-assignment listing gap for
   technicians (a technician CAN access via direct link even when not
   listed — an access-vs-discoverability inconsistency, not an
   authorization bypass).

See `product-decisions-required.md` for the full detail on each.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation —
  `_resolve_job_for_thread` (new this slice) only ever queries
  `ServiceJob`/`ServiceBooking`, never `field_ops.Job` or legacy `Booking`.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied.
- No new role, permission, or alias added.
- All previously-approved tests still pass (2 pre-existing tests received
  expected, deliberate assertion updates — see `test-report.md`).

## Coverage
**Unchanged at 200/226** — this slice deepened object-level policy behind
the same 10 routes 2F-18 already router-guard-protected; the canonical
CSV's router-dependency-based convention is unaffected. See
`canonical-coverage-reconciliation.md`.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No frontend/mobile
file was modified. No attachment-upload, email/SMS/push, or WebSocket
infrastructure was built (only reference-validation against the EXISTING
`MediaAsset` model). No second, unrelated module's authorization was begun.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18A approval gate. The remaining 26-route, 10-module queue is left for
a future slice; no implementation of any other module has begun.
