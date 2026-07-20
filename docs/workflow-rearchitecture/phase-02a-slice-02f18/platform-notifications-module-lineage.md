# Platform Notifications — Module Lineage

## Files
| File | Role |
|---|---|
| `models.py` | 8 ORM models (notifications + chat) |
| `constants.py` | Error codes, status/channel/visibility/recipient enums, event-key registry keys |
| `notification_service.py` | `NotificationService` — event firing, outbox dispatch, in-app CRUD, preferences, templates |
| `chat_service.py` | `ChatThreadService`, `ChatMessageService` — thread/message lifecycle, access control |
| `audit_service.py` | `PlatformAuditLogService` — wraps `security.models.PlatformAuditLog` |
| `channel_providers.py` | Delivery provider abstraction (in-app real; email/sms/whatsapp/push stubbed) |
| `event_registry.py` | `NotificationEventRegistry` — event_key → channels/template/enabled config |
| `recipient_resolver.py` | Resolves recipient lists for a fired event (not reached by provider_router) |
| `provider_router.py` | **This slice's target** — 5 routers: provider notif/chat/audit, staff notif/chat |
| `customer_router.py` | Customer notif/chat — same records, fixed alongside as an alternate-route bypass |
| `admin_router.py` | 6 routers, already `require_platform_staff`/`require_super_admin` gated — untouched |

## Capability boundary (not one capability)
1. In-app notifications (read/mark-read/preferences) — no send/create capability exists on this router (events are fired internally by other engines via `fire_event`, never by an HTTP mutation here).
2. Job/booking/complaint-linked chat (create thread, send message, mark read).
3. Tenant-scoped audit-log reads (no mutation).

## Parent-object relationships
- Chat threads link to `service_booking` / `service_job` / `complaint` (resolvable) or other `record_type` values (not resolvable by this service, but legitimately used by other engines' own chat entry points).
- `ServiceJob`/`ServiceBooking` are `app.engines.final_records.models`; `CustomerComplaint` is `app.engines.complaints.models`. Neither `field_ops.Job` nor `Booking` (legacy) is referenced anywhere in this module.
