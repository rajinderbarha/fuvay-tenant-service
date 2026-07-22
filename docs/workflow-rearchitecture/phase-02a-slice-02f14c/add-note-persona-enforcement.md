# add_note Persona Policy

## Supported personas

- `tenant_owner` — tenant-wide authority (own tenant only, `_assert_can_access_job`'s
  tenant_owner branch).
- Canonical `staff` — assigned-Job authority only (`_assert_can_access_job`'s
  `_assert_assigned` branch, role-agnostic `assigned_staff_id == actor_id`).
- `technician` — same as `staff`: assigned-Job authority only. Technician note creation IS
  supported (the model's `author_role` field explicitly accepts arbitrary role strings and
  `_assert_can_access_job` treats `staff`/`technician` identically).
- Unassigned `staff`/`technician` — **denied** (`NotFoundException`, 404, existence hidden).
- `customer` — **denied** (`NOTE_ACCESS_DENIED`, 403) — no documented "customer adds a note to
  their own job" capability exists anywhere in this engine.
- `super_admin` — platform-wide (no restriction branch in `_assert_can_access_job` fires for
  this role).

## Fixed this slice

Router-level guard was `get_current_user` only (no persona/scope dependency at all) — the
service-level fix from Slice 2F-14A was real but entirely invisible to runtime dependency
introspection. Fixed by adding `require_staff_or_above_mutation` at the router — the narrowest
existing composed dependency that (a) excludes `customer` (matching the service's own denial),
(b) admits `tenant_owner`/`staff`/`technician`/`super_admin`, and (c) denies any tenant-side
actor with a read-only `access_scope`. No new permission or dependency was created.

## Verified

- Tenant-wide vs. assigned-Job authority: `tenant_owner` is tenant-wide (any job in their
  tenant); `staff`/`technician` are assigned-Job only. Both mechanisms pre-date this slice and
  are unmodified.
- Technician note creation: supported, assignment-gated (see above).
- Note author type: `author_id=self.actor_id`, `author_role=self.actor_role` — both always
  **server-derived** from the authenticated `UserContext`, never taken from the request body.
  The request body only supplies `content`/`note_type`/`is_internal` — there is no field the
  client could use to impersonate a different author.
- Internal/customer-visible behavior: unchanged from Slice 2F-14A (`is_internal=True` notes
  filtered from customer reads in `list_notes`).
- Job-final-state behavior: no state guard exists on note creation regardless of Job status —
  notes may be added at any point in the Job lifecycle, including after completion/closure. This
  is intentional (notes are an audit/communication trail, not a lifecycle-gated action) and was
  not changed.
- Cross-tenant Job IDs fail without disclosure: `_assert_can_access_job` raises
  `NotFoundException` (404), not 403, for a `tenant_owner` whose tenant doesn't match.
- Denied calls create no `JobNote`: verified via `test_no_mutation_on_denied_add_note` (Slice
  2F-14A, re-verified this slice) — `db.add` is never called before the ownership/persona check
  passes.

## Final classification

**FULLY_PROTECTED_ROUTER_AND_SERVICE** — both layers now present and verified.
