# Claimed Retrieval Reverification

All items below were established in 2F-18C and are re-verified unchanged
by this slice's regression run (no code path governing CLAIMED asset
retrieval was modified this slice — only the UNCLAIMED branch and the
lock/tampering mechanisms changed).

| Requirement | Status | Test |
|---|---|---|
| Correct participant can retrieve | UNCHANGED, re-passing | 2F-18C's retrieval suite |
| Assigned technician can retrieve | UNCHANGED, re-passing | `test_assigned_technician_allowed_retrieval` |
| Wrong-Job technician denied | UNCHANGED, re-passing | `test_unassigned_technician_denied_retrieval_of_job_thread_media` (covers the wrong-Job case via a job assigned to someone else) |
| Unassigned technician denied | UNCHANGED, re-passing | same |
| Removed participant denied | UNCHANGED, re-passing (mechanism: `left_at` filter in `validate_thread_access`, reused at retrieval since 2F-18C) | covered by 2F-18A/2F-18C's participant-removal suites |
| Correct customer can retrieve | UNCHANGED, re-passing | `validate_thread_access`'s `RECIP_CUSTOMER` branch, reused at retrieval |
| Foreign customer denied | UNCHANGED, re-passing | same mechanism |
| Cross-tenant user denied | UNCHANGED, re-passing | `validate_thread_access`'s tenant-match branch |
| Malformed claim fails closed | **STRENGTHENED THIS SLICE** — now explicitly tested with a non-UUID-shaped claim value at the `MediaAssetService` layer directly | `test_asset_service_malformed_claim_denied_not_crashed` |
| Missing thread fails closed | UNCHANGED, re-passing | `_assert_chat_thread_authority`'s `thread is None` check (2F-18C) |
| Cross-tenant claimed thread fails closed | UNCHANGED, re-passing — additionally now also gates `replace_asset` (this slice), not just `get_asset`/`get_local_file_for_serve` | `test_replace_asset_requires_thread_authority_for_claimed_chat_asset` |

## New this slice: `replace_asset` brought into the claimed-retrieval-authority family
Previously only READ paths (`get_asset`, `get_local_file_for_serve`)
enforced `_assert_chat_thread_authority` for claimed assets. This slice
extends the SAME check to `replace_asset` — a mutation that, while not a
"retrieval," has an equivalent privacy/authority profile (it lets an
authorized-in-general-but-not-thread-authorized user overwrite what a
retrieval would later serve). See `implementation-summary.md` finding 3.
