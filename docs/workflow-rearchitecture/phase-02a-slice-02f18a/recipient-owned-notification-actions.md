# Recipient-Owned Notification Actions

## Finding: already correct, re-verified not re-fixed

`mark_notification_read`, `mark_all_read`, `get_user_notifications`,
`get_unread_count`, `get_preferences`, `update_preference` all derive the
acting principal's identity exclusively from the JWT
(`uuid.UUID(u.user_id)`), and every underlying query is `WHERE user_id ==
caller` (or `id == X AND user_id == caller` for the single-record mutation).
This was true before 2F-18, remained true through 2F-18, and is unchanged
by 2F-18A — confirmed by direct code read, no gap found.

Consequences directly proven by this and prior slices' test suites:
- One staff member cannot mark another staff member's notification read
  (`mark_notification_read` raises `IN_APP_NOTIFICATION_NOT_FOUND` for a
  cross-user ID — the notification genuinely isn't found under that
  `WHERE user_id=caller` filter).
- A technician cannot alter another technician's recipient record (same
  mechanism — `staff_mark_read`/`staff_mark_all_read` pass `u.user_id`
  regardless of role).
- A provider cannot mark a customer's notification read, and a customer
  cannot alter a provider's — there is no shared identifier space that
  would make `user_id` collide across personas (UUIDs), and no route
  accepts a `user_id` override in its request body on any of the 3 routers.
- Bulk state updates (`mark_all_read`) are principal-scoped by construction
  — the underlying query is `WHERE user_id == caller AND read_status ==
  unread`, never a tenant- or role-wide bulk update.

No code change was required for this workstream — it is reported here to
close the workstream explicitly, not to claim a fix that didn't happen.
