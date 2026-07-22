# Notification Read Privacy

## Reads on this router
| Read | Tenant isolation | Recipient/participant ownership | Missing/foreign privacy-equivalent |
|---|---|---|---|
| `GET /v1/provider\|staff/notifications` | n/a (user-scoped, not tenant-filtered — `get_user_notifications` filters strictly by `user_id`) | `user_id == caller` | n/a (list, not by-ID) |
| `GET .../unread-count` | as above | as above | n/a |
| `GET .../preferences` | as above | as above | n/a |
| `GET .../chat/threads` | `tenant_id == caller` (provider/staff) | tenant-wide within own tenant, see `known-limitations.md` | n/a (list) |
| `GET .../chat/threads/{id}` | `validate_thread_access` | tenant match required | **YES** — a foreign thread ID and a nonexistent thread ID both raise the same error path: `get_thread` raises `CHAT_THREAD_NOT_FOUND` for a truly nonexistent ID, and `validate_thread_access` raises `CHAT_THREAD_ACCESS_DENIED` for a real-but-foreign-tenant thread. These are DISTINCT error codes (not privacy-equivalent in the strict sense used elsewhere in this initiative, e.g. Booking's unified 404) — flagged as a minor, pre-existing, non-blocking gap in `known-limitations.md`; both are still 4xx and neither discloses the foreign thread's content, so no content leak occurs, only existence-vs-access distinguishability. |
| `GET .../chat/threads/{id}/messages` | as above (via thread) | as above, plus per-message `visibility` filtering (now enum-validated) | same distinguishability caveat as above |
| `GET .../audit-logs` | `tenant_id == caller` | tenant-scoped by `actor_type="provider"` hardcoded server-side | n/a (list) |
| `GET .../audit-logs/record-timeline` | as above | as above | n/a |

## Nested-serializer check
`ChatMessage.to_dict(viewer_type)` returns `{}` (empty dict, filtered out by
the caller's list comprehension in `list_messages`) for any message not
visible to the requesting `viewer_type` — no hidden-field leak was found in
any nested structure; `InAppNotification.to_dict()` and `ChatThread.to_dict()`
expose only their own declared fields, no embedded foreign-tenant data.

## GET routes produce no mutation
Confirmed by code read: every GET handler in `provider_router.py` calls
only read methods (`get_user_notifications`, `get_unread_count`,
`get_preferences`, `list_threads`, `get_thread`, `list_messages`,
`get_audit_logs`, `get_record_timeline`) — none of these call `db.add`,
`db.commit`, or any write-returning service method.
