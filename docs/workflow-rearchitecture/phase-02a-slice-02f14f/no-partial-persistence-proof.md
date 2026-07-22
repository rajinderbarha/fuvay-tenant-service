# No Partial Persistence Proof

## Ordering (unchanged, extended)

The relationship guard (`_assert_tenant_customer_relationship`) executes inside the existing
`customer_id` validation block — after the `role == "customer"` and `is_active`/`deleted_at`
checks, before the `Job(...)` constructor is ever reached (same block, same position in source
order as all prior 2F-14C/D/E customer validation).

## Proven for every rejected case

- `db.add.assert_not_called()` — explicitly asserted in
  `test_completely_unrelated_customer_rejected`, `test_customer_known_only_to_another_tenant_rejected_same_error`
  (implicitly, via `pytest.raises` before any add), `test_wrong_role_user_rejected_before_relationship_check`,
  `test_deactivated_customer_rejected`, `test_deleted_customer_rejected`.
- **No assignment created**: `create_job` never creates an assignment under any code path
  (structural, unchanged from Slice 2F-14D).
- **No JobChecklistItem created**: `create_job` never materializes the normalized checklist
  system under any code path (structural, unchanged).
- **No JobStatusHistory created**: `_write_history` is only called after `db.add`/`db.flush`,
  never reached on any rejection.
- **No commit**: no explicit `commit()` call exists in this method; the surrounding
  request-scoped transaction (unchanged, out-of-scope infrastructure) never receives a
  self-inflicted "success" state to commit, since the exception propagates up before any of the
  success-path statements execute.
- **Existing Booking/Job records unchanged**: the relationship query is read-only
  (`select(...).limit(1)`), confirmed via source inspection — no `UPDATE`/`db.add` targeting
  `Booking` or `Job` occurs anywhere in `_assert_tenant_customer_relationship`.

## Test-level proof

All 2F-14F rejection tests exercise the SAME `MagicMock`-based `db` object used across
`create_job`'s existing test suite — `db.add.assert_not_called()` is a real, executed assertion
against a call-tracking mock, not a source-string inspection.
