# No Partial Persistence Proof (this slice's new paths)

| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Claim written? | Test |
|---|---|---|---|---|---|
| Technician first-use claim of an unowned unclaimed asset | `_validate_attachments`, before the claim-application pass | No | No | No — `unowned.metadata_json.get("chat_thread_id")` asserted still `None` | `test_technician_cannot_first_claim_unowned_asset`, `test_technician_first_use_rejection_persists_nothing` |
| Non-dict `metadata_json` (corrupted state) | `_validate_attachments`, before the claim-application pass | No | No | No | `test_non_dict_metadata_json_fails_closed` |
| Malformed claim value (non-UUID) | `_validate_attachments`, before the claim-application pass | No | No | No | `test_malformed_claim_value_fails_closed` |
| `replace_asset` on a claimed asset without thread authority | `MediaAssetService.replace_asset`, before any file storage or DB write | n/a (no `db.add` on this path in the mocked test — the method raises before reaching `MediaAsset(...)` construction) | n/a | No — old asset's claim untouched | `test_replace_asset_requires_thread_authority_for_claimed_chat_asset` |

All new rejected-path tests assert `db.add.assert_not_called()` (and, for
the dedicated no-partial-persistence test, `db.commit.assert_not_called()`
plus an explicit assertion that the asset's `metadata_json` was never
mutated).

## Transaction rollback restores prior metadata
Not independently testable with mocks (no real DB transaction exists in
the mocked unit-test environment) — this relies on standard SQLAlchemy/
Postgres rollback-on-exception semantics, the SAME mechanism every prior
slice's "no partial persistence" proofs have relied on throughout this
initiative. Documented in `atomic-claiming.md`.

## Pre-existing rejected paths (unchanged, re-confirmed by 2F-18/2F-18A/2F-18B/2F-18C, not re-tested here)
All prior slices' `no-partial-persistence*.md` proofs re-confirmed still
passing by this slice's full regression run (356 targeted tests, 0
failures).
