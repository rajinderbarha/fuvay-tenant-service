# Preferences and Device Token Policy

## Notification preferences
`NotificationPreference` is strictly principal-owned: `update_preference`
always writes `user_id = uuid.UUID(u.user_id)` (JWT-derived) — no route
accepts a `user_id` field, so one staff member cannot modify another's
preferences, and a tenant owner cannot modify a customer's preferences
through this router (customer preferences live under `/v1/customer/*`,
also now `require_customer`-gated).

**Fixed this slice**: `event_key`/`channel` are now validated against
`NotificationEventRegistry`/`ALL_CHANNELS` before write —
`NOTIFICATION_PREFERENCE_INVALID` on an unknown value (previously any
string was silently persisted, which is a data-quality gap, not an
authorization gap, but closed here since it was a one-line fix directly in
the same method already being hardened).

## Tenant-wide notification defaults
No such capability exists — `NotificationPreference` has no
"tenant default" row concept distinct from a per-user row (there is no
`user_id IS NULL` tenant-default semantics anywhere in the model or
service). Not built this slice (OUT OF SCOPE: do not invent
preferences/device-token features when absent).

## Device tokens
No `DeviceToken` model, route, or field exists anywhere in this module —
confirmed absent by the earlier model inventory
(`notification-model-lineage.md` lists all 8 models; none is a device
token). Classified `TECHNICIAN_NOT_SUPPORTED`-equivalent / not present,
not built.
