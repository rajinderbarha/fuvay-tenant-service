# Service-Layer Bypass Report

## `NotificationService` methods reached by `provider_router.py`
`get_user_notifications`, `get_unread_count`, `mark_notification_read`,
`mark_all_read`, `get_preferences`, `update_preference`. All 6 also called
from `customer_router.py` (now `require_customer`-gated) and
`admin_router.py`'s `admin_notif_router` (already `require_platform_staff`).
No internal/worker caller reaches these 6 read/preference methods — the
internal-only surface (`fire_event`, `dispatch_pending`, `retry_failed`,
template CRUD) is entirely disjoint from what `provider_router.py` calls.

Strongest caller: `admin_notif_router` (`require_platform_staff`). Weakest
caller before this slice: `provider_router.py`/`customer_router.py` (bare
`get_current_user`). Weakest caller after this slice: none remain weaker
than role-scoped — parity restored across all three surfaces.

## `ChatThreadService`/`ChatMessageService` methods reached by `provider_router.py`
`list_threads`, `get_or_create_thread`/`create_thread`, `get_thread`,
`list_messages`, `send_message`, `mark_thread_read`. Also called from
`customer_router.py` (now `require_customer`-gated) and `admin_router.py`
(`require_super_admin`, plus `close_thread`/`moderate_message` which are
admin-exclusive and never reached from this router).

Router-level dependencies (this slice's fix) do not replace service-layer
ownership — the router guard determines WHO may call the endpoint at all;
`validate_thread_access`/the new record-ownership checks determine WHICH
records that caller may touch. Both layers were verified independently in
this slice's test suite.

## `PlatformAuditLogService` methods reached by `provider_router.py`
`get_audit_logs`, `get_record_timeline` — both called with
`actor_type="provider"` hardcoded server-side (not client-supplied),
`tenant_id=_tid(u)` (JWT-derived). No internal/worker caller reaches these
two methods from anywhere else with a weaker guard; `admin_audit_router`
(`require_super_admin`) is the only sibling caller, using
`actor_type="admin"` which bypasses tenant filtering inside
`get_audit_logs` by design (super_admin -- expected).
