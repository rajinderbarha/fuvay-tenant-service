# StaffPermission Presentation

Backing model: `app/engines/auth/models.py::StaffPermission`
(`user_id`, `tenant_id`, `permission_key`, `is_granted`, `granted_by`),
applied via `app/engines/auth/service.py::_get_staff_permissions` and the
override-write path around line 1495 (`for perm_key, is_granted in
permissions.items(): ... StaffPermission.permission_key == perm_key ...`).

Real `permission_key` format: `"<namespace>:<resource>:<action>"`, e.g.
`field_ops:jobs:assign`, `inventory:items:write`,
`tenant_service_area:update` (see `app/core/permissions.py`'s `P` class).
`lib/ux03/fixtures.ts::FIXTURE_PERMISSION_CATALOG` uses real key strings
pulled from that file — no invented key names.

Four states are rendered, never conflated:
1. `granted_by_role` — comes from `ROLE_PERMISSIONS[role]`, no override row.
2. `granted_override` — explicit `StaffPermission` row, `is_granted=true`.
3. `denied_override` — explicit `StaffPermission` row, `is_granted=false`.
4. `not_granted` — no role default, no override row.

`denied_override` and `not_granted` both look "off" to a permission check
but must be visually distinct in the editor (see `PermissionEditor.tsx`'s
`StateChip`) — a denied override is an intentional lockout, not an absence.
A grant can never be presented as overriding an explicit deny anywhere in
this UI; `permissions-and-pipelines.test.ts` asserts a technician with a
`denied_override` entry never also renders as granted.

The tenant owner is excluded from the permission-override table entirely
(full account authority by role) — `TeamMemberDetail.tsx` renders an
explanatory note instead of the editor for `role === "tenant_owner"`.
