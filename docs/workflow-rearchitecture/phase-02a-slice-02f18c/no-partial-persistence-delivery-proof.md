# No Partial Persistence / No Delivery Proof (this slice's new paths)

| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Test |
|---|---|---|---|---|
| Cross-Job/cross-conversation reuse (thread-claim mismatch) | `_validate_attachments`, before `ChatMessage(...)` construction | No | No | `test_cross_job_reuse_within_same_customer_rejected`, `test_cross_job_reuse_rejection_persists_nothing` |
| Partial-batch failure (2nd asset invalid) leaves 1st asset unclaimed | Claim-application pass runs only AFTER the full validation loop succeeds for ALL assets | No | No (and `good_asset.metadata_json` explicitly asserted unchanged) | `test_partial_batch_failure_does_not_claim_earlier_asset` |
| Unassigned technician retrieval denial | `MediaAssetService._assert_chat_thread_authority`, called from `get_asset`/`get_local_file_for_serve` before any file/metadata is returned | n/a (read-only route — no persistence to prove absent; the proof here is that NO response body/file bytes are returned, via the raised exception) | n/a | `test_unassigned_technician_denied_retrieval_of_job_thread_media` |

All rejected-attachment tests assert `db.add.assert_not_called()` and, for
the explicit no-partial-persistence test, `db.commit.assert_not_called()`
as well. Since `_notify_other_participants` executes strictly AFTER
attachment validation (including the claim check) succeeds, every
attachment-rejection test also proves zero delivery-side-effect
(`InAppNotification`) rows are created.

## Retrieval-path proof
Retrieval routes are read-only by construction (`GET` — no `db.add`/
`db.commit` call exists anywhere in `get_asset`/`get_local_file_for_serve`
or the router handlers that call them) — a denied retrieval simply raises
before returning any response body; there is no persistence to prove
absent on this path, only that no unauthorized data crosses the response
boundary (proven by the raised `NotFoundException`/`ServiceOSException`
propagating out before `return asset.to_dict(...)`/`return path,
mime_type` is ever reached).

## Pre-existing rejected paths (unchanged, re-confirmed by 2F-18/2F-18A/2F-18B, not re-tested here)
See the `no-partial-persistence-delivery-proof.md` files in each prior
slice's docs directory — all re-confirmed still passing by this slice's
full regression run.
