# Repeated / Conflicting Action Review — Slice 2F-9A

| Scenario | Classification | Evidence |
|---|---|---|
| Repeated `respond_to_complaint` in the same active state | ALLOWED_MESSAGE_APPEND | `test_repeated_response_is_allowed_message_append` — 2 calls, 2 `ComplaintMessage` rows, no error |
| `respond_to_complaint` after complaint reaches `closed`/`cancelled`/`rejected` | STATE_TRANSITION_REJECTED (via `ERR_COMPLAINT_ALREADY_CLOSED`) | `test_final_state_rejected_no_mutation` |
| `offer_resolution` while one is already `resolution_proposed` | STATE_TRANSITION_REJECTED | `test_repeated_offer_while_already_resolution_proposed_rejected` |
| `offer_resolution` after settlement proposal exists (`settlement_proposed`-adjacent states) | N/A — `offer_resolution` and `create_settlement_proposal` are independent record types with independent legality checks; no shared guard exists, and none was found necessary — a settlement proposal does not itself change `complaint.status` to a value that would legalize or illegalize a resolution offer beyond the existing `ALLOWED_TRANSITIONS_EXT` check | source review, `complaint_service.py` `create_settlement_proposal` |
| `respond_to_complaint` after rework completion (`resolved`) | ALLOWED (respond_to_complaint has no final-state block on `resolved`, only on base `FINAL_STATUSES`) | matrix row `resolved` in `final-state-policy-matrix.csv` |
| `offer_resolution` after rework completion (`resolved`) | FINAL_STATE_MUTATION_PROHIBITED — `resolved` has no outgoing transition to `resolution_proposed` | `test_illegal_source_state_rejected_no_mutation[resolved]` |
| Concurrent/duplicate `respond_to_complaint` requests (race) | Not distinctly testable at the service-mock layer (no DB-level unique constraint exists on `ComplaintMessage`, by design — messages are an append-only log); out of scope to add one, since ordinary conversation is intentionally unbounded | source review |

## Explicit non-classification
Per the mission's instruction, an ordinary repeated provider message was
**not** treated as a duplicate to reject, and no idempotency key or
dedup logic was invented for it — `ComplaintMessage` is an append-only
conversation log by design (confirmed by its sibling, `add_customer_message`,
having the identical, unguarded-against-repeats behavior).
