# Slice 2F-18C Approval Gate

> **DEEPENED BY SLICE 2F-18D.** This slice built the thread-claim lock but
> did not restrict WHO could perform the first claim (any authorized
> viewer, including a tenant-wide technician, could claim an unclaimed
> asset into any thread) and did not make claim creation atomic against
> concurrent requests. Slice 2F-18D
> (`docs/workflow-rearchitecture/phase-02a-slice-02f18d/`) added a
> first-use destination-authority rule (technician uploader-match) and
> `SELECT ... FOR UPDATE` locking, closing both gaps, plus audited and
> hardened every writer of the claim metadata. Coverage remains 200/226
> (unchanged — router-level arithmetic). Nothing in this slice's findings
> was factually wrong; this notice records a genuine depth increase on the
> first-use/atomicity/integrity dimension, not a correction of the
> retrieval-time thread authority or privacy-equivalence work this slice
> did, which remains intact and unmodified.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Why SECURITY_CLOSED (deepened from 2F-18B's tenant/customer-only foundation)
- View authority (`MediaAccessService.assert_can_view`) is no longer
  treated as equivalent to redistribution authority — a separate,
  additional thread-claim lock now governs whether an asset may be shared
  into a SPECIFIC conversation (`view-versus-share-authority.md`).
- Same-customer cross-Job/cross-conversation attachment reuse is proven
  rejected (`test_cross_job_reuse_within_same_customer_rejected`) — this
  is the specific gap 2F-18B's tenant/customer-only check could not close.
- Unassigned technicians (and technicians assigned to a different Job)
  can no longer retrieve a Job-thread's media directly, even with generic
  tenant-role media-view rights
  (`test_unassigned_technician_denied_retrieval_of_job_thread_media`).
- Removed participants lose retrieval access to claimed media on their
  next attempt, not just thread-read access
  (`participant-removal-revocation.md`).
- `staff_send_message`'s previously-silently-dropped `media_ids` is now
  processed through the identical validation chain as
  `provider_send_message` — no client input is silently discarded.
- All 2F-18/2F-18A/2F-18B security controls (router guards, technician
  thread-assignment/participant policy, thread-error privacy, tenant/
  customer/context/lifecycle attachment checks) remain intact and
  unmodified — re-confirmed by the full targeted regression (344 tests).

## Why DOMAIN_INTEGRITY_CLOSED (advanced — target-context authority now provable where the schema allows)
- Per the mission's own instruction ("Do not claim domain-integrity
  closure while accepted media_ids are silently discarded or
  target-context authority cannot be proven"): media_ids are no longer
  silently discarded (fixed), and target-context authority (which
  conversation an asset belongs to) is now provable via the thread-claim
  lock — the smallest safe mechanism achievable without a schema change
  (explicitly forbidden this slice).
- The one dimension genuinely NOT fully closable — an unclaimed asset's
  pre-first-use tenant-wide visibility, and non-`chat_attachment`
  contexts' retrieval privacy — is honestly disclosed, not silently
  claimed closed (`known-limitations.md`).

## Why PRIVACY_CLOSED (advanced — retrieval routes now included, not just attachment validation)
- Per the mission's own instruction ("Do not claim privacy closure while
  media retrieval bypasses thread authority" / "The claim that the media
  engine retrieval gap is unrelated to chat privacy" must be corrected):
  the retrieval routes (`GET /v1/media/{id}`, `/view`, `/download`) now
  apply thread-equivalent authority for `chat_attachment` assets, and
  missing/denied are now privacy-equivalent (same `NotFoundException`,
  same 404) for that context — proven directly
  (`test_get_asset_unifies_missing_and_denied_to_not_found`).
- This closes the SPECIFIC gap that blocked `platform_notifications`
  privacy closure (a known `media_id` bypassing thread authority) without
  claiming a broader, unscoped media-engine-wide privacy fix.

## Why PRODUCT_POLICY_BLOCKED (not fully closed)
Five genuine product questions remain open (see
`product-decisions-required.md`), none representing a live authorization
bypass in the paths this slice's mission actually covers:
1. Whether to further restrict unclaimed-asset tenant-wide visibility.
2. Whether to align `_load`'s lifecycle filter with attach-time strictness.
3. Whether a future migration should give `MediaAsset` first-class
   thread/Job lineage columns instead of the `metadata_json` convention.
4. Whether to extend retrieval-privacy unification to every media context.
5. Whether participant-removal revocation should extend to other media
   contexts if chat ever supports them.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation —
  this slice touched no Job/Booking model, only `MediaAsset` (via its
  existing `metadata_json` column) and `ChatThread`/`ChatThreadParticipant`
  (read-only, reused unmodified).
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied — and no migration was added or applied this
  slice either (the thread-claim lock deliberately uses the EXISTING
  `metadata_json` column, per the explicit OUT OF SCOPE constraint).
- No new role, permission, or alias added.
- All 2F-18/2F-18A/2F-18B controls remain intact and unmodified.
- All previously-approved tests still pass (2 pre-existing tests received
  expected, deliberate mock-completeness updates — see `test-report.md`).

## Coverage
**Unchanged at 200/226** — verified route-by-route, not assumed (see
`canonical-coverage-reconciliation.md` and `final-selected-route-protection.csv`).
All 10 selected routes are individually confirmed `FULLY_PROTECTED`,
including `staff_send_message`, which is now a genuinely functional,
fully-validated attachment-capable route for the first time.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No frontend/mobile
file was modified. No media upload/storage/signed-URL infrastructure or
new message-attachment table was built — only a narrowly-scoped retrieval
authority check reusing EXISTING `platform_notifications` logic, added to
ONE file in `app/engines/media/` as explicitly permitted by this slice's
own mission text. No second, unrelated module's authorization was begun.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18C approval gate. The remaining 26-route, 10-module queue is left for
a future slice; no implementation of any other module has begun.
