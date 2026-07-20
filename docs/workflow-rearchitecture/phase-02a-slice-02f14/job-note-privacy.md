# Job Note Privacy

> **SUPERSEDED (Slice 2F-14A):** the finding below was fixed in Slice 2F-14A, not deferred. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f14a/jobnote-access-control.md`. Content below
> retained for historical record.

## Model

`JobNote` (`job_notes`): `job_id`, `tenant_id`, `author_id`, `author_role`, `note_type`
(default `"staff_note"`), `content`, `status_at`, `is_internal` (bool, default `True`).

## Exposure surface

`JobNote` is **not** read or written anywhere in `field_ops.staff_router` or in any of the 9
routes fixed this slice on `field_ops.router`. `_job_dict` (the job-detail serializer used by
`my_job_detail`) does not embed notes. The only surface is `field_ops.router`'s
`add_note`/`list_notes` (lines ~472-487), which are among the 19 routes this slice's mission
explicitly places out of scope (distinct capability, not a same-record-same-capability alternate
to staff_router's checklist/status/assign mutations).

## Finding — NOT FIXED THIS SLICE (documented per mission's honesty requirement)

`FieldOpsService.add_note`/`list_notes` perform **no tenant, role, or `is_internal` filtering at
all**: `list_notes` returns every note for a `job_id` (including `is_internal=True` staff-only
notes) to any caller who passes `get_current_user` (no role check), regardless of tenant
membership or job assignment. `add_note` similarly never validates that `tenant_id` matches the
job's actual tenant, or that the caller has any relationship to the job.

This is a real, pre-existing privacy gap (a customer or a staff member from a different tenant
could, in principle, read internal notes on any job by ID), but it is **not** a same-capability
bypass of anything fixed this slice — it is an independently unprotected capability that predates
this slice's work and was never gated by either router. Per the mission's explicit scope rule
("Implementation work in a second router is prohibited unless it is a live, same-record,
same-capability bypass") this does not qualify for a fix in this slice. Recorded in
known-limitations.md / deferred-items.md / product-decisions-required.md for a future slice
scoped to `field_ops.router`'s notes/media capability.
