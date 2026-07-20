# Invalid-State Side-Effect Proof — Slice 2F-9A

Both target routes were tested with a mocked `AsyncSession` whose
`db.add`, `db.flush`, and `db.commit` are directly assertable mocks. For
every rejected (illegal-state) call to either route, all three are
confirmed **never called**:

| Route | Rejected states tested | `db.add` calls | `db.flush` calls | `db.commit` calls |
|---|---|---|---|---|
| `provider_add_response` | closed, cancelled, rejected | 0 | 0 | 0 |
| `provider_offer_resolution` | open, awaiting_customer_response, resolution_proposed, rework_approved, resolved, closed, cancelled, rejected, settled | 0 | 0 | 0 |

This directly proves no `ComplaintMessage`, `ComplaintResolution`,
`ComplaintEvent`, settlement proposal, rework record, refund record, or
internal-credit/security-deposit mutation can occur through either route
when the complaint is in a state where the operation is prohibited —
because the `ValueError` is raised before any `db.add` call is reached in
both methods (confirmed by source inspection and by the mock call-count
assertions in `tests/test_phase2f9a_complaints_state_machine.py::TestSideEffectSafety`
and the per-state matrix tests).

Neither target method has any code path that reaches
`create_settlement_proposal`, `respond_to_settlement`,
`schedule_rework`/`mark_rework_in_progress`/`mark_rework_completed`, or
`provider_review_refund` — those are separate service methods, called
only from their own separate router endpoints (already authorized and
tenant-scoped per Slice 2F-9, unmodified this slice). No shared mutable
state or shared helper exists between them and the two target methods
that could allow one to trigger the other's side effect.
