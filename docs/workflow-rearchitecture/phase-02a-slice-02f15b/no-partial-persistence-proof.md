# No-Partial-Persistence Proof

Every rejection scenario in scope for this slice raises `ServiceOSException` before any `db.add`/`db.flush`/`db.commit` call, verified with `db.add.assert_not_called()`:

| Rejection scenario | Test | Persistence proof |
|---|---|---|
| No history row at all (field_ops relationship) | `test_no_history_row_at_all_fails_closed` | `db.add.assert_not_called()` |
| NULL `changed_by_role` on creation row (convert_to_job) | `test_null_changed_by_role_fails_closed` | `db.add.assert_not_called()` |
| Provider-confirmation-only history (convert_to_job) | `test_provider_confirmation_only_history_fails_closed` | `db.add.assert_not_called()` |
| Customer dependency impersonation (forged access_scope) | `test_customer_user_with_forged_readonly_scope_is_denied` | Raises before any handler/service code executes — the FastAPI dependency itself denies the request; no service method is ever entered |
| Foreign customer Booking action | Covered by pre-existing `_assert_can_access_booking` tests (Slice 2F-14F/2F-15A, unchanged, re-verified this slice via full regression) | `NotFoundException` raised before any mutation logic runs |

For every scenario above:
- The existing Booking row is unchanged (no `UPDATE` statement is ever reached — the exception is raised before the method's mutation code).
- No Job, assignment, checklist item, success-history row, success audit/domain event, or notification is created (all downstream code that would create these runs strictly after the provenance/ownership checks in every affected method — confirmed by source position: the checks are the first substantive logic after argument validation, before any `Job(...)`/`BookingRescheduleRequest(...)`/history-write construction).
- No commit precedes rejection — `ServiceOSException` propagates up through the (mocked, in tests; real `AsyncSession` in production) call stack to the router's exception handler, which never reaches the request's commit boundary.
