# Alternate Notification Route Audit

| Alternate surface | Same model/table? | Persona/dependency | Disposition |
|---|---|---|---|
| `customer_router.py` (`customer_notif_router`, `customer_chat_router`) | SAME (`InAppNotification`, `ChatThread`, `ChatMessage`, `NotificationPreference`) via the SAME service methods | Was `get_current_user` only — WEAKER_SAME_RECORD_ROUTE | **FIXED this slice** — now `require_customer`. See `implementation-summary.md` finding 2. |
| `admin_router.py` (`admin_notif_router`, `admin_chat_router`, etc.) | SAME tables, plus admin-only tables (`NotificationEvent`, `NotificationOutbox`, `NotifEventTemplate`) | Already `require_platform_staff`/`require_super_admin` | ALTERNATE_PROTECTED — stronger, not weaker; unchanged, out of scope. |
| Booking/ServiceBooking routers | DISTINCT models — only referenced indirectly via `record_id` resolution, no chat/notification write path exists there | n/a | DISTINCT_NOTIFICATION_MODEL — no bypass possible. |
| ServiceJob/field_ops routers | DISTINCT models, same relationship as above | n/a | DISTINCT_NOTIFICATION_MODEL |
| WebSocket handlers | None exist in this codebase for chat/notifications | n/a | DISCONNECTED (not built, not a bypass) |
| Internal delivery workers (`dispatch_pending`/`retry_failed`) | SAME `NotificationOutbox` table | Called only from `admin_router.py` (`require_super_admin`) or scheduled internal jobs, never HTTP-reachable via `provider_router.py` | TRUSTED_INTERNAL |
| Notification preference / device-token routers | No separate router exists — preferences live inside `provider_notif_router`/`customer_notif_router`/`admin_notif_router` only | n/a | n/a (already covered above) |

## Conclusion
Exactly one weaker same-record route was found (`customer_router.py`) and
it has been fixed as part of this slice (same module, directly connected —
not a second unrelated module). No other alternate route reaching these
records is weaker than the now-hardened `provider_router.py`/`staff_router`.
