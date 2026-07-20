# Runtime Verification Report

## Route-level (unchanged from 2F-18/2F-18A, re-run this slice)
All 10 selected routes still report a `VERIFIED`-set `guard_status`
(`TENANT_MUTATION_ROLE_SCOPE_AWARE` / `STAFF_EXECUTION_ROLE_SCOPE_AWARE`),
confirmed via live `inventory_mutation_routes.walk()` output identical to
2F-18/2F-18A's.

## Object/attachment-level (this slice's new deterministic checks)
`tests/test_phase2f18b_platform_notifications_media_authority.py` — 9/9
passing — functions as this slice's deterministic verification suite:
- `media_context` taxonomy enforcement (2 tests).
- Lifecycle-state rejection (2 tests).
- Same-tenant cross-customer IDOR rejection (2 tests).
- `MediaAccessService` reuse proof, including the documented
  technician-tenant-wide existing-policy case (2 tests).
- Missing/cross-tenant privacy equivalence (1 test).

## Exit-condition checks (per this slice's Workstream 14)
- Tenant equality as the ONLY MediaAsset authority — **no longer true**:
  4 additional independent checks now run (context, lifecycle, customer,
  `MediaAccessService`).
- Existing media access policy ignored — **fixed**: `MediaAccessService.assert_can_view`
  is now called directly.
- A same-tenant unrelated asset can be attached — **fixed** for the
  customer dimension (customer_id check) and the context dimension
  (media_context check); **NOT fixed** for the Job/conversation dimension
  (no schema support) — honestly disclosed, not silently passed.
- Customer-visible messages can contain hidden/internal assets — the
  `media_context` taxonomy prevents non-`chat_attachment` assets from
  entering any message regardless of visibility.
- A Job-linked asset can be used in another Job's thread — **residual
  gap, disclosed** (no `job_id` column exists to check).
- An attached asset can be downloaded by an unauthorized recipient — NO
  (retrieval re-authorizes via the SAME `MediaAccessService`, pre-existing,
  verified not built).
- Legacy unlinked assets accepted without trusted authority — NO (see
  `legacy-unlinked-media-policy.md` — every row goes through the same 5
  checks regardless of lineage completeness).
- Missing/foreign asset errors distinguishable — NO, within
  `platform_notifications`'s own boundary (this slice); YES at the media
  engine's own retrieval routes (pre-existing, out-of-scope, disclosed).
- Denied attachment use persists or dispatches anything — NO, proven
  (`no-partial-persistence-delivery-proof.md`).
- Coverage marks an attachment-unsafe route fully protected — N/A; the
  one attachment-accepting route (`provider_send_message`) is now
  genuinely fully protected on this dimension, not merely assumed.
- Documentation disagrees with code — cross-checked;
  `final-selected-route-protection.csv` matches the actual
  `_validate_attachments` implementation.

## Test-suite exit code
`pytest tests/test_phase2f18b_platform_notifications_media_authority.py`
exits 0 (9/9). Combined with 2F-18's 49 and 2F-18A's 26, this module now
has 84 deterministic tests across the three slices.
