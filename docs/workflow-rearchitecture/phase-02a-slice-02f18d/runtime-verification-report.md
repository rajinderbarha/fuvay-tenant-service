# Runtime Verification Report

## Route-level (unchanged, re-run this slice)
All 10 selected routes still report a `VERIFIED`-set `guard_status`,
confirmed via live `inventory_mutation_routes.walk()` output identical to
every prior slice in this series.

## Object/attachment/first-use/atomicity-level (this slice's new deterministic checks)
`tests/test_phase2f18d_platform_notifications_first_use_and_claim_integrity.py`
— 12/12 passing:
- Unclaimed-asset first-use authority (4 tests): technician denied without
  uploader match, technician allowed with uploader match, office persona
  unaffected, customer unaffected.
- Atomic claiming (1 test): proves the asset lookup query compiles with
  `FOR UPDATE`.
- Claim tampering resistance (3 tests): upload strips a forged claim key,
  `_strip_claim_key` handles `None`, `replace_asset` requires thread
  authority for claimed assets.
- Malformed/conflicting claim fail-closed (3 tests): non-dict
  `metadata_json`, non-UUID claim value (both layers — `chat_service` and
  `MediaAssetService`).
- No-partial-persistence (1 test): technician first-use rejection
  persists and claims nothing.

## Exit-condition checks (per this slice's Workstream 14)
- First-use destination authority caller-selected without evidence —
  **fixed**: technician now requires uploader-match evidence; all other
  personas already had independent evidence (customer/tenant match).
- Unclaimed technician retrieval tenant-wide — **fixed**: uploader-match
  now required at both attach AND retrieval time for technicians.
- Claim creation non-atomic — **fixed**: `SELECT ... FOR UPDATE` locks the
  row for the transaction's duration.
- Client or alternate writers modify the claim — **fixed/confirmed
  absent**: only two writers exist (`upload`, `replace_asset`), both now
  audited and hardened (claim-key stripping, thread-authority gate).
- Malformed/conflicting claims not failing closed — **fixed**: both
  layers now explicitly reject non-dict metadata and non-UUID claim
  values.
- Private attachments exposing permanent unrestricted URLs — NO, confirmed
  unchanged/already correct (`serializer-url-audit.csv`).
- Revoked users retaining direct media access — NO for claimed assets
  (2F-18C, re-confirmed); the unclaimed-technician window is now also
  closed (this slice).
- A blocked route marked FULLY_PROTECTED — none;
  `final-selected-route-protection.csv` shows all 10 routes individually
  re-verified.
- Documentation disagrees with runtime — cross-checked; the CSV/docs match
  the actual implementation.

## Test-suite exit code
`pytest tests/test_phase2f18d_platform_notifications_first_use_and_claim_integrity.py`
exits 0 (12/12). Combined with 2F-18's 49, 2F-18A's 26, 2F-18B's 9, and
2F-18C's 11, this module now has 107 deterministic tests across the five
slices.
