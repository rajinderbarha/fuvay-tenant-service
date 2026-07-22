# Transaction Atomicity Report - Slice 2F-29

- Both new validations fail **before** any `db.add`, so a rejected request
  leaves no partial row. For `invite_staff` this is explicit: permission-key
  validation runs at the top of the method, before the `User` is constructed.
  Asserted by `test_unknown_permission_rejected_on_invite_before_persistence`
  (`db.add` must not be called).
- No new broad `except` was introduced; no authorization failure is swallowed.
- The guard rejection for read-only access scope happens inside the FastAPI
  dependency, before the endpoint body runs and therefore before any DB work.
- Existing session-revocation and usage-adjustment logic inside
  `deactivate_staff` / `update_permissions` was left in its existing
  transaction boundary.
