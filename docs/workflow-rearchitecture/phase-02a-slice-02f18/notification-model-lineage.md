# Notification/Chat Model Lineage

| Model | Table | Tenant key | Sender/creator key | Recipient key(s) | Status column | Classification |
|---|---|---|---|---|---|---|
| `NotificationEvent` | `notification_events` | `tenant_id` (nullable) | `actor_user_id` | — | `status` (created/processed/failed/ignored) | PLATFORM_INTERNAL_NOTIFICATION |
| `NotificationOutbox` | `notification_outbox` | `tenant_id` (nullable) | — | `recipient_user_id`, `recipient_type` | `delivery_status` | DELIVERY_RECORD |
| `InAppNotification` | `in_app_notifications` | `tenant_id` (nullable) | — | `user_id` (NOT NULL) | `read_status` | CUSTOMER_VISIBLE_RECORD / TENANT_INTERNAL_NOTIFICATION (both use this table, gated purely by `user_id`) |
| `NotifEventTemplate` | `notif_event_templates` | none | — | — | `is_active` | PLATFORM_INTERNAL_NOTIFICATION |
| `NotificationPreference` | `notification_preferences` | `tenant_id` (nullable) | — | `user_id` (NOT NULL) | `is_enabled` | NOTIFICATION_PREFERENCE |
| `ChatThread` | `chat_threads` | `tenant_id` (nullable) | `created_by_user_id` | `customer_id` (nullable) | `status` (open/closed/archived/blocked) | JOB_CONVERSATION / CUSTOMER_CONVERSATION (same table, distinguished by `record_type`) |
| `ChatThreadParticipant` | `chat_thread_participants` | `tenant_id` (nullable) | — | `user_id` (NOT NULL) | none (`can_read`/`can_send`/`left_at`) | JOB_CONVERSATION (membership) |
| `ChatMessage` | `chat_messages` | none (relies on thread) | `sender_user_id` (nullable), `sender_type` | implicit (thread participants) | `delivery_status`, `visibility` | CUSTOMER_VISIBLE_RECORD / PROVIDER_INTERNAL_RECORD (per `visibility`) |
| `ChatMessageRead` | `chat_message_reads` | none | — | `user_id` (NOT NULL) | none | AUDIT_INTERNAL (read receipt) |

## Notes (unchanged this slice — documented, not modified)
- No `ForeignKey()` constraints exist on any of these 8 models — all relational columns are bare UUIDs. Out of scope for this slice (would require a migration; migrations are explicitly forbidden).
- `tenant_id` is nullable on every table that has it. `validate_thread_access`'s provider/staff branch requires BOTH `thread.tenant_id` and the caller's `tenant_id` to be truthy AND equal — a `NULL` on either side falls through to deny (fails closed), verified by existing tests, unchanged this slice.
- `ChatMessage` has no `tenant_id` of its own (relies on its parent `ChatThread`) — this is a normal, non-duplicated FK-style relationship, not a gap.
