# No Partial Persistence / No Delivery Proof

## Method
Direct service-layer tests assert `db.add.assert_not_called()` and
`db.commit.assert_not_called()` immediately after every rejected-path
exception, plus dependency-level tests proving the router itself never
reaches the service layer for a denied role.

## Proven rejected paths (this slice's new code)
| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Test |
|---|---|---|---|---|
| `create_thread` with nonexistent `service_job` record_id | Before `ChatThread(...)` construction | No | No | `test_provider_create_thread_rejects_nonexistent_service_job` |
| `create_thread` with cross-tenant `service_booking` | Before `ChatThread(...)` construction | No | No | `test_provider_create_thread_rejects_foreign_tenant_booking` |
| `create_thread` with cross-customer booking (customer caller) | Before `ChatThread(...)` construction | No | No | `test_customer_create_thread_rejects_foreign_customer_booking` |
| `send_message` with invalid `visibility` value | Before `ChatMessage(...)` construction, after thread/participant validation | No | No | `test_invalid_visibility_value_rejected` |
| `send_message` with non-admin sender + restricted visibility | Same point | No | No | `test_non_admin_cannot_set_restricted_visibility` |
| `update_preference` with unknown channel | Before any `select`/upsert | No | No | `test_unknown_channel_rejected` |
| `update_preference` with unknown event_key | Before any `select`/upsert | No | No | `test_unknown_event_key_rejected` |

## Pre-existing rejected paths (unchanged, re-confirmed by inspection, not re-tested here to avoid duplicate coverage)
- `mark_notification_read` on a foreign notification ID: raises before any
  `notif.read_status = ...` assignment (the `if not notif: raise` check
  happens before any mutation of the fetched row).
- `validate_thread_access` denial: raises before `send_message`/
  `mark_thread_read`/`list_messages` reach any write statement.
- Router-level denial (wrong role): the service layer is never invoked at
  all — FastAPI's dependency resolution raises before the endpoint function
  body runs, so zero DB calls of any kind occur.

## Delivery side effect
Since `_notify_other_participants` is only called from inside
`send_message` AFTER all the above checks pass, every rejected `send_message`
call also proves zero `InAppNotification` delivery-side-effect rows are
created (the same `db.add.assert_not_called()` assertion covers this,
since `_notify_other_participants` itself calls `db.add`).
