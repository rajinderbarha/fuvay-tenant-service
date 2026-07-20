# Runtime Verification Report

## Route-level (unchanged, re-run this slice)
All 10 selected routes still report a `VERIFIED`-set `guard_status`,
confirmed via live `inventory_mutation_routes.walk()` output identical to
every prior slice in this series.

## Object/attachment/retrieval-level (this slice's new deterministic checks)
`tests/test_phase2f18c_platform_notifications_media_sharing_retrieval.py`
— 11/11 passing:
- Thread-claim lock (4 tests): first-use claim, same-thread reuse allowed,
  cross-conversation reuse rejected, partial-batch-failure leaves no
  partial claim.
- Retrieval-time thread authority (5 tests): unassigned technician denied,
  assigned technician allowed, unclaimed asset skips the check,
  super_admin bypasses, missing/denied unified to `NotFoundException`.
- Dropped media_ids fix (1 test): `staff_send_message` now forwards
  `media_ids`.
- No-partial-persistence (1 test): cross-Job rejection persists nothing.

## Exit-condition checks (per this slice's Workstream 13)
- `assert_can_view` treated as redistribution permission without
  additional evidence — **fixed**: the thread-claim lock is additional,
  independent evidence layered on top.
- Intended recipients not authorized — addressed via the retrieval-time
  design (see `attachment-recipient-authority.md`'s reasoning for why a
  send-time enumeration was not built, and why the retrieval-time
  approach is a stronger, not weaker, guarantee).
- Same-customer cross-context media accepted ambiguously — **fixed**: the
  thread-claim lock rejects ambiguous reuse rather than allowing it.
- Technician tenant membership permits attachment retrieval — **fixed**
  for claimed assets; residual window for UNCLAIMED assets honestly
  disclosed (`known-limitations.md`).
- Removed participants retain private media access unexpectedly —
  **fixed** for claimed assets (`participant-removal-revocation.md`).
- Retrieval errors reveal asset existence — **fixed** for `chat_attachment`
  context (`media-error-privacy-equivalence.md`); other contexts
  unaffected (out of this slice's narrow scope).
- media_ids silently ignored — **fixed** (`staff_send_message`).
- Private media exposed through an unauthenticated permanent URL — NO,
  confirmed unchanged/already correct (`preview_url` defaults to the
  authenticated API path for non-public assets).
- An unsafe route marked FULLY_PROTECTED — none; `final-selected-route-protection.csv`
  shows all 10 routes individually re-verified, not assumed.
- Documentation disagrees with runtime — cross-checked; the CSV/docs match
  the actual `_validate_attachments`/`_assert_chat_thread_authority`
  implementations.

## Test-suite exit code
`pytest tests/test_phase2f18c_platform_notifications_media_sharing_retrieval.py`
exits 0 (11/11). Combined with 2F-18's 49, 2F-18A's 26, and 2F-18B's 9,
this module now has 95 deterministic tests across the four slices.
