# Content Visibility Policy

## Unchanged from 2F-18 (re-confirmed)
`_VALID_VISIBILITIES = {thread, admin_only, provider_only, customer_only}`;
non-admin senders restricted to `thread`; unrecognized values fail closed
(`is_visible_to`'s default → `viewer_type == "admin"`).

## New this slice: technician is a distinct `viewer_type`
Previously, `staff_send_message`/`staff_list_messages` always passed the
literal string `"staff"` as `viewer_type` to `ChatMessage.to_dict()`/
`is_visible_to()`, for BOTH staff and technician callers. Since
`is_visible_to("provider_only")` admits `viewer_type in ("provider",
"staff", "admin")`, a technician viewing messages was previously treated
identically to office staff for visibility purposes — a `provider_only`
message (staff-internal) WAS visible to technicians.

Fixed (as a consequence of `_staff_actor_type(u)` now passing `"technician"`
for technician callers): `is_visible_to("provider_only")` does NOT include
`"technician"` in its allow-list — a `provider_only`/staff-internal message
is now correctly invisible to technician viewers, satisfying Workstream 12's
"Staff-internal messages are invisible to technicians unless policy
permits" requirement (no such permitting policy exists here, so the default
— invisible — applies).

`customer_only` and `admin_only` messages remain invisible to technicians
either way (technician was never in either allow-list).

## Nested serializer consistency
`list_messages` and the direct `send_message` response both route through
the SAME `ChatMessage.to_dict(viewer_type)` method — there is only one
serialization path for messages in this module, so "nested serializers
apply the same field filtering as direct reads" is true by construction
(not two divergent code paths that could drift).

## Visibility cannot be changed after send
No edit route exists on any router in this module — `visibility` is
immutable once a message is created (structural, not merely policy).
